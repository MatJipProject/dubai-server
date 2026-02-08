# router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.users.schema import auth_schema as schemas
from app.users.crud import auth_crud as crud
from app.users.service import auth_service as service
from app.config.config import settings


router = APIRouter()

# 회원가입
@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate):
    db_user = crud.get_user_by_username(user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pw = service.get_password_hash(user.password)
    return crud.create_user(user=user, hashed_password=hashed_pw)

# 로그인 (토큰 발급)
@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # form_data.username, form_data.password 로 들어옵니다.
    user = service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = service.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 보호된 라우트 (로그인한 사용자만 접근 가능)
@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: dict = Depends(service.get_current_user)):
    return current_user