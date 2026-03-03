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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
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
    # [추가] 유저가 삭제되면 북마크도 연쇄 삭제(cascade) 되도록 설정
    bookmarks = relationship(
        "Bookmark", back_populates="user", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="user", cascade="all, delete-orphan"
    )


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
    # [추가] 식당이 삭제되면 북마크도 연쇄 삭제되도록 설정
    bookmarks = relationship(
        "Bookmark", back_populates="restaurant", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="restaurant", cascade="all, delete-orphan"
    )


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

    # 👇👇 [이 두 줄을 추가해 주세요!] 👇👇
    user = relationship("User", back_populates="reviews")
    restaurant = relationship("Restaurant", back_populates="reviews")


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    # 어떤 유저가
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 어떤 식당을
    restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 언제 찜했는지
    created_at = Column(DateTime, default=func.now())

    # 한 유저가 같은 식당을 두 번 찜할 수 없도록 중복 방지 제약조건
    __table_args__ = (
        UniqueConstraint(
            "user_id", "restaurant_id", name="uq_user_restaurant_bookmark"
        ),
    )

    # 연결 설정
    user = relationship("User", back_populates="bookmarks")
    restaurant = relationship("Restaurant", back_populates="bookmarks")
