# crud.py
from app.models import models
from app.users.schemas import auth_schemas as schemas
from sqlalchemy.orm import Session


def check_duplicate_email(email: str, db: Session):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate, hashed_password: str):
    db_user = models.User(
        email=user.email,
        password_hash=hashed_password,
        nickname=user.username,
        birth=user.birth,
        phone=user.phone,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
