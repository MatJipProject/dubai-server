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
