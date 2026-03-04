from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.bookmark.schemas import bookmark_schemas as schemas
from app.bookmark.service import bookmark_service as service
from app.models.models import User

router = APIRouter()


@router.post("/", response_model=schemas.Bookmark)
def create_bookmark(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):

    return service.create_bookmark(
        db=db, restaurant_id=restaurant_id, user_id=current_user.id
    )


@router.get("/me", response_model=List[schemas.Bookmark])
def read_my_bookmarks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        security.get_current_user
    ),  # 👈 핵심: 토큰에서 내 정보 빼오기
):
    """
    현재 로그인한 사용자의 북마크(찜한 식당) 목록을 조회합니다.
    """
    # 내 user_id를 서비스 레이어로 넘겨줍니다.
    bookmarks = service.get_my_bookmarks(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return bookmarks


@router.delete("/{restaurant_id}")
def delete_my_bookmark(
    restaurant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user),  # 👈 내 정보 빼오기
):
    """
    현재 로그인한 사용자의 특정 식당 북마크를 취소(삭제)합니다.
    """
    service.delete_bookmark(db=db, user_id=current_user.id, restaurant_id=restaurant_id)

    # 프론트엔드가 처리하기 편하게 성공 메시지를 내려줍니다.
    return {"message": "북마크가 성공적으로 취소되었습니다."}
