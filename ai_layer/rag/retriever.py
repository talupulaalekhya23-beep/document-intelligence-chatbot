from pathlib import Path
from typing import List, Dict, Any

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "index"

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

_db = None
_last_loaded_time = None


def _load_db():

    global _db, _last_loaded_time

    if not INDEX_DIR.exists():
        raise RuntimeError("RAG index not found. Run: python rag/build_index.py")

    index_time = INDEX_DIR.stat().st_mtime

    # Reload if index changed
    if _db is None or _last_loaded_time != index_time:

        print("🔄 Loading FAISS index...")

        _db = FAISS.load_local(
            str(INDEX_DIR),
            _embeddings,
            allow_dangerous_deserialization=True
        )

        _last_loaded_time = index_time

    return _db


def retrieve(query: str, k: int = 4) -> List[Dict[str, Any]]:
    """
    Returns top-k chunks:
    [
      {"text": "...", "source_file": "abc.pdf", "page": 3},
      ...
    ]
    """

    db = _load_db()

    docs = db.similarity_search(query, k=k)

    print("\n🔎 QUERY:", query)

    for i, d in enumerate(docs):
        print(f"\n--- Chunk {i+1} ---")
        print(d.page_content[:400])

    results = []

    for d in docs:
        results.append({
            "text": d.page_content,
            "source_file": d.metadata.get(
                "source_file",
                d.metadata.get("source", "unknown")
            ),
            "page": d.metadata.get("page", None),
        })

    return results