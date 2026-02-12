from pydantic import BaseModel
from typing import Optional


# 회원가입/로그인 시 받을 데이터
class UserCreate(BaseModel):
    username: str
    password: str
    birth: str
    phone: Optional[str] = None
    email: str


# 사용자에게 응답할 데이터 (비밀번호 제외)
class UserResponse(BaseModel):
    nickname: str
    email: str
    birth: str
    phone: str


# JWT 토큰 응답 데이터
class TokenResponse(BaseModel):
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    id: int
    token_type: str


# 토큰 페이로드 데이터
class TokenData(BaseModel):
    username: Optional[str] = None
