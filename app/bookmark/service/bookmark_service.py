import httpx
from fastapi import HTTPException, status
from app.config.config import settings  # .env에서 키 가져오기
from sqlalchemy.orm import Session
from app.bookmark.schemas import bookmark_schemas as schemas
from app.bookmark.crud import bookmark_crud as crud


def create_bookmark(db: Session, restaurant_id: int, user_id: int):
    # 1. 이미 찜한 식당인지 확인 (DB 에러 방지)
    existing_bookmark = crud.get_bookmark(
        db=db, user_id=user_id, restaurant_id=restaurant_id
    )

    if existing_bookmark:
        # 이미 찜했다면 400 Bad Request 에러를 던집니다.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 북마크한 식당입니다."
        )

    # 2. 유효한 요청이면 DB에 저장
    return crud.create_bookmark(db=db, user_id=user_id, restaurant_id=restaurant_id)


def get_my_bookmarks(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    # CRUD에게 "이 user_id의 북마크만 찾아와!" 라고 시킵니다.
    return crud.get_bookmarks_by_user(db=db, user_id=user_id, skip=skip, limit=limit)


def delete_bookmark(db: Session, user_id: int, restaurant_id: int):
    # 1. 지울 북마크가 실제로 있는지 조회 (이전에 crud.py에 만들어둔 함수 사용)
    existing_bookmark = crud.get_bookmark(
        db=db, user_id=user_id, restaurant_id=restaurant_id
    )

    # 2. 만약 찜한 적도 없는데 취소해달라고 요청이 오면 404 에러 반환
    if not existing_bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 식당의 북마크 내역을 찾을 수 없습니다.",
        )

    # 3. 존재한다면 CRUD를 호출해서 안전하게 삭제
    crud.delete_bookmark(db=db, db_bookmark=existing_bookmark)
