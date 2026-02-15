# router.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.core.database import get_db
from app.core import security
from app.users.schemas import auth_schemas as schemas
from app.users.crud import auth_crud as crud
from app.users.service import auth_service as service
from app.config.config import settings
from sqlalchemy.orm import Session

router = APIRouter()


# 회원가입
@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.TokenResponse,
)
def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    service.check_email(user.email, db)
    email_user = service.create_user(db, user)

    access_token = security.create_access_token(data={"sub": email_user.email})
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    refresh_token = security.create_refresh_token(data={"sub": email_user.email})
    refresh_expires_in = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60

    return {
        "access_token": access_token,
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "refresh_expires_in": refresh_expires_in,
        "id": email_user.id,
        "token_type": "bearer",
    }


# 로그인 (토큰 발급)
@router.post("/signin", response_model=schemas.TokenResponse)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # form_data.username, form_data.password 로 들어옵니다.
    user = service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    refresh_token = security.create_refresh_token(data={"sub": user.email})
    refresh_expires_in = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
    return {
        "access_token": access_token,
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "refresh_expires_in": refresh_expires_in,
        "id": user.id,
        "token_type": "bearer",
    }


# 보호된 라우트 (로그인한 사용자만 접근 가능)
@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: dict = Depends(security.get_current_user)):
    return current_user


# 토큰 갱신 (Refresh Token)
@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(
    refresh_token: str = Body(..., embed=True), db: Session = Depends(get_db)
):
    """
    Refresh Token을 받아 새로운 Access Token과 Refresh Token을 발급합니다.
    Body: { "refresh_token": "..." }
    """
    # 1. 토큰 디코딩 및 검증 (만료/위조 시 security.py 내부에서 HTTPException 발생)
    email = security.decode_token(refresh_token)

    # 2. 유저 확인
    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. 새로운 토큰 발급 (Rotation)
    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    new_access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_expires
    )
    new_refresh_token = security.create_refresh_token(
        data={"sub": user.email}, expires_delta=refresh_expires
    )

    return {
        "access_token": new_access_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_token": new_refresh_token,
        "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        "id": user.id,
        "token_type": "bearer",
    }
