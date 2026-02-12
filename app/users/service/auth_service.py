# service.py
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
from email_validator import validate_email, EmailNotValidError

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config.config import settings
from app.core.security import get_password_hash
from app.core import security
from app.users.schemas import auth_schemas as schemas
from app.users.crud import auth_crud as crud
from sqlalchemy.orm import Session


def check_email(email: str, db: Session):
    # 이메일 유효성 검증
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is not valid"
        )

    # 중복 이메일 체크
    if crud.check_duplicate_email(email, db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Same email is already registered",
        )

    return True


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    new_user = crud.create_user(db, user, hashed_password)
    return new_user


def authenticate_user(db: Session, email: str, password: str):
    user = crud.get_user_by_email(db, email)
    if not user:
        return False
    if not security.verify_password(password, user.password_hash):
        return False
    return user
