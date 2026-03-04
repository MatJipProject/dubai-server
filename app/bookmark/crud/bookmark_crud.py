from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import models
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, cast  # cast 추가
from geoalchemy2 import Geography  # Geography 추가
from sqlalchemy import desc
from sqlalchemy.orm import Session


# 중복 검사용: 특정 유저가 특정 식당을 찜했는지 조회
def get_bookmark(db: Session, user_id: int, restaurant_id: int):
    return (
        db.query(models.Bookmark)
        .filter(
            models.Bookmark.user_id == user_id,
            models.Bookmark.restaurant_id == restaurant_id,
        )
        .first()
    )


# 북마크 생성 (DB에 Insert)
def create_bookmark(db: Session, user_id: int, restaurant_id: int):
    db_bookmark = models.Bookmark(user_id=user_id, restaurant_id=restaurant_id)
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark


# 북마크 취소 (DB에서 Delete) - 나중에 쓰일 것을 대비해 미리 만들어둡니다.
def delete_bookmark(db: Session, db_bookmark: models.Bookmark):
    db.delete(db_bookmark)
    db.commit()


def get_bookmarks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Bookmark)
        .filter(models.Bookmark.user_id == user_id)  # 👈 내 북마크만 필터링
        .offset(skip)
        .limit(limit)
        .all()
    )
