import uuid
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client

# 설정 파일에서 키 가져오기 (경로는 프로젝트에 맞게 수정하세요)
from app.config.config import settings

# 1. Supabase 클라이언트 초기화
# (매번 생성하지 않도록 전역 변수나 싱글톤으로 관리하는 게 좋습니다)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


async def upload_image_to_supabase(
    file: UploadFile, bucket_name: str = "reviews", folder_name: str = "uploads"
) -> str:
    """
    이미지를 Supabase Storage에 업로드하고 Public URL을 반환합니다.

    :param file: FastAPI UploadFile 객체
    :param bucket_name: Supabase 버킷 이름 (기본값: reviews)
    :param folder_name: 버킷 내부 폴더 (기본값: uploads)
    :return: 이미지의 Public URL 문자열
    """
    try:
        # 1. 파일 내용 읽기
        file_content = await file.read()

        # 2. 고유한 파일명 생성 (충돌 방지)
        # 예: my_photo.jpg -> uuid-uuid-uuid.jpg
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = f"{folder_name}/{unique_filename}"

        # 3. Supabase 업로드 요청
        # content-type을 명시해야 브라우저에서 바로 이미지로 보입니다.
        res = supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": file.content_type},
        )

        # 4. Public URL 생성
        # 주의: Supabase 대시보드에서 버킷이 'Public'으로 설정되어 있어야 합니다.
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)

        return public_url

    except Exception as e:
        print(f"이미지 업로드 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail="이미지 업로드 중 오류가 발생했습니다."
        )


async def delete_image_from_supabase(image_url: str, bucket_name: str = "reviews"):
    """
    업로드된 이미지 URL을 받아 Supabase에서 삭제합니다. (롤백용)
    """
    try:
        if bucket_name not in image_url:
            return  # 다른 버킷이거나 잘못된 URL이면 무시

        file_path = image_url.split(f"/{bucket_name}/")[-1]

        # 2. Supabase 삭제 요청 (리스트로 경로 전달)
        supabase.storage.from_(bucket_name).remove([file_path])
        print(f"🗑️ 롤백: 이미지 삭제 완료 ({file_path})")

    except Exception as e:
        # 삭제 실패는 로그만 남기고 넘어감 (메인 로직을 방해하면 안 됨)
        print(f"⚠️ 이미지 삭제 실패: {e}")
