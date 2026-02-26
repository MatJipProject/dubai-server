from typing import Optional
from fastapi import Form
from app.reviews.schemas import reviews_schemas as schemas
from app.restaurants.schemas import restaurants_schemas


async def parse_review_form(
    # Restaurant 필드들
    kakao_place_id: str = Form(..., description="카카오 장소 ID"),
    name: str = Form(..., description="식당 이름"),
    category: Optional[str] = Form(None, description="카테고리"),
    phone: Optional[str] = Form(None, description="전화번호"),
    place_url: Optional[str] = Form(None, description="카카오맵 링크"),
    road_address: Optional[str] = Form(None, description="도로명 주소"),
    address: Optional[str] = Form(None, description="지번 주소"),
    latitude: float = Form(..., description="위도"),
    longitude: float = Form(..., description="경도"),
    # Review 필드들
    rating: int = Form(..., ge=1, le=5, description="평점 (1~5)"),
    content: str = Form(..., description="리뷰 내용"),
) -> schemas.ReviewWithRestaurantCreate:
    """
    Form 데이터를 ReviewWithRestaurantCreate 스키마로 변환
    """
    restaurant = restaurants_schemas.RestaurantCreate(
        kakao_place_id=kakao_place_id,
        name=name,
        category=category,
        phone=phone,
        place_url=place_url,
        road_address=road_address,
        address=address,
        latitude=latitude,
        longitude=longitude,
    )
    
    return schemas.ReviewWithRestaurantCreate(
        restaurant=restaurant,
        rating=rating,
        content=content,
    )


async def parse_review_only_form(
    restaurant_id: int = Form(..., description="식당 ID"),
    rating: int = Form(..., ge=1, le=5, description="평점 (1~5)"),
    content: str = Form(..., description="리뷰 내용"),
) -> schemas.ReviewCreate:
    """
    기존 식당에 리뷰만 작성할 때 사용하는 Form 파서
    """
    return schemas.ReviewCreate(
        restaurant_id=restaurant_id,
        rating=rating,
        content=content,
    )
