from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    chunk_count: int
    created_at: datetime


class ChatRequest(BaseModel):
    question: str
    document_id: Optional[int] = None  # None = search across all user docs


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    document_id: Optional[int]
