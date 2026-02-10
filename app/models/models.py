from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Float,
    func,
)
from app.core.database import Base
from geoalchemy2 import Geometry, Geography  # PostGIS 사용을 위한 임포트


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)  # 로그인 이메일 주소
    password_hash = Column(String(555))  # 암호화된 비밀번호
    nickname = Column(String(30))  # 유저 닉네임
    birth = Column(String(10), nullable=True)  # 생년월일
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)  # 계정 활성화 여부
    created_at = Column(DateTime, default=func.now())  # 작성일


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    # [변경] unique_hash 대신 카카오의 고유 ID를 저장합니다.
    # 예: "18577297" (카카오에서 주는 id는 숫자형 문자열입니다)
    kakao_place_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), index=True)  # 식당 이름 (place_name)
    category = Column(String(100))  # 카테고리 (category_name)
    address = Column(String(255))  # 지번 주소 (address_name)
    road_address = Column(String(255))  # 도로명 주소 (road_address_name)
    # [추가] 상세 정보 및 링크
    phone = Column(String(50), nullable=True)  # 전화번호
    place_url = Column(
        String(255), nullable=True
    )  # 카카오맵 상세 링크 (http://place.map.kakao.com/...)
    latitude = Column(Float, nullable=False)  # 위도 (y)
    longitude = Column(Float, nullable=False)  # 경도 (x)
    # PostGIS 거리 계산용 (기존 유지)
    location = Column(Geography(geometry_type="POINT", srid=4326))
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 작성일
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 수정일


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # 유저 ID
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))  # 식당 ID
    rating = Column(Integer)  # 별점
    content = Column(Text)  # 리뷰 내용
    images = Column(JSON)  # 이미지 URL 목록
    created_at = Column(DateTime, default=func.now())  # 작성일
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # 수정일
