from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.models import Restaurant, Review
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, cast  # cast 추가
from geoalchemy2 import Geography  # Geography 추가


def get_restaurant_by_hash(db: Session, unique_hash: str):
    """해시값으로 이미 등록된 식당인지 확인"""
    return db.query(Restaurant).filter(Restaurant.unique_hash == unique_hash).first()


def create_restaurant(
    db: Session,
    name: str,
    category: str,
    address: str,
    road_address: str,
    lat: float,
    lng: float,
    unique_hash: str,
):
    """DB에 식당 정보 저장"""

    # PostGIS 좌표 객체 생성 (WKT: Well-Known Text 형식)
    # POINT(경도 위도) 순서 중요!
    location_point = WKTElement(f"POINT({lng} {lat})", srid=4326)

    db_obj = Restaurant(
        unique_hash=unique_hash,
        name=name,
        category=category,
        address=address,
        road_address=road_address,
        latitude=lat,
        longitude=lng,
        location=location_point,  # PostGIS 컬럼
    )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


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
