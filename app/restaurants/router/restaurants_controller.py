from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.restaurants.schema import restaurants_schemas as schemas
from app.restaurants.service import restaurants_service as service

router = APIRouter()


@router.get("/search")
async def search_restaurants(query: str):
    # 프론트엔드는 이 주소(GET /api/v1/restaurants/search?query=강남)를 호출
    result = await service.search_restaurants_by_category_only(query)
    return result


@router.post("/", response_model=schemas.RestaurantResponse)
def register_restaurant(
    item: schemas.RestaurantCreate,
    db: Session = Depends(get_db),
):
    """
    네이버 검색 결과(Item)를 받아서 맛집으로 등록합니다.
    """
    try:
        restaurant = service.create_restaurant(db, item)
        return restaurant
    except Exception as e:
        # 로그 남기기 등을 추천
        raise HTTPException(status_code=400, detail=f"맛집 등록 실패: {str(e)}")


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
