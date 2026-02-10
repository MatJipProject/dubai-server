from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from app.models.models import Review


def create_review(
    db: Session,
    user_id: int,
    restaurant_id: int,
    rating: int,
    content: str,
    images: list,
):
    db_obj = Review(
        user_id=user_id,
        restaurant_id=restaurant_id,
        rating=rating,
        content=content,
        images=images,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_latest_reviews_for_restaurants(
    db: Session, restaurant_ids: list[int], limit_per_restaurant: int = 2
):
    """
    [성능 최적화] 각 식당별 최신 리뷰 데이터(이미지 리스트, 리뷰 내용)를 가져옵니다.
    """
    if not restaurant_ids:
        return []

    # 1. Subquery: 각 식당별(partition_by) 최신순(order_by) 번호 매기기
    subquery = (
        db.query(
            Review.restaurant_id,
            Review.images,
            Review.content,  # [중요] 내용도 가져옴
            func.row_number()
            .over(partition_by=Review.restaurant_id, order_by=desc(Review.created_at))
            .label("rn"),
        )
        .filter(
            Review.restaurant_id.in_(restaurant_ids),
            # 이미지나 내용 둘 중 하나라도 있는 것을 가져옴 (보통 이미지를 우선시)
            Review.images.isnot(None),
        )
        .subquery()
    )

    # 2. Main Query: 상위 N개만 필터링
    results = (
        db.query(subquery.c.restaurant_id, subquery.c.images, subquery.c.content)
        .filter(subquery.c.rn <= limit_per_restaurant)
        .all()
    )

    return results


def get_reviews_by_restaurant(
    db: Session, restaurant_id: int, skip: int = 0, limit: int = 10
):
    return (
        db.query(Review)
        .filter(Review.restaurant_id == restaurant_id)
        .order_by(desc(Review.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
