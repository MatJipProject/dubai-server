from app.config.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Iterator

DATABASE_URL = settings.DATABASE_URL

if settings.ENVIRONMENT == "PROD":
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=15,
        pool_timeout=60,
        pool_recycle=3600,
        echo=False,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=15,
        pool_timeout=60,
        pool_recycle=3600,
        echo=False,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# 반환 타입을 Generator[Session, None, None]으로 수정
def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
