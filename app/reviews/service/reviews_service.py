from sqlalchemy.orm import Session
from app.reviews.schemas import reviews_schemas as schemas
from app.reviews.crud import reviews_crud as crud
from app.restaurants.service import (
    restaurants_service as restaurant_service,
)  # 식당 서비스 재사용
from app.restaurants.schemas import restaurants_schemas as restaurant_schemas
from typing import List


async def create_review_with_restaurant(
    db: Session,
    user_id: int,
    restaurant_create: restaurant_schemas.RestaurantCreate,
    rating: int,
    content: str,
    images: List[str],
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
    # Step 2. 리뷰 작성
    # -------------------------------------------------------
    new_review = crud.create_review(
        db=db,
        user_id=user_id,
        restaurant_id=restaurant.id,  # 위에서 받은 ID 사용
        rating=rating,
        content=content,
        images=images,
    )

    return new_review


def get_reviews_by_restaurant(
    db: Session, restaurant_id: int, skip: int = 0, limit: int = 10
):
    return crud.get_reviews_by_restaurant(db, restaurant_id, skip, limit)
