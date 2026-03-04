from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import delete_image_from_supabase, upload_image_to_supabase
from app.reviews.schemas import reviews_schemas as schemas
from app.reviews.service import reviews_service as service
from app.reviews.dependencies import parse_review_form, parse_review_only_form
from app.models.models import User

router = APIRouter()


@router.post("/register", response_model=schemas.RegisterResponse)
async def create_review_and_restaurant(
    parsed_data: schemas.ReviewWithRestaurantCreate = Depends(parse_review_form),
    files: Optional[List[UploadFile]] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    맛집 등록과 리뷰를 같이 작성합니다.

    - restaurants/search API 기반 정보로 맛집 등록과 리뷰를 같이하는 기능입니다.
    - 이미지는 여러 장 업로드 가능합니다 (이미지 필수 X)
    """
    uploaded_urls = []
    # 💡 리뷰 작성 여부 판단 (별점이 있는지 확인)
    is_review_included = parsed_data.rating is not None

    try:
        # ✅ 리뷰가 포함된 경우에만 이미지 필터링 및 업로드 진행
        if is_review_included:
            valid_files = [
                f
                for f in (files or [])
                if isinstance(f, UploadFile)
                and f.filename
                and f.size > 0
                and f.content_type.startswith("image/")
            ]

            for file in valid_files:
                url = await upload_image_to_supabase(file)
                uploaded_urls.append(url)

        # 서비스 호출 (리뷰 유무 상관없이 호출)
        result = await service.create_review_with_restaurant(
            db=db,
            user_id=current_user.id,
            restaurant_create=parsed_data.restaurant,
            rating=parsed_data.rating,
            content=parsed_data.content,
            images=uploaded_urls,
        )
        return result

    except Exception as e:
        if uploaded_urls:
            print(f"🔥 에러 발생으로 인한 이미지 롤백 시작 ({len(uploaded_urls)}개)")
            for url in uploaded_urls:
                await delete_image_from_supabase(url)
        raise e


@router.post("", response_model=schemas.ReviewResponse)
async def create_review(
    review_data: schemas.ReviewCreate = Depends(parse_review_only_form),
    files: Optional[List[UploadFile]] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    기존 식당에 리뷰만 작성합니다.

    - restaurant_id로 기존 식당을 지정합니다
    - 이미지는 여러 장 업로드 가능합니다 (이미지 필수 X)
    """
    uploaded_urls = []
    try:
        # 유효한 이미지 파일만 필터링
        valid_files = [
            f
            for f in (files or [])
            if isinstance(f, UploadFile)
            and f.filename
            and f.size > 0
            and f.content_type.startswith("image/")
        ]

        for file in valid_files:
            url = await upload_image_to_supabase(file)
            uploaded_urls.append(url)

        # 리뷰 생성
        return await service.create_review_only(
            db=db,
            user_id=current_user.id,
            restaurant_id=review_data.restaurant_id,
            rating=review_data.rating,
            content=review_data.content,
            images=uploaded_urls,
        )

    except Exception as e:
        # 에러 발생 시 업로드된 이미지 삭제
        if uploaded_urls:
            print(f"🔥 에러 발생으로 인한 이미지 롤백 시작 ({len(uploaded_urls)}개)")
            for url in uploaded_urls:
                await delete_image_from_supabase(url)
        raise e


@router.get("", response_model=List[schemas.ReviewResponse])
def get_reviews(
    restaurant_id: int,
    skip: int = 0,  # 0이면 1페이지, 10이면 2페이지... (프론트에서 계산)
    limit: int = 10,  # 한 번에 10개씩 가져옴
    db: Session = Depends(get_db),
):
    """
    특정 식당의 리뷰를 페이지네이션하여 가져옵니다.
    """
    return service.get_reviews_by_restaurant(db, restaurant_id, skip=skip, limit=limit)
