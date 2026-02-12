# 가벼운 파이썬 버전 사용
FROM python:3.11-slim

# 출력 버퍼링 끄기 (로그 바로 보려고)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사
COPY . .

# 실행 명령 (8000번 포트)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]