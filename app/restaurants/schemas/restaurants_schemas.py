from typing import Optional, List
from pydantic import BaseModel, Field


# ==========================================
# 1. 요청 (Request) 스키마
# ==========================================
class RestaurantCreate(BaseModel):
    """
    카카오 검색 결과를 서비스 계층으로 넘길 때 사용하는 구조
    """

    kakao_place_id: str  # [핵심] 카카오 장소 ID (예: "18577297")
    name: str  # 식당 이름 (태그 없는 순수 텍스트)
    category: Optional[str] = None

    phone: Optional[str] = None  # [추가] 전화번호
    place_url: Optional[str] = None  # [추가] 카카오맵 상세 링크

    road_address: Optional[str] = None
    address: Optional[str] = None

    # [변경] mapx, mapy (String) -> longitude, latitude (Float)
    # 카카오 API는 위경도 좌표를 바로 줍니다.
    latitude: float  # 위도 (y)
    longitude: float  # 경도 (x)


# ==========================================
# 2. 응답 (Response) 베이스 스키마
# ==========================================
class RestaurantBase(BaseModel):
    """
    DB 모델의 컬럼들과 1:1 매핑되는 기본 스키마
    """

    id: int
    kakao_place_id: str  # [변경] unique_hash 대신 사용
    name: str
    category: Optional[str] = None

    phone: Optional[str] = None
    place_url: Optional[str] = None

    road_address: Optional[str] = None
    address: Optional[str] = None

    latitude: float
    longitude: float

    class Config:
        from_attributes = True


# ==========================================
# 3. 구체적인 응답 스키마
# ==========================================


# 리뷰 등록 등의 결과로 반환될 때 (기본 정보만 포함)
class RestaurantResponse(RestaurantBase):
    pass


# 통계 정보가 포함된 공통 부모 (Detail과 Nearby에서 상속)
class RestaurantStatsBase(RestaurantBase):
    rating: float = 0.0  # 평균 별점
    review_count: int = 0  # 리뷰 개수


# [상세 조회] 식당 상세 페이지용 (이미지 갤러리 + 맛보기 리뷰 포함)
class RestaurantDetailResponse(RestaurantStatsBase):
    # 상단 갤러리용 이미지 (5~10장)
    images: List[str] = []

    # (선택사항) 맛보기용 최신 리뷰 3개 (ReviewResponse 스키마 필요 시 import)
    # pre_reviews: List[ReviewResponse] = []


# [지도 조회] 내 주변 맛집용 (가벼운 정보 + 거리 + 썸네일)
class RestaurantNearbyResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None

    # [좌표]
    latitude: float
    longitude: float

    # [주소 정보]
    road_address: Optional[str] = None  # 도로명
    address: Optional[str] = None  # [추가] 지번 주소

    # [상세 정보]
    phone: Optional[str] = None  # [추가] 전화번호
    place_url: Optional[str] = None  # [추가] 카카오맵 링크

    # [통계 및 거리]
    distance: float
    rating: float
    review_count: int

    # [이미지 & 프리뷰]
    images: List[str] = []
    review_preview: Optional[str] = None

    class Config:
        from_attributes = True


# [최신 등록순 조회] 최근 등록된 맛집 목록용
class RestaurantListResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    
    # [주소 정보]
    road_address: Optional[str] = None
    address: Optional[str] = None
    
    # [상세 정보]
    phone: Optional[str] = None
    place_url: Optional[str] = None
    
    # [좌표]
    latitude: float
    longitude: float
    
    # [통계]
    rating: float = 0.0
    review_count: int = 0
    
    # [등록일]
    created_at: Optional[str] = None  # ISO 형식 문자열 (optional)
    
    # [이미지 썸네일]
    thumbnail: Optional[str] = None

    class Config:
        from_attributes = True
