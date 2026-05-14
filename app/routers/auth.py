from fastapi import APIRouter, HTTPException, status
import aiosqlite
import traceback
from app.db.database import DB_PATH
from app.models.schemas import UserRegister, UserLogin, TokenResponse
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: UserRegister):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM users WHERE email = ?", (body.email,)) as cur:
                if await cur.fetchone():
                    raise HTTPException(status_code=400, detail="Email already registered")
            hashed = hash_password(body.password)
            cursor = await db.execute(
                "INSERT INTO users (email, hashed_password) VALUES (?, ?)",
                (body.email, hashed),
            )
            await db.commit()
            user_id = cursor.lastrowid

        token = create_access_token(user_id, body.email)
        return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, email, hashed_password FROM users WHERE email = ?", (body.email,)
            ) as cur:
                user = await cur.fetchone()

        if not user or not verify_password(body.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(user["id"], user["email"])
        return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))