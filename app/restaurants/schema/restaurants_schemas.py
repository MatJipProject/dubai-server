from typing import Optional
from pydantic import BaseModel


class RestaurantCreate(BaseModel):
    title: str  # 예: "<b>토스트카페마리</b> 강남성심병원점"
    category: str  # 예: "음식점>샌드위치"
    roadAddress: str  # 도로명 주소
    address: Optional[str] = None  # 지번 주소 (없을 수도 있음)
    mapx: str  # "1269079057" (문자열로 옴)
    mapy: str  # "374916071"


class RestaurantResponse(BaseModel):
    id: int
    unique_hash: str
    name: str
    latitude: float
    longitude: float

    class Config:
        from_attributes = True


class RestaurantNearbyResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    road_address: str
    latitude: float
    longitude: float

    # [추가된 필드]
    distance: float  # 내 위치로부터의 거리 (미터)
    rating: float = 0.0  # 평균 별점 (없으면 0.0)
    review_count: int = 0  # 리뷰 개수

    class Config:
        from_attributes = True
