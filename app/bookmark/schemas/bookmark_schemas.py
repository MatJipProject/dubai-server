from typing import Optional

from pydantic import BaseModel
from datetime import datetime

from app.restaurants.schemas.restaurants_schemas import RestaurantBase


# 공통 속성
class BookmarkBase(BaseModel):
    restaurant_id: int


# 프론트엔드에서 북마크 생성 요청을 보낼 때 쓸 스키마
class BookmarkCreate(BookmarkBase):
    pass


# 2. [추가] 프론트엔드에 내려줄 때 식당 정보까지 포함된 형태
class Bookmark(BookmarkBase):
    id: int
    created_at: datetime

    # DB 모델에 relationship("Restaurant") 가 걸려있으면 알아서 채워집니다!
    restaurant: Optional[RestaurantBase] = None

    class Config:
        from_attributes = True
        orm_mode = True
