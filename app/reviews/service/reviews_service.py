from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.reviews.schemas import reviews_schemas as schemas
from app.reviews.crud import reviews_crud as crud
from app.restaurants.service import (
    restaurants_service as restaurant_service,
)  # 식당 서비스 재사용
from app.restaurants.schemas import restaurants_schemas as restaurant_schemas
from typing import List, Optional


async def create_review_with_restaurant(
    db: Session,
    user_id: int,
    restaurant_create: restaurant_schemas.RestaurantCreate,
    rating: Optional[int] = None,
    content: Optional[str] = None,
    images: List[str] = [],
):
    """
    식당 등록(또는 조회) + 리뷰 작성을 한 번에 처리
    """
    # -------------------------------------------------------
    # Step 1. 식당 처리 (Get or Create)
    # -------------------------------------------------------
    # 기존 만들어둔 식당 등록 로직을 그대로 호출합니다.
    # 내부적으로 중복 체크를 다 하므로, 결과는 무조건 'DB에 저장된 식당 객체'입니다.
    restaurant = restaurant_service.create_restaurant(db, restaurant_create)

    # -------------------------------------------------------
    # Step 2. 리뷰 작성 (데이터가 있을 때만!)
    # -------------------------------------------------------
    new_review = None

    # 별점(rating)이 들어왔다면 리뷰를 작성하는 것으로 간주합니다.
    if rating is not None:
        last_review = crud.get_latest_review_by_user_and_restaurant(
            db, user_id, restaurant.id
        )

        # 🌟 2. 서비스 계층은 비즈니스 로직(검증)만 담당!
        if last_review:
            # (UTC 시간 기준 방어 로직 예시 - DB 설정에 따라 timezone 고려 필요)
            # 현재는 naive datetime을 쓴다고 가정
            time_diff = datetime.now() - last_review.created_at

            if time_diff < timedelta(days=1):
                raise HTTPException(
                    status_code=400,
                    detail="동일한 식당에는 24시간에 한 번만 리뷰를 남길 수 있습니다.",
                )

        new_review = crud.create_review(
            db=db,
            user_id=user_id,
            restaurant_id=restaurant.id,
            rating=rating,
            content=content or "",  # 내용이 없으면 빈 문자열 처리
            images=images,
        )

    # -------------------------------------------------------
    # Step 3. 결과 반환 (식당 정보 + 작성된 리뷰 정보)
    # -------------------------------------------------------
    return {
        "message": "등록이 완료되었습니다.",
        "restaurant": restaurant,
        "review": new_review,  # 리뷰 안 썼으면 None이 들어감
    }


def get_reviews_by_restaurant(
    db: Session, restaurant_id: int, skip: int = 0, limit: int = 10
):
    return crud.get_reviews_by_restaurant(db, restaurant_id, skip, limit)


async def create_review_only(
    db: Session,
    user_id: int,
    restaurant_id: int,
    rating: int,
    content: str,
    images: List[str],
):
    """
    기존 식당에 리뷰만 작성
    """
    # 1. 방금 만든 CRUD 함수 재사용! (가장 최근 리뷰 조회)
    last_review = crud.get_latest_review_by_user_and_restaurant(
        db=db, user_id=user_id, restaurant_id=restaurant_id
    )

    # 2. 비즈니스 로직: 24시간이 지났는지 검증
    if last_review:
        # 주의: DB의 created_at과 서버의 datetime.now()의 타임존(UTC/KST)이 같아야 합니다.
        time_diff = datetime.now() - last_review.created_at

        if time_diff < timedelta(days=1):
            raise HTTPException(
                status_code=400,
                detail="동일한 식당에는 24시간에 한 번만 리뷰를 남길 수 있습니다.",
            )

    # 3. 검증 통과 시 정상적으로 리뷰 생성
    return crud.create_review(
        db=db,
        user_id=user_id,
        restaurant_id=restaurant_id,
        rating=rating,
        content=content,
        images=images,
    )
