import json
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import Json
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import delete_image_from_supabase, upload_image_to_supabase
from app.reviews.schemas import reviews_schemas as schemas
from app.reviews.service import reviews_service as service
from app.models.models import User

router = APIRouter()


from fastapi import APIRouter, Depends, Form, File, UploadFile
from pydantic import Json
from typing import List
from sqlalchemy.orm import Session

# ... import 생략 ...


@router.post("/register", response_model=schemas.ReviewResponse)
async def create_review_and_restaurant(
    request_data: str = Form(..., description="식당 및 리뷰 정보 JSON 문자열"),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. JSON 파싱
    try:
        parsed_data = schemas.ReviewWithRestaurantCreate.model_validate_json(
            request_data
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"JSON 파싱 에러: {e}")

    # 2. 이미지 업로드 진행
    uploaded_urls = []  # 성공한 URL들을 담아둘 리스트
    try:
        # --- [A] 업로드 ---
        for file in files:
            if file.size > 0 and file.content_type.startswith("image/"):
                url = await upload_image_to_supabase(file)
                uploaded_urls.append(url)

        # --- [B] 서비스 호출 (DB 저장) ---
        # 여기서 에러가 나면 -> except 블록으로 점프!
        return await service.create_review_with_restaurant(
            db=db,
            user_id=current_user.id,
            restaurant_create=parsed_data.restaurant,
            rating=parsed_data.rating,
            content=parsed_data.content,
            images=uploaded_urls,
        )

    except Exception as e:
        # 🚨 [C] 에러 발생 시 롤백 (보상 트랜잭션)
        # 이미 업로드된 파일이 있다면 지워버림
        if uploaded_urls:
            print(f"🔥 에러 발생으로 인한 이미지 롤백 시작 ({len(uploaded_urls)}개)")
            for url in uploaded_urls:
                await delete_image_from_supabase(url)

        # 에러를 다시 던져서 클라이언트에게 500 에러를 알림
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
