from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.models import Restaurant, Review
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, cast  # cast 추가
from geoalchemy2 import Geography  # Geography 추가
from sqlalchemy import desc


def get_restaurant_by_kakao_id(db: Session, kakao_place_id: str):
    return (
        db.query(Restaurant).filter(Restaurant.kakao_place_id == kakao_place_id).first()
    )


def create_restaurant(
    db: Session,
    kakao_place_id: str,
    name: str,
    category: str,
    address: str,
    road_address: str,
    phone: str,
    place_url: str,
    lat: float,
    lng: float,
    location_wkt: str,
):
    db_item = Restaurant(
        kakao_place_id=kakao_place_id,
        name=name,
        category=category,
        address=address,
        road_address=road_address,
        phone=phone,
        place_url=place_url,
        latitude=lat,
        longitude=lng,
        location=WKTElement(location_wkt, srid=4326),
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_nearby_restaurants_query(
    db: Session, lat: float, lng: float, radius: int = 1000, limit: int = 20
):
    """
    DB에서 반경 내 식당과 평점 정보를 조회합니다.
    반환값: (Restaurant객체, 거리, 평점, 리뷰수) 튜플의 리스트
    """
    # 1. 내 위치 포인트 생성
    # WKTElement 자체는 Geometry로 인식될 수 있으므로 아래에서 캐스팅합니다.
    user_location_shape = WKTElement(f"POINT({lng} {lat})", srid=4326)

    # 2. Geometry -> Geography로 명시적 형변환
    # PostGIS 함수들이 타입을 헷갈리지 않게 확실하게 Geography로 바꿔줍니다.
    user_geography = cast(user_location_shape, Geography(srid=4326))

    return (
        db.query(
            Restaurant,
            # Geography 타입끼리 비교하면 자동으로 미터 단위 거리가 나옵니다.
            func.ST_Distance(Restaurant.location, user_geography).label("distance"),
            func.coalesce(func.avg(Review.rating), 0.0).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .outerjoin(Review, Restaurant.id == Review.restaurant_id)
        .filter(
            # "내 위치에서 radius 미터 안에 있는가?"를 인덱스를 타서 검색합니다.
            func.ST_DWithin(Restaurant.location, user_geography, radius)
        )
        .group_by(Restaurant.id)
        .order_by("distance")
        .limit(limit)
        .all()
    )


def get_restaurant_with_stats(db: Session, restaurant_id: int):
    return (
        db.query(
            Restaurant,
            # 1. 평균 별점: 리뷰가 없으면 NULL이 나오므로 0.0으로 변환
            func.coalesce(func.avg(Review.rating), 0.0).label("avg_rating"),
            # 2. 리뷰 개수: Review.id를 카운트
            func.count(Review.id).label("review_count"),
        )
        .outerjoin(
            # 식당에 리뷰가 하나도 없어도 식당 정보는 나와야 하므로 outerjoin 사용
            Review,
            Restaurant.id == Review.restaurant_id,
        )
        .filter(Restaurant.id == restaurant_id)
        .group_by(
            # 집계 함수(avg, count)를 제외한 나머지 컬럼으로 그룹화
            Restaurant.id
        )
        .first()
    )


def get_restaurant_images(db: Session, restaurant_id: int, limit: int) -> list[str]:
    """
    특정 식당의 리뷰들 중에서 이미지가 있는 것들만 최신순으로 가져와서
    URL 리스트로 평탄화(Flatten)하여 반환합니다.
    """
    # 1. 이미지가 포함된 리뷰만 최신순으로 조회
    # (사진 1장에 리뷰 1개가 아니라, 리뷰 1개에 사진이 여러 장일 수 있으므로 넉넉하게 limit * 2만큼 조회)
    reviews = (
        db.query(Review)
        .filter(
            Review.restaurant_id == restaurant_id,
            Review.images.isnot(None),  # NULL 제외
        )
        .order_by(desc(Review.created_at))
        .limit(limit * 2)
        .all()
    )

    collected_images = []

    for review in reviews:
        # review.images는 ["url1", "url2"] 형태의 리스트라고 가정
        if review.images:
            # 리스트를 풀어서 하나씩 추가 (extend)
            collected_images.extend(review.images)

        # 목표 개수(limit)를 채우면 즉시 중단 (성능 최적화)
        if len(collected_images) >= limit:
            break

    # 정확히 limit 개수만큼만 잘라서 반환
    return collected_images[:limit]


def get_latest_images_for_restaurants(
    db: Session, restaurant_ids: list[int], limit_per_restaurant: int = 2
):
    """
    [성능 최적화] 각 식당별로 이미지가 있는 최신 리뷰를 딱 N개씩만 가져옵니다.
    """
    if not restaurant_ids:
        return []

    # 1. Subquery: 각 식당별로(partition_by) 최신순 번호(rn)를 매김
    subquery = (
        db.query(
            Review.restaurant_id,
            Review.images,
            func.row_number()
            .over(partition_by=Review.restaurant_id, order_by=desc(Review.created_at))
            .label("rn"),
        )
        .filter(Review.restaurant_id.in_(restaurant_ids), Review.images.isnot(None))
        .subquery()
    )

    # 2. Main Query: 번호(rn)가 limit_per_restaurant 이하인 것만 필터링
    results = (
        db.query(subquery.c.restaurant_id, subquery.c.images)
        .filter(subquery.c.rn <= limit_per_restaurant)
        .all()
    )

    return results


def get_restaurants_by_latest(
    db: Session, skip: int = 0, limit: int = 20, category: str = None
):
    """
    최근 등록된 순으로 식당 목록을 조회합니다.
    평점과 리뷰 수도 함께 반환합니다.
    카테고리 필터링 옵션 추가.
    """
    query = (
        db.query(
            Restaurant,
            func.coalesce(func.avg(Review.rating), 0.0).label("avg_rating"),
            func.count(Review.id).label("review_count"),
        )
        .outerjoin(Review, Restaurant.id == Review.restaurant_id)
    )
    
    # 카테고리 필터링 (카카오맵 카테고리 기준)
    if category:
        # 카테고리가 포함된 식당 필터링 (부분 일치)
        query = query.filter(Restaurant.category.ilike(f"%{category}%"))
    
    return (
        query
        .group_by(Restaurant.id)
        .order_by(desc(Restaurant.created_at))  # 최신 등록순
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_restaurant_thumbnail(db: Session, restaurant_id: int) -> str:
    """
    특정 식당의 첫 번째 이미지를 썸네일로 반환합니다.
    """
    review = (
        db.query(Review)
        .filter(
            Review.restaurant_id == restaurant_id,
            Review.images.isnot(None),
        )
        .order_by(desc(Review.created_at))
        .first()
    )
    
    if review and review.images and len(review.images) > 0:
        return review.images[0]
    return None


def get_available_categories(db: Session):
    """
    DB에 등록된 식당들의 카테고리 목록을 조회합니다.
    카카오맵 기준 카테고리들을 중복 제거하여 반환합니다.
    """
    categories = (
        db.query(Restaurant.category)
        .filter(Restaurant.category.isnot(None))
        .distinct()
        .all()
    )
    
    # 카테고리를 파싱하여 주요 카테고리만 추출
    category_set = set()
    for (category,) in categories:
        if category:
            # "음식점 > 한식 > 육류,고기" -> ["음식점", "한식", "육류,고기"]
            parts = [part.strip() for part in category.split(">")]
            for part in parts:
                if part and part not in ["음식점", "식당"]:  # 일반적인 단어 제외
                    category_set.add(part)
    
    return sorted(list(category_set))
