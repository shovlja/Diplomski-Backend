# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Literal

class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=2, max_length=120)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
