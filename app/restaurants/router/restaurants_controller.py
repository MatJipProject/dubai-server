from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.restaurants.schemas import restaurants_schemas as schemas
from app.restaurants.service import restaurants_service as service

router = APIRouter()


@router.get("/search")
async def search_restaurants(query: str):
    # 프론트엔드는 이 주소(GET /api/v1/restaurants/search?query=강남)를 호출
    result = await service.search_restaurants_kakao(query)
    return result


@router.get("/nearby", response_model=List[schemas.RestaurantNearbyResponse])
def get_nearby_restaurants(
    lat: float = Query(..., description="사용자 현재 위도"),
    lng: float = Query(..., description="사용자 현재 경도"),
    radius: int = Query(1000, description="검색 반경 (미터)"),
    db: Session = Depends(get_db),
):
    """
    내 주변 맛집 리스트 조회 (거리순, 별점 포함)
    """
    return service.get_nearby_restaurants(db, lat=lat, lng=lng, radius=radius)


@router.get("/{restaurant_id}", response_model=schemas.RestaurantDetailResponse)
def get_restaurant_detail(
    restaurant_id: int,
    db: Session = Depends(get_db),
):
    """
    식당 정보 + 최신 이미지 5장 + 맛보기 리뷰 3개를 한 번에 내려줍니다.
    """
    return service.get_restaurant_detail(db, restaurant_id)
