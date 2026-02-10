import httpx
from fastapi import HTTPException
from app.config.config import settings  # .env에서 키 가져오기
from sqlalchemy.orm import Session
from app.restaurants.schemas import restaurants_schemas as schemas
from app.restaurants.crud import restaurants_crud as crud

from app.reviews.crud import reviews_crud


KAKAO_SEARCH_URL = settings.KAKAO_SEARCH_URL


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


async def search_restaurants_kakao(query: str, display: int = 5):
    """
    [카카오 API] 키워드로 음식점(FD6)과 카페(CE7)를 검색합니다.
    에러 발생 시 카카오가 보내준 상세 사유를 포함합니다.
    """
    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}

    # 1. 요청 개수 설정 (Buffer)
    buffer_size = display * 3
    if buffer_size > 45:
        buffer_size = 45

    params = {
        "query": query,
        "size": buffer_size,
        "sort": "accuracy",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(KAKAO_SEARCH_URL, headers=headers, params=params)

        # 🚨 [에러 처리 강화] 상태 코드가 200이 아니면 이유를 파헤칩니다.
        if response.status_code != 200:
            error_detail = "카카오 검색 API 호출 실패"
            try:
                # 카카오 에러 응답 파싱
                error_json = response.json()
                kakao_msg = error_json.get(
                    "message"
                )  # 에러 메시지 (예: "cannot find appkey")
                error_type = error_json.get(
                    "errorType"
                )  # 에러 타입 (예: "AccessDeniedError")

                if kakao_msg:
                    error_detail = f"카카오 API 오류: {kakao_msg} ({error_type})"
            except Exception:
                # JSON 파싱 실패 시, 응답 텍스트 원본 사용
                error_detail = f"카카오 API 오류(Raw): {response.text}"

            # 서버 로그에 찍어서 개발자가 볼 수 있게 함
            print(f"❌ {error_detail}")

            # 클라이언트(Postman/Front)에게 상세 사유 전달
            raise HTTPException(status_code=response.status_code, detail=error_detail)

        data = response.json()
        print(data)
        documents = data.get("documents", [])

        # ... (이하 필터링 로직 동일) ...
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
                }
                filtered_items.append(item)

            if len(filtered_items) >= display:
                break

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
    # 카카오 예시: "음식점 > 한식 > 육류,고기" -> "육류,고기"
    # 문자열 파싱만 조금 다듬어 줍니다.
    simple_category = item.category
    if item.category:
        parts = item.category.split(">")
        if len(parts) > 1:
            simple_category = parts[-1].strip()  # 맨 뒤에꺼 가져오고 공백 제거

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
