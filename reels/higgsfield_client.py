import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import random
import time

import requests

HF_API_BASE = "https://api.higgsfield.ai"
KLING_IMAGE_TO_VIDEO_ENDPOINT = f"{HF_API_BASE}/kling-video/v3.0/std/image-to-video"
KLING_TEXT_TO_VIDEO_ENDPOINT = f"{HF_API_BASE}/kling-video/v3.0/std/text-to-video"

TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}


class HiggsfieldError(Exception):
    pass


def _auth_headers() -> dict:
    key_id = os.environ["HF_API_KEY_ID"]
    key_secret = os.environ["HF_API_KEY_SECRET"]
    return {"Authorization": f"Key {key_id}:{key_secret}"}


def upload_image(image_bytes: bytes, content_type: str = "image/jpeg") -> str:
    """이미지를 Higgsfield 스토리지에 업로드하고 모델 입력용 공개 URL을 반환."""
    r = requests.post(
        f"{HF_API_BASE}/files/generate-upload-url",
        headers=_auth_headers(),
        json={"content_type": content_type},
        timeout=30,
    )
    if r.status_code >= 400:
        raise HiggsfieldError(f"업로드 URL 발급 실패 ({r.status_code}): {r.text}")
    upload_info = r.json()

    put_r = requests.put(
        upload_info["upload_url"],
        headers=upload_info["upload_headers"],
        data=image_bytes,
        timeout=60,
    )
    if put_r.status_code >= 400:
        raise HiggsfieldError(f"이미지 업로드 실패 ({put_r.status_code}): {put_r.text}")

    return upload_info["public_url"]


def _poll_until_done(status_url: str, timeout_seconds: float = 600.0) -> dict:
    """status_url을 백오프(2초→최대 10초, 지터 포함)로 폴링해 completed 응답을 반환."""
    deadline = time.monotonic() + timeout_seconds
    delay = 2.0
    while True:
        r = requests.get(status_url, headers=_auth_headers(), timeout=30)
        if r.status_code >= 400:
            raise HiggsfieldError(f"상태 조회 실패 ({r.status_code}): {r.text}")
        result = r.json()
        if result["status"] in TERMINAL_STATUSES:
            if result["status"] != "completed":
                raise HiggsfieldError(
                    f"생성 실패 (status={result['status']}): {result.get('error', '알 수 없는 오류')}"
                )
            return result
        if time.monotonic() > deadline:
            raise HiggsfieldError(f"생성 대기 타임아웃 ({timeout_seconds}초 초과)")
        time.sleep(delay + random.uniform(0, 0.5))
        delay = min(delay * 1.5, 10.0)
