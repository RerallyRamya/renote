# ReNote RAG Backend

A FastAPI backend that lets users upload PDF/TXT documents and chat with them using a RAG (Retrieval-Augmented Generation) pipeline.

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
cp .env.example .env
# Fill in your ANTHROPIC_API_KEY in .env
docker-compose up --build
```

### Option 2 — Local Python

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY=AIzaSyBvZTHLqACKPDGQ1pGLP8pSA4ibQXxA3hk
export SECRET_KEY=lalaLand

uvicorn app.main:app --reload
```

API is live at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

---

## API Overview

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/auth/register` | No | Register & get JWT |
| POST | `/auth/login` | No | Login & get JWT |
| POST | `/documents/upload` | Yes | Upload PDF or TXT |
| GET | `/documents/` | Yes | List your documents |
| DELETE | `/documents/{id}` | Yes | Delete a document |
| POST | `/chat/` | Yes | Ask a question |
| GET | `/chat/history` | Yes | View past Q&A |

All protected endpoints require: `Authorization: Bearer <token>`

### Chat request body
```json
{
  "question": "What are the key findings?",
  "document_id": 1          // optional — omit to search all your docs
}
```

### Chat response
```json
{
  "answer": "The key findings are...",
  "sources": ["excerpt 1...", "excerpt 2...", "excerpt 3..."],
  "document_id": 1
}
```

---

## Design Decisions

### Authentication
**JWT (python-jose) + bcrypt (passlib)** — stateless, standard, no extra infra needed. Tokens expire in 24 hours.

### Database
**SQLite via aiosqlite** — zero-config, fully async, perfect for a local service. Stores users, document metadata, and chat history. For production, swap to Postgres with minimal changes.

### Document Processing
**pypdf** for PDF extraction — pure Python, no system deps (vs. pdfminer or Tesseract). Text is split into 500-word overlapping chunks (50-word overlap) to preserve context across chunk boundaries.

### Embeddings & Vector Store
**ChromaDB** (persistent, local) + **sentence-transformers `all-MiniLM-L6-v2`** — completely free, runs on CPU, produces good semantic embeddings. No API key or external service needed. Each document gets its own Chroma collection so user isolation is enforced at the storage level.

### LLM
**Anthropic Claude Haiku** (`claude-haiku-4-5-20251001`) — the fastest and cheapest Claude model, ideal for low-latency Q&A. The system prompt strictly grounds answers in retrieved context, and the model is instructed to say when it can't find an answer rather than hallucinate.

### RAG Pipeline
1. Upload → extract text → chunk → embed → store in ChromaDB
2. Query → embed question → top-4 nearest chunks retrieved → fed to Claude with context
3. Multi-document mode: queries each document collection, merges results by similarity distance, picks global top-4

### Security
- Passwords bcrypt-hashed, never stored in plain text
- JWT signed with a configurable secret key
- Document access enforced by `user_id` check on every query — users can only see and query their own documents
- File size capped at 10 MB; only PDF and TXT accepted

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | **required** | Your Anthropic API key |
| `SECRET_KEY` | `change-me-in-production-please` | JWT signing secret |
| `DB_PATH` | `renote.db` | SQLite database path |
| `CHROMA_PATH` | `./chroma_store` | ChromaDB persistence directory |
| `CHUNK_SIZE` | `500` | Words per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap words between chunks |
| `LLM_MODEL` | `claude-haiku-4-5-20251001` | Anthropic model to use |

---

## Testing

Import `renote_api.postman_collection.json` into Postman. The Register and Login requests automatically save the JWT to the `token` collection variable, so subsequent requests are pre-authorized.
