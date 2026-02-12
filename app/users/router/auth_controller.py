# router.py
from fastapi import APIRouter, Depends, HTTPException, status
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
