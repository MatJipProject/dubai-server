import httpx
from fastapi import HTTPException
from app.config.config import settings  # .env에서 키 가져오기
from sqlalchemy.orm import Session
from app.restaurants.schemas import restaurants_schemas as schemas
from app.restaurants.crud import restaurants_crud as crud
import hashlib


NAVER_SEARCH_URL = settings.NAVER_SEARCH_URL


# 1. 허용할 카테고리 키워드 정의 (화이트리스트)
# 네이버 카테고리 문자열(예: "음식점>한식")에 이 단어들이 포함되어 있어야만 통과
FOOD_KEYWORDS = [
    "음식점",
    "식당",
    "카페",
    "베이커리",
    "디저트",
    "술집",
    "한식",
    "중식",
    "일식",
    "양식",
    "분식",
    "뷔페",
    "패스트푸드",
    "제과",
    "떡",
    "도시락",
    "피자",
    "치킨",
    "호프",
    "이자카야",
]


async def search_restaurants_by_category_only(query: str, display: int = 5):
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    # 2. 요청 개수 뻥튀기 (Buffer)
    # 필터링 과정에서 탈락하는 항목이 생기므로, 요청한 개수(display)의 3배를 가져옵니다.
    # 예: 프론트가 5개 달라고 하면, 네이버에는 15개를 달라고 요청
    buffer_display = display * 3
    if buffer_display > 100:
        buffer_display = 100  # 네이버 최대 한도가 100개

    params = {
        "query": query,  # 검색어 조작 없이 그대로 사용
        "display": buffer_display,
        "sort": "random",  # 정확도순(random) 추천 (comment는 리뷰순)
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(NAVER_SEARCH_URL, headers=headers, params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="네이버 API 호출 실패"
            )

        data = response.json()
        raw_items = data.get("items", [])

        filtered_items = []

        # 3. 카테고리 검사 로직
        for item in raw_items:
            category_str = item.get("category", "")  # 예: "스포츠,레저>요가"

            # 카테고리 문자열에 우리 키워드가 하나라도 들어있는지 확인
            is_food = any(keyword in category_str for keyword in FOOD_KEYWORDS)

            if is_food:
                filtered_items.append(item)

            # 목표 개수(display)를 채웠으면 즉시 중단 (최적화)
            if len(filtered_items) >= display:
                break

        return {
            "total": len(filtered_items),  # 실제 필터링된 개수
            "items": filtered_items,  # 딱 display 개수만큼 채워진 리스트
        }


def create_restaurant(db: Session, item: schemas.RestaurantCreate):

    # 1. 데이터 정제 (HTML 태그 제거)
    clean_name = _clean_html(item.title)

    # 2. 해시 생성을 위한 주소 선택 (도로명 우선, 없으면 지번)
    target_address = item.roadAddress if item.roadAddress else (item.address or "")
    unique_hash = _generate_hash(clean_name, target_address)

    # 3. 중복 검사 (CRUD 호출)
    existing_restaurant = crud.get_restaurant_by_hash(db, unique_hash)
    if existing_restaurant:
        # 이미 있으면 해당 정보 반환 (또는 에러 발생 선택 가능)
        return existing_restaurant

    # 4. 좌표 변환 (문자열 정수 -> WGS84 실수)
    # 네이버 제공 좌표는 10,000,000으로 나누어야 위도/경도가 됨
    try:
        lng = float(item.mapx) / 10_000_000  # 경도 (X)
        lat = float(item.mapy) / 10_000_000  # 위도 (Y)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="유효하지 않은 좌표 데이터입니다.")

    # 5. 카테고리 단순화 (선택 사항)
    # "음식점>한식>육류,고기요리" -> "육류,고기요리" (가장 세부적인 것만 저장)
    simple_category = item.category.split(">")[-1] if item.category else ""

    # 6. 최종 저장 (CRUD 호출)
    return crud.create_restaurant(
        db=db,
        name=clean_name,
        category=simple_category,
        address=item.address,
        road_address=item.roadAddress,
        lat=lat,
        lng=lng,
        unique_hash=unique_hash,
    )


def get_nearby_restaurants(db: Session, lat: float, lng: float, radius: int):
    """
    내 주변 맛집 조회 비즈니스 로직
    1. CRUD 호출하여 Raw 데이터 획득
    2. 프론트엔드 응답 포맷으로 데이터 가공
    """
    # 1. CRUD 호출
    rows = crud.get_nearby_restaurants_query(db, lat, lng, radius)

    # 2. 데이터 변환 (Tuple -> Schema Dict)
    result_list = []
    for row in rows:
        restaurant, distance, avg_rating, count = row

        # Restaurant 모델의 필드를 dict로 변환 (SQLAlchemy 객체 -> dict)
        # __dict__를 쓰거나 명시적으로 매핑
        restaurant_data = {
            "id": restaurant.id,
            "name": restaurant.name,
            "category": restaurant.category,
            "road_address": restaurant.road_address,
            "latitude": restaurant.latitude,
            "longitude": restaurant.longitude,
            # 계산된 필드 추가
            "distance": round(distance, 1),
            "rating": round(avg_rating, 1),
            "review_count": count,
        }
        result_list.append(restaurant_data)

    return result_list


def get_restaurant_detail(
    db: Session, restaurant_id: int
) -> schemas.RestaurantDetailResponse:
    """
    식당 상세 정보 조회 (북마크 제외)
    """
    # 1. 기본 정보 및 통계
    result = crud.get_restaurant_with_stats(db, restaurant_id)
    if not result:
        raise HTTPException(status_code=404, detail="식당을 찾을 수 없습니다.")

    restaurant, avg_rating, review_count = result

    # 2. 대표 이미지
    images = crud.get_restaurant_images(db, restaurant_id, limit=5)

    # 3. 응답 반환
    return schemas.RestaurantDetailResponse(
        id=restaurant.id,
        unique_hash=restaurant.unique_hash,
        name=restaurant.name,
        category=restaurant.category,
        address=restaurant.address,
        road_address=restaurant.road_address,
        latitude=restaurant.latitude,
        longitude=restaurant.longitude,
        rating=round(avg_rating, 1),
        review_count=review_count,
        images=images,
    )


def _generate_hash(name: str, address: str) -> str:
    """가게 이름 + 주소로 고유 해시 생성 (내부 함수)"""
    unique_string = f"{name.strip()}|{address.strip()}"
    return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()


def _clean_html(text: str) -> str:
    """HTML 태그 제거 (<b> 등)"""
    return text.replace("<b>", "").replace("</b>", "").strip()
