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
    name = Column(String(100))  # 식당 이름
    unique_hash = Column(
        String(64), unique=True, index=True, nullable=False
    )  # naver_id 대신 고유성을 보장할 식별자 생성
    category = Column(String(100))  # 음식 카테고리
    address = Column(String(255))  # 지번 주소
    road_address = Column(String(255))  # 도로명 주소
    latitude = Column(Float)  # 위도
    longitude = Column(Float)  # 경도
    # PostGIS 거리 계산용 핵심 컬럼 (SRID 4326 = WGS84)
    location = Column(Geography(geometry_type="POINT", srid=4326))
    created_at = Column(DateTime, default=func.now())  # 작성일


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
