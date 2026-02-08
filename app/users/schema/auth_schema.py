from pydantic import BaseModel
from typing import Optional

# 회원가입/로그인 시 받을 데이터
class UserCreate(BaseModel):
    username: str
    password: str
    birth: str
    phone: str
    email: Optional[str] = None

# 사용자에게 응답할 데이터 (비밀번호 제외)
class UserResponse(BaseModel):
    username: str
    email: Optional[str] = None

# JWT 토큰 응답 데이터
class Token(BaseModel):
    access_token: str
    token_type: str

# 토큰 페이로드 데이터
class TokenData(BaseModel):
    username: Optional[str] = None