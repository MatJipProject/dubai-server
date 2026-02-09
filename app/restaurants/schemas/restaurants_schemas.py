from typing import Optional, List
from pydantic import BaseModel


# ==========================================
# 1. 요청 (Request) 스키마
# ==========================================
class RestaurantCreate(BaseModel):
    title: str  # "<b>토스트...</b>"
    category: str  # "음식점>샌드위치"
    roadAddress: str  # 도로명 주소
    address: Optional[str] = None
    mapx: str  # "1269079057"
    mapy: str  # "374916071"


# ==========================================
# 2. 응답 (Response) 베이스 스키마
# ==========================================
# 모든 응답 모델이 공통으로 가지는 DB 필드들입니다.
class RestaurantBase(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    road_address: str
    address: Optional[str] = None
    latitude: float
    longitude: float

    class Config:
        from_attributes = True  # ORM 객체 매핑 허용 (한 번만 선언)


# ==========================================
# 3. 구체적인 응답 스키마 (상속 활용)
# ==========================================


# 기본 등록 응답 (Base + unique_hash)
class RestaurantResponse(RestaurantBase):
    unique_hash: str


# 별점/리뷰 통계가 포함된 중간 모델 (Nearby와 Detail의 공통 부모)
class RestaurantStatsBase(RestaurantBase):
    rating: float = 0.0  # 평균 별점
    review_count: int = 0  # 리뷰 개수


# 내 주변 맛집 응답 (Stats + 거리)
class RestaurantNearbyResponse(RestaurantStatsBase):
    distance: float  # 거리 (미터)


# 식당 상세 조회 응답 (Stats + 이미지 등 추가 정보)
class RestaurantDetailResponse(RestaurantStatsBase):
    # (필요 없다면 pass로 비워두셔도 상속 덕분에 필드는 다 존재합니다)
    images: List[str] = []
