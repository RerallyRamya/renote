from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import aiosqlite
from app.db.database import DB_PATH
from app.models.schemas import DocumentResponse
from app.services.auth_service import get_current_user
from app.services.document_service import process_document
from app.services import vector_store

router = APIRouter()

ALLOWED_TYPES = {".pdf", ".txt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    import os
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    try:
        chunks = process_document(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process document: {e}")

    if not chunks:
        raise HTTPException(status_code=422, detail="Document appears to be empty or unreadable")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "INSERT INTO documents (user_id, filename, file_type, chunk_count) VALUES (?, ?, ?, ?)",
            (current_user["id"], file.filename, ext.lstrip("."), len(chunks)),
        )
        await db.commit()
        doc_id = cursor.lastrowid
        async with db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)) as cur:
            doc = await cur.fetchone()

    vector_store.upsert_chunks(current_user["id"], doc_id, chunks)

    return DocumentResponse(
        id=doc["id"],
        filename=doc["filename"],
        file_type=doc["file_type"],
        chunk_count=doc["chunk_count"],
        created_at=doc["created_at"],
    )


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC",
            (current_user["id"],),
        ) as cur:
            docs = await cur.fetchall()
    return [
        DocumentResponse(
            id=d["id"],
            filename=d["filename"],
            file_type=d["file_type"],
            chunk_count=d["chunk_count"],
            created_at=d["created_at"],
        )
        for d in docs
    ]


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: int, current_user: dict = Depends(get_current_user)):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id FROM documents WHERE id = ? AND user_id = ?",
            (document_id, current_user["id"]),
        ) as cur:
            doc = await cur.fetchone()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        await db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        await db.commit()

    vector_store.delete_document(current_user["id"], document_id)
