import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_store")

# Use a lightweight local embedding model — free, fast, no API key needed
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

_client = chromadb.PersistentClient(path=CHROMA_PATH)


def _collection_name(user_id: int, document_id: int) -> str:
    return f"user_{user_id}_doc_{document_id}"


def upsert_chunks(user_id: int, document_id: int, chunks: list[str]) -> int:
    """Store text chunks into ChromaDB. Returns chunk count."""
    col_name = _collection_name(user_id, document_id)
    collection = _client.get_or_create_collection(
        name=col_name,
        embedding_function=_ef,
        metadata={"user_id": user_id, "document_id": document_id},
    )
    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
    collection.upsert(documents=chunks, ids=ids)
    return len(chunks)


def query_document(user_id: int, document_id: int, question: str, top_k: int = 4) -> list[str]:
    """Retrieve top-k relevant chunks from a specific document."""
    col_name = _collection_name(user_id, document_id)
    try:
        collection = _client.get_collection(name=col_name, embedding_function=_ef)
    except Exception:
        return []
    results = collection.query(query_texts=[question], n_results=min(top_k, collection.count()))
    return results["documents"][0] if results["documents"] else []


def query_all_user_docs(user_id: int, document_ids: list[int], question: str, top_k: int = 4) -> list[str]:
    """Query across all user documents, merge and return top chunks."""
    all_chunks: list[tuple[float, str]] = []
    per_doc = max(1, top_k // max(len(document_ids), 1))

    for doc_id in document_ids:
        col_name = _collection_name(user_id, doc_id)
        try:
            collection = _client.get_collection(name=col_name, embedding_function=_ef)
            n = min(per_doc + 1, collection.count())
            if n == 0:
                continue
            results = collection.query(
                query_texts=[question], n_results=n, include=["documents", "distances"]
            )
            docs = results["documents"][0]
            dists = results["distances"][0]
            all_chunks.extend(zip(dists, docs))
        except Exception:
            continue

    # Sort by distance (lower = more similar), take top_k
    all_chunks.sort(key=lambda x: x[0])
    return [chunk for _, chunk in all_chunks[:top_k]]


def delete_document(user_id: int, document_id: int):
    col_name = _collection_name(user_id, document_id)
    try:
        _client.delete_collection(col_name)
    except Exception:
        pass
