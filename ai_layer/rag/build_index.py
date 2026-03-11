from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "pdfs"
INDEX_DIR = BASE_DIR / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_pdfs():
    pdfs = sorted([p for p in DOCS_DIR.rglob("*.pdf")])

    if not pdfs:
        raise SystemExit(f"No PDFs found. Put text PDFs into: {DOCS_DIR}")

    docs = []

    for pdf in pdfs:
        print(f"📘 Loading: {pdf.name}")

        loader = PyPDFLoader(str(pdf))
        loaded = loader.load()

        # Add metadata for citation
        for d in loaded:
            d.metadata["source_file"] = pdf.name
            d.metadata["page"] = d.metadata.get("page", None)

        docs.extend(loaded)

    return docs


def main():

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📄 Loading PDFs from: {DOCS_DIR}")

    documents = load_pdfs()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(documents)

    print(f"✂️ Split into {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

    print(f"🧠 Creating embeddings locally using: {EMBED_MODEL_NAME}")

    db = FAISS.from_documents(chunks, embeddings)

    db.save_local(str(INDEX_DIR))

    print(f"✅ FAISS index saved to: {INDEX_DIR}")


# ---------------- NEW FUNCTION FOR UPLOADED PDF ---------------- #

def index_new_pdf(pdf_path: str):

    print(f"📘 Indexing new PDF: {pdf_path}")

    loader = PyPDFLoader(pdf_path)

    docs = loader.load()

    for d in docs:
        d.metadata["source_file"] = Path(pdf_path).name
        d.metadata["page"] = d.metadata.get("page", None)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

    # If FAISS index exists → load and add documents
    if (INDEX_DIR / "index.faiss").exists():

        db = FAISS.load_local(
            str(INDEX_DIR),
            embeddings,
            allow_dangerous_deserialization=True
        )

        db.add_documents(chunks)

    else:

        db = FAISS.from_documents(chunks, embeddings)

    db.save_local(str(INDEX_DIR))

    print("✅ New document indexed successfully")


if __name__ == "__main__":
    main()