import json
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import Json
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.storage import upload_image_to_supabase
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
    # 1. JSON 데이터 (스키마 사용)
    request_data: Json[schemas.ReviewWithRestaurantCreate] = Form(...),
    # 2. 파일 데이터 (별도 처리)
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --- [A] 이미지 업로드 처리 ---
    image_urls = []
    for file in files:
        if file.size > 0 and file.content_type.startswith("image/"):
            url = await upload_image_to_supabase(file)
            image_urls.append(url)

    # --- [B] 서비스 호출 ---
    # 스키마(request_data)와 이미지 URL 리스트(image_urls)를 따로 넘깁니다.
    return await service.create_review_with_restaurant(
        db=db,
        user_id=current_user.id,
        restaurant_create=request_data.restaurant,  # 식당 정보 추출
        rating=request_data.rating,  # 별점 추출
        content=request_data.content,  # 내용 추출
        images=image_urls,  # 업로드된 URL 리스트 전달
    )
