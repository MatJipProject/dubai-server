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


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """
    DB에 등록된 식당들의 카테고리 목록을 조회합니다.
    카카오맵 기준 카테고리들을 반환합니다.
    """
    return {"categories": service.get_available_categories(db)}


@router.get("/latest", response_model=List[schemas.RestaurantListResponse])
def get_latest_restaurants(
    skip: int = Query(0, description="건너뛸 개수 (페이징)"),
    limit: int = Query(20, description="가져올 개수 (최대 50개)"),
    category: str = Query(None, description="카테고리 필터 (예: 한식, 중식, 일식, 양식, 카페, 치킨, 피자 등)"),
    db: Session = Depends(get_db),
):
    """
    최근 등록된 순으로 식당 목록을 조회합니다.
    
    카테고리 필터링 예시:
    - 한식: /latest?category=한식
    - 중식: /latest?category=중식  
    - 일식: /latest?category=일식
    - 양식: /latest?category=양식
    - 카페: /latest?category=카페
    - 치킨: /latest?category=치킨
    - 피자: /latest?category=피자
    - 분식: /latest?category=분식
    - 술집: /latest?category=술집
    """
    if limit > 50:
        limit = 50
    
    return service.get_restaurants_latest(db, skip=skip, limit=limit, category=category)


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
