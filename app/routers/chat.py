from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
import traceback
from app.db.database import DB_PATH
from app.models.schemas import ChatRequest, ChatResponse
from app.services.auth_service import get_current_user
from app.services import vector_store, rag_service

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["id"]

        if body.document_id:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id FROM documents WHERE id = ? AND user_id = ?",
                    (body.document_id, user_id),
                ) as cur:
                    doc = await cur.fetchone()
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            chunks = vector_store.query_document(user_id, body.document_id, body.question)
        else:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT id FROM documents WHERE user_id = ?", (user_id,)
                ) as cur:
                    docs = await cur.fetchall()
            if not docs:
                return ChatResponse(
                    answer="You haven't uploaded any documents yet.",
                    sources=[],
                    document_id=None,
                )
            doc_ids = [d["id"] for d in docs]
            chunks = vector_store.query_all_user_docs(user_id, doc_ids, body.question)

        answer = rag_service.generate_answer(body.question, chunks)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO chat_history (user_id, document_id, question, answer) VALUES (?, ?, ?, ?)",
                (user_id, body.document_id, body.question, answer),
            )
            await db.commit()

        return ChatResponse(
            answer=answer,
            sources=chunks[:3],
            document_id=body.document_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def chat_history(current_user: dict = Depends(get_current_user), limit: int = 20):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT ch.id, ch.question, ch.answer, ch.created_at, d.filename
                   FROM chat_history ch
                   LEFT JOIN documents d ON ch.document_id = d.id
                   WHERE ch.user_id = ?
                   ORDER BY ch.created_at DESC LIMIT ?""",
                (current_user["id"], limit),
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))