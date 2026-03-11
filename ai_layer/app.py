import os
import shutil
from typing import List, Optional, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from anthropic import Anthropic

from rag.retriever import retrieve
from rag.build_index import main  

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
PY_PORT = int(os.getenv("PY_PORT", "8000"))

MAX_CONTEXT_CHARS = 12000

PDF_FOLDER = "rag/pdfs"
os.makedirs(PDF_FOLDER, exist_ok=True)

if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY is missing in ai_layer/.env")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

app = FastAPI(
    title="AI Layer (Anthropic + Local RAG)",
    version="1.0.0",
    description="FastAPI service with local-embedding RAG over PDFs + Anthropic generation."
)

Role = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: Optional[List[ChatMessage]] = None
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=400, ge=1, le=2000)
    top_k: int = Field(default=4, ge=1, le=10)


class Source(BaseModel):
    source_file: str
    page: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    sources: List[Source] = []


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "ai-layer-rag",
        "model": ANTHROPIC_MODEL
    }


# ---------------- PDF Upload Endpoint ---------------- #

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):

    try:

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        file_path = os.path.join(PDF_FOLDER, file.filename)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ⭐ INDEX THE PDF INTO FAISS
        # index_new_pdf(file_path)
        main()
        return {
            "message": "PDF uploaded and FAISS index updated",
            "filename": file.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ---------------- Utility Function ---------------- #

def extract_text(content_blocks) -> str:
    parts = []
    for b in content_blocks or []:
        if getattr(b, "type", None) == "text":
            parts.append(getattr(b, "text", ""))
    return "".join(parts).strip()


# ---------------- Chat Endpoint ---------------- #

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):

    try:

        contexts = retrieve(req.message, k=req.top_k)

        if not contexts:
            return ChatResponse(
                reply="I don’t have that information in my documents.",
                sources=[]
            )

        context_text = "\n\n".join(
            [
                f"[Source: {c['source_file']}"
                f"{'' if c['page'] is None else ', page ' + str(c['page'])}]"
                f"\n{c['text']}"
                for c in contexts
            ]
        )

        context_text = context_text[:MAX_CONTEXT_CHARS]

        system_prompt = (
            "You are a helpful assistant.\n"
            "Use ONLY the CONTEXT provided to answer.\n"
            "If the answer is not in the context, say: "
            "'I don’t have that information in my documents.'\n"
            "When you use a fact from the context, cite it like (Source: filename.pdf).\n\n"
            f"CONTEXT:\n{context_text}\n"
        )

        messages = []

        if req.history:
            messages.extend(
                [{"role": m.role, "content": m.content} for m in req.history]
            )

        messages.append({"role": "user", "content": req.message})

        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            system=system_prompt,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )

        reply = extract_text(resp.content) or "(No text returned)"

        seen = set()
        sources: List[Source] = []

        for c in contexts:
            key = (c["source_file"], c.get("page"))

            if key not in seen:
                seen.add(key)
                sources.append(
                    Source(
                        source_file=c["source_file"],
                        page=c.get("page")
                    )
                )

        return ChatResponse(reply=reply, sources=sources)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG chat failed: {str(e)}"
        )