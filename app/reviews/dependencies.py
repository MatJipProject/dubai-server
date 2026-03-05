from typing import Optional
from fastapi import Form, HTTPException
from pydantic import ValidationError
from app.reviews.schemas import reviews_schemas as schemas
from app.restaurants.schemas import restaurants_schemas
import json


def parse_review_form(
    request_data: str = Form(..., description="JSON 형식의 식당 및 리뷰 데이터 문자열")
) -> schemas.ReviewWithRestaurantCreate:
    """
    프론트엔드에서 'request_data'라는 폼 필드에 담아 보낸 JSON 문자열을 파싱합니다.
    """
    try:
        # 1. 문자열을 Python 딕셔너리로 변환
        parsed_dict = json.loads(request_data)

        # 2. Pydantic 스키마를 이용해 데이터 검증 및 객체 생성
        # ReviewWithRestaurantCreate 스키마 구조에 맞게 변환됩니다.
        return schemas.ReviewWithRestaurantCreate(**parsed_dict)

    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="유효한 JSON 형식이 아닙니다.")
    except ValidationError as e:
        # Pydantic 검증 실패 시 에러 반환
        raise HTTPException(status_code=422, detail=e.errors())


async def parse_review_only_form(
    restaurant_id: int = Form(..., description="식당 ID"),
    rating: int = Form(..., ge=1, le=5, description="평점 (1~5)"),
    content: str = Form(..., description="리뷰 내용"),
) -> schemas.ReviewCreate:
    """
    기존 식당에 리뷰만 작성할 때 사용하는 Form 파서
    """
    return schemas.ReviewCreate(
        restaurant_id=restaurant_id,
        rating=rating,
        content=content,
    )
