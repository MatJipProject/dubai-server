import traceback
import json
from urllib.parse import parse_qs, urlencode
from fastapi import HTTPException, Request
from starlette.background import BackgroundTask
from starlette.responses import Response
from app.logging import logger
from starlette.types import Message
import re

SENSITIVE_KEYS = ["password", "access_token", "email", "username", "refresh_token"]


def partial_mask(value):
    if isinstance(value, str):
        length = len(value)
        if length <= 7:  # 길이가 7 이하일 경우 앞 2자리와 뒤 5자리만 표시
            return value[:2] + "*" * (length - 2)
        return value[:2] + "*" * (length - 7) + value[-5:]
    return value


def sanitize_data(data, content_type):
    if not data:
        return {}

    # (이미지 데이터는 로그에 텍스트로 찍을 수도 없고, 찍으면 터미널만 도배되므로 생략하는 것이 좋습니다)
    if "multipart/form-data" in content_type:
        return "<Multipart/form-data request - File Upload Omitted>"

    # 2. 일반 텍스트 데이터(JSON 등) 디코딩 시도
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            # 혹시 모를 다른 바이너리 데이터 예외 처리
            return "<Unreadable Binary Data>"

    # 3. 이후 로직은 기존과 동일
    if content_type == "application/json":
        try:
            data_json = json.loads(data)
            if isinstance(data_json, dict):
                return json.dumps(sanitize_dict(data_json))
            else:
                return data
        except (json.JSONDecodeError, TypeError):
            return data

    elif content_type == "application/x-www-form-urlencoded":
        data_dict = parse_qs(data)
        sanitized_dict = sanitize_dict(
            {k: v[0] if isinstance(v, list) else v for k, v in data_dict.items()}
        )
        return urlencode(sanitized_dict)

    else:
        return data


def sanitize_dict(data_dict):
    if not isinstance(data_dict, dict):
        return data_dict
    redacted_dict = {}
    for key, value in data_dict.items():
        if key.lower() in SENSITIVE_KEYS:
            redacted_dict[key] = partial_mask(value)
        elif isinstance(value, dict):
            redacted_dict[key] = sanitize_dict(value)
        else:
            redacted_dict[key] = value
    return redacted_dict


def log_info(
    level, url, req_body, content_type, status_code, res_body, res_content_type, headers
):
    sanitized_req_body = sanitize_data(req_body, content_type)
    # authorization = headers.get("Authorization", "<No Authorization Header>")
    user_agent = headers.get("User-Agent", "<No User-Agent Header>")

    if "application/pdf" in res_content_type:
        sanitized_res_body = "<PDF content>"
    elif "text/html" in res_content_type:
        sanitized_res_body = "<HTML content>"
    elif (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in res_content_type
    ):
        sanitized_res_body = "<Excel content>"
    else:
        sanitized_res_body = sanitize_data(res_body, "application/json")

    log_message = (
        f"[{status_code}] request_url: {url}, user_agent: {user_agent}, "
        f"request_body: {sanitized_req_body}, response_body: {sanitized_res_body}"
    )

    if level == "info":
        logger.info(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "error":
        logger.error(log_message)


def log_error(url, req_body, content_type, error, headers):
    sanitized_req_body = sanitize_data(req_body, content_type)
    error_traceback = traceback.format_exc()

    # # Authorization 헤더 추가
    # auth_header = headers.get("Authorization", "N/A")

    logger.error(
        f"Error processing request_url: {url}, request_body: {sanitized_req_body}, "
        f"error: {str(error)}, traceback: {error_traceback}"
    )


async def set_body(request: Request, body: bytes):
    async def receive() -> Message:
        return {"type": "http.request", "body": body}

    request._receive = receive


async def log_requests(request: Request, call_next):
    # --- FIX: Add this conditional block at the top ---
    # If the request is for the firmware file download, skip the detailed body logging.
    if "/firmware/file/" in request.url.path:
        logger.info(f"Skipping body logging for streaming endpoint: {request.url.path}")
        response = await call_next(request)
        return response

    if request.url.path.endswith("/") or request.url.path.endswith("/openapi.json"):
        response = await call_next(request)
        return response

    req_body = await request.body()
    await set_body(request, req_body)
    content_type = request.headers.get("Content-Type", "")
    try:
        response = await call_next(request)
    except HTTPException as e:
        log_error(request.url, req_body, content_type, e, request.headers)
        raise e
    except Exception as e:
        log_error(request.url, req_body, content_type, e, request.headers)
        raise e

    res_body = b""
    async for chunk in response.body_iterator:
        res_body += chunk
    res_content_type = response.headers.get("Content-Type", "")

    if 200 <= response.status_code < 300:
        log_level = "info"
    elif 400 <= response.status_code < 500:
        log_level = "warning"
    elif 500 <= response.status_code < 600:
        log_level = "error"
    else:
        log_level = "info"

    task = BackgroundTask(
        log_info,
        log_level,
        request.url,
        req_body,
        content_type,
        response.status_code,
        res_body,
        res_content_type,
        request.headers,
    )

    return Response(
        content=res_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
        background=task,
    )
