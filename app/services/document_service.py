import os
import re
from io import BytesIO
from typing import Union
import pypdf


CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))       # words per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))  # word overlap


def extract_text(content: bytes, filename: str) -> str:
    """Extract raw text from PDF or TXT bytes."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        reader = pypdf.PdfReader(BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    elif ext == ".txt":
        return content.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def clean_text(text: str) -> str:
    """Normalise whitespace."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks


def process_document(content: bytes, filename: str) -> list[str]:
    """Full pipeline: extract → clean → chunk."""
    raw = extract_text(content, filename)
    cleaned = clean_text(raw)
    chunks = chunk_text(cleaned)
    return chunks
