from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.restaurants.schemas import restaurants_schemas  # 기존 식당 스키마 재사용


# [요청] 식당 정보 + 리뷰 정보를 한 번에 받는 스키마
class ReviewWithRestaurantCreate(BaseModel):
    # 1. 식당 정보 (네이버 검색 결과 그대로)
    restaurant: restaurants_schemas.RestaurantCreate

    # 2. 리뷰 정보
    rating: int = Field(..., ge=1, le=5)  # 1~5점
    content: str


# [응답] 리뷰 조회 시 반환할 스키마
class ReviewResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    rating: int
    content: str
    images: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True
