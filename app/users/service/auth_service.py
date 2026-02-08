# service.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config.config import settings
from app.users.schema import auth_schema as schemas
from app.users.crud import auth_crud as crud

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정 (토큰 발급 URL 지정)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 1. 비밀번호 관련 로직
def _hash_password_for_bcrypt(password: str) -> str:
    """bcrypt의 72바이트 제한을 해결하기 위해 SHA256으로 먼저 해시"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    # 입력받은 비밀번호를 SHA256으로 해시한 후 bcrypt와 비교
    processed_password = _hash_password_for_bcrypt(plain_password)
    return pwd_context.verify(processed_password, hashed_password)

def get_password_hash(password):
    # 비밀번호를 먼저 SHA256으로 해시한 후 bcrypt 적용
    processed_password = _hash_password_for_bcrypt(password)
    return pwd_context.hash(processed_password)

# 2. JWT 토큰 생성 로직
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# 3. 사용자 인증 (로그인 시 사용)
def authenticate_user(username: str, password: str):
    user = crud.get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

# 4. 현재 로그인한 사용자 가져오기 (의존성 주입용)
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user