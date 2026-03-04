from typing import Optional

from fastapi import Depends, HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from app.config.config import settings
from sqlalchemy.orm import Session
from app.users.crud import auth_crud as crud
from app.core.database import get_db
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/signin")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/signin", auto_error=False
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str, key: str = settings.SECRET_KEY):
    try:
        payload = jwt.decode(token, key, algorithms=[ALGORITHM])
        data = payload.get("sub")
        return data
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    try:
        email = decode_token(token)
        user = crud.get_user_by_email(db, email=email)
        if user is None:
            raise HTTPException(status_code=401, detail="User is None")
        if user.is_active is False:
            raise HTTPException(status_code=401, detail="User is Deleted")
        return user
    except JWTError as e:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """
    선택적 유저 인증 의존성 함수
    - 로그인한 유저: 정상적으로 User 객체 반환
    - 비로그인 유저 또는 토큰 만료: 에러 없이 그냥 None 반환
    """
    # 1. 헤더에 토큰이 아예 없으면 조용히 None을 반환하고 통과시킵니다.
    if not token:
        return None

    try:
        # 2. 토큰 해독
        email = decode_token(token)
        if not email:
            return None

        # 3. DB에서 유저 조회
        user = crud.get_user_by_email(db, email=email)

        # 4. 유저가 없거나 탈퇴(is_active=False) 상태여도 에러 내지 않고 None 반환
        if user is None or user.is_active is False:
            return None

        return user

    except JWTError:
        # 🚨 [핵심 2] 토큰이 만료되었거나 조작되었더라도 401 에러를 던지지 않습니다!
        # 그냥 "비로그인 상태"로 취급해서 통과시킵니다.
        return None
