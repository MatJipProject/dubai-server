import os
import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

log = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.environ.get("ENV", "DEV")
    SITE_DOMAIN: str = "baebulook.site"
    KAKAO_SEARCH_URL: str = "https://dapi.kakao.com/v2/local/search/keyword"
    KAKAO_REST_API_KEY: str = os.getenv("KAKAO_REST_API_KEY")
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: str = os.getenv("DB_PORT")
    DBNAME: str = os.getenv("DB_NAME")
    DATABASE_URL: str = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DBNAME}?sslmode=require"
    )
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "reviews")


settings = Settings()
