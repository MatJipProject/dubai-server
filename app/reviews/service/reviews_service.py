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
    return crud.create_review(
        db=db,
        user_id=user_id,
        restaurant_id=restaurant_id,
        rating=rating,
        content=content,
        images=images,
    )
