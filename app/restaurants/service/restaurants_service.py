import asyncio

import httpx
from fastapi import HTTPException
from app.config.config import settings  # .env에서 키 가져오기
from sqlalchemy.orm import Session
from app.restaurants.schemas import restaurants_schemas as schemas
from app.restaurants.crud import restaurants_crud as crud

from app.reviews.crud import reviews_crud


KAKAO_SEARCH_URL = settings.KAKAO_SEARCH_URL
NAVER_CLIENT_ID = settings.NAVER_CLIENT_ID
NAVER_CLIENT_SECRET = settings.NAVER_CLIENT_SECRET


# 1. 허용할 카테고리 키워드 정의 (화이트리스트)
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


# 1. 단일 식당의 이미지를 네이버에서 비동기로 가져오는 함수
async def fetch_naver_image_async(
    client: httpx.AsyncClient, name: str, address: str
) -> str | None:
    client_id = NAVER_CLIENT_ID
    client_secret = NAVER_CLIENT_SECRET

    if not client_id or not client_secret:
        return None

    # 🌟 [수정된 부분 시작] 🌟
    # 카카오 지번 주소("서울 강남구 역삼동 123")에서 '역삼동'만 추출
    dong = ""
    if address:
        parts = address.split()
        if len(parts) >= 3:
            dong = parts[2]  # 3번째 단어인 '동/읍/면' 추출

    # 마법의 키워드 "맛집" 추가! (예: "역삼동 땀땀 맛집")
    query = f"{dong} {name} 맛집".strip()
    # 🌟 [수정된 부분 끝] 🌟

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": query, "display": 1, "sort": "sim"}

    try:
        # 비동기로 네이버에 요청 (await)
        response = await client.get(
            "https://openapi.naver.com/v1/search/image", headers=headers, params=params
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                return data["items"][0]["link"]
    except Exception as e:
        print(f"네이버 이미지 검색 실패 ({name}): {e}")

    return None


async def search_restaurants_kakao(query: str, display: int = 5):
    """
    [카카오 API] 키워드로 음식점(FD6)과 카페(CE7)를 검색합니다.
    [네이버 API] 검색된 결과의 썸네일 이미지를 비동기로 병렬 수집하여 합칩니다.
    """
    KAKAO_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

    buffer_size = display * 3
    if buffer_size > 45:
        buffer_size = 45

    params = {
        "query": query,
        "size": buffer_size,
        "sort": "accuracy",
    }

    # --- [1단계: 카카오 API 검색] ---
    async with httpx.AsyncClient() as client:
        response = await client.get(KAKAO_SEARCH_URL, headers=headers, params=params)

        if response.status_code != 200:
            error_detail = "카카오 검색 API 호출 실패"
            try:
                error_json = response.json()
                kakao_msg = error_json.get("message")
                error_type = error_json.get("errorType")
                if kakao_msg:
                    error_detail = f"카카오 API 오류: {kakao_msg} ({error_type})"
            except Exception:
                error_detail = f"카카오 API 오류(Raw): {response.text}"

            print(f"❌ {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        data = response.json()
        documents = data.get("documents", [])

    # --- [2단계: 카카오 결과 파싱 및 필터링] ---
    filtered_items = []
    target_groups = ["FD6", "CE7"]

    for doc in documents:
        if doc.get("category_group_code") in target_groups:
            item = {
                "kakao_place_id": doc["id"],
                "name": doc["place_name"],
                "category": doc["category_name"],
                "phone": doc["phone"],
                "place_url": doc["place_url"],
                "road_address": doc["road_address_name"],
                "address": doc["address_name"],
                "latitude": float(doc["y"]),
                "longitude": float(doc["x"]),
                "image_url": None,  # 👈 일단 빈칸으로 만들어 둡니다.
            }
            filtered_items.append(item)

        if len(filtered_items) >= display:
            break

    # --- [3단계: 네이버 이미지 비동기 병렬 검색 (핵심!)] ---
    if filtered_items:
        async with httpx.AsyncClient() as client:
            # 1. 해야 할 작업(Task) 리스트 만들기
            tasks = [
                fetch_naver_image_async(client, item["name"], item["address"])
                for item in filtered_items
            ]

            # 2. 동시에 네이버로 검색
            images = await asyncio.gather(*tasks)

            # 3. 받아온 이미지를 filtered_items에 순서대로 꽂아주기
            for i, item in enumerate(filtered_items):
                item["image_url"] = images[i]

    # 최종 결과 반환
    return {"total": len(filtered_items), "items": filtered_items}


def create_restaurant(db: Session, item: schemas.RestaurantCreate):
    """
    카카오 검색 결과를 DB에 저장합니다.
    """

    # 1. 중복 검사 (카카오 고유 ID 사용)
    # 더 이상 복잡한 주소 해시(unique_hash)를 만들 필요가 없습니다.
    existing_restaurant = crud.get_restaurant_by_kakao_id(db, item.kakao_place_id)

    if existing_restaurant:
        return existing_restaurant

    # 2. 카테고리 단순화
    # 카카오 예시: "음식점 > 한식 > 육류,고기" -> "한식" 추출
    # 단일 항목("음식점")만 올 경우 "기타"로 분류
    simple_category = "기타"  # 기본값을 '기타'로 설정

    if item.category:
        # '>' 기준으로 쪼개고 앞뒤 공백 제거
        parts = [part.strip() for part in item.category.split(">")]

        # "음식점 > 한식" 처럼 2개 이상일 경우 두 번째(인덱스 1) 값을 가져옴
        if len(parts) >= 2:
            simple_category = parts[1]
        # "음식점" 처럼 1개만 있을 때는 기본값인 "기타"가 그대로 유지됨

    # 3. 좌표 변환 (문자열 -> WGS84 Point)
    # 카카오 API는 이미 WGS84 좌표를 제공하므로 10,000,000으로 나눌 필요가 없습니다!
    # 다만 PostGIS 저장을 위해 WKT 포맷 문자열 생성은 필요합니다.
    point_wkt = f"POINT({item.longitude} {item.latitude})"

    # 4. 최종 저장 (CRUD 호출)
    return crud.create_restaurant(
        db=db,
        kakao_place_id=item.kakao_place_id,
        name=item.name,  # 태그 없는 깔끔한 이름
        category=simple_category,
        address=item.address,
        road_address=item.road_address,
        phone=item.phone,  # 전화번호 추가
        place_url=item.place_url,  # 링크 추가
        lat=item.latitude,  # 계산 없이 그대로 사용
        lng=item.longitude,  # 계산 없이 그대로 사용
        location_wkt=point_wkt,  # PostGIS용 WKT
        image_url=item.image_url,
    )


def get_nearby_restaurants(db: Session, lat: float, lng: float, radius: int):
    # 1. 주변 식당 조회 (쿼리 1번)
    rows = crud.get_nearby_restaurants_query(db, lat, lng, radius)

    if not rows:
        return []

    # 2. 식당 ID 추출
    restaurant_ids = [row[0].id for row in rows]

    # 3. 리뷰 데이터 Bulk 조회 (쿼리 2번 - 이미지 + 텍스트)
    reviews_data = reviews_crud.get_latest_reviews_for_restaurants(db, restaurant_ids)

    # 4. 데이터 매핑 (Dictionary 구조 잡기)
    # 목표 구조: { 식당ID : {"images": ["url1", "url2"], "preview": "맛있어요..."} }
    extra_data = {rid: {"images": [], "preview": None} for rid in restaurant_ids}

    for r_id, r_imgs, r_content in reviews_data:
        target = extra_data[r_id]

        # (A) 이미지 수집 (최대 2개)
        # r_imgs는 ["url1", "url2"] 형태의 리스트이거나 None
        if len(target["images"]) < 2 and r_imgs:
            for img in r_imgs:
                if len(target["images"]) >= 2:
                    break
                target["images"].append(img)

        # (B) 리뷰 프리뷰 설정 (가장 최신 것 1개만 설정하고 끝)
        # 쿼리가 이미 최신순 정렬되어 있으므로, 먼저 잡히는 게 최신임.
        if target["preview"] is None and r_content:
            # 텍스트가 길면 50자에서 자르고 "..." 붙이기
            text = r_content
            if len(text) > 50:
                text = text[:50] + "..."
            target["preview"] = text

    # 5. 최종 응답 데이터 조립
    result_list = []
    for row in rows:
        restaurant, distance, avg_rating, count = row

        # 미리 준비해둔 추가 데이터 가져오기
        extra = extra_data.get(restaurant.id, {"images": [], "preview": None})

        result_list.append(
            {
                "id": restaurant.id,
                "name": restaurant.name,
                "category": restaurant.category,
                # [좌표]
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude,
                # [주소 및 상세]
                "road_address": restaurant.road_address,
                "address": restaurant.address,
                "phone": restaurant.phone,
                "place_url": restaurant.place_url,
                "image_url": restaurant.image_url,
                # [통계]
                "distance": round(distance, 1),
                "rating": round(avg_rating, 1),
                "review_count": count,
                # [UX 데이터]
                "images": extra["images"],
                "review_preview": extra["preview"],
            }
        )

    return result_list


def get_restaurant_detail(
    db: Session, restaurant_id: int
) -> schemas.RestaurantDetailResponse:
    # 1. 식당 기본 정보 (평점 포함)
    restaurant = crud.get_restaurant_with_stats(db, restaurant_id)

    # 2. 상단 갤러리용 이미지 (최신 5장)
    images = crud.get_restaurant_images(db, restaurant_id, limit=5)

    # 3. 하단 맛보기 리뷰 (최신 3개만) -> 더 보고 싶으면 리뷰 목록 API 호출
    recent_reviews = reviews_crud.get_reviews_by_restaurant(
        db, restaurant_id, skip=0, limit=3
    )

    return {
        **restaurant.__dict__,  # 식당 객체 풀기
        "images": images,
        "pre_reviews": recent_reviews,  # 맛보기 리뷰 리스트
    }


def get_restaurants_latest(
    db: Session, skip: int = 0, limit: int = 20, category: str = None
) -> list[schemas.RestaurantListResponse]:
    """
    최근 등록된 순으로 식당 목록을 조회합니다.
    - 식당 테이블에 image_url이 있으면 바로 사용하고,
    - 없을 때만 리뷰 사진을 조회하여 성능을 최적화합니다.
    """
    # 1. 최신 등록순으로 식당 조회 (평점, 리뷰수 포함)
    rows = crud.get_restaurants_by_latest(db, skip, limit, category)

    if not rows:
        return []

    # 2. [최적화 포인트] 식당 테이블에 image_url이 '없는' 식당의 ID만 골라냅니다.
    missing_image_ids = [row[0].id for row in rows if not row[0].image_url]

    # 3. 사진이 없는 식당들에 대해서만 리뷰 사진을 조회 (벌크 쿼리 최소화)
    thumbnail_map = {}
    if missing_image_ids:
        thumbnail_data = crud.get_latest_images_for_restaurants(
            db, missing_image_ids, 1
        )
        for r_id, images in thumbnail_data:
            if images and len(images) > 0:
                thumbnail_map[r_id] = images[0]

    # 4. 응답 데이터 조립
    result_list = []
    for row in rows:
        restaurant, avg_rating, review_count = row

        # created_at 안전 처리
        created_at_str = (
            restaurant.created_at.isoformat() if restaurant.created_at else None
        )

        # 🌟 핵심: 1순위는 식당의 image_url, 2순위는 리뷰에서 찾은 사진
        final_thumbnail = restaurant.image_url or thumbnail_map.get(restaurant.id)

        result_list.append(
            {
                "id": restaurant.id,
                "name": restaurant.name,
                "category": restaurant.category,
                "road_address": restaurant.road_address,
                "address": restaurant.address,
                "phone": restaurant.phone,
                "place_url": restaurant.place_url,
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude,
                "rating": round(avg_rating, 1) if avg_rating else 0.0,
                "review_count": review_count or 0,
                "created_at": created_at_str,
                "thumbnail": final_thumbnail,
            }
        )

    return result_list


def get_available_categories(db: Session) -> list[str]:
    """
    DB에 등록된 식당들의 카테고리 목록을 조회합니다.
    """
    return crud.get_available_categories(db)


def get_trending_restaurants(db: Session, limit: int = 10):
    # 나중에 여기에 "최근 7일 내의 북마크만 카운트" 같은 복잡한 비즈니스 로직을 추가할 수 있습니다.
    return crud.get_trending_restaurants(db=db, limit=limit)
