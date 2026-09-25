import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import random
import sys
import time

import requests

from image_prep import crop_to_vertical

HF_API_BASE = "https://api.higgsfield.ai"
KLING_IMAGE_TO_VIDEO_ENDPOINT = f"{HF_API_BASE}/kling-video/v3.0/std/image-to-video"
KLING_TEXT_TO_VIDEO_ENDPOINT = f"{HF_API_BASE}/kling-video/v3.0/std/text-to-video"

TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}

# status_url 폴링이 네트워크 오류/5xx/429로 연속 실패할 때 재시도할 최대 횟수.
# 이 횟수를 넘기면 폴링을 포기하지만, 결제는 이미 끝난 생성 작업 자체는 계속 진행 중일 수 있다.
MAX_CONSECUTIVE_POLL_FAILURES = 5


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
    """status_url을 백오프(2초→최대 10초, 지터 포함)로 폴링해 completed 응답을 반환.

    네트워크 오류/5xx/429는 일시적 실패로 보고 같은 백오프로 재시도한다(연속
    MAX_CONSECUTIVE_POLL_FAILURES회 실패하면 포기). 그 외 4xx는 즉시 포기한다.
    """
    deadline = time.monotonic() + timeout_seconds
    delay = 2.0
    consecutive_failures = 0
    last_error = None
    while True:
        transient_error = None
        try:
            r = requests.get(status_url, headers=_auth_headers(), timeout=30)
        except requests.RequestException as e:
            transient_error = str(e)
        else:
            if r.status_code == 429 or r.status_code >= 500:
                transient_error = f"{r.status_code}: {r.text}"
            elif r.status_code >= 400:
                raise HiggsfieldError(
                    f"상태 조회 실패 ({r.status_code}): {r.text} (status_url={status_url})"
                )
            else:
                consecutive_failures = 0
                result = r.json()
                if result["status"] in TERMINAL_STATUSES:
                    if result["status"] != "completed":
                        raise HiggsfieldError(
                            f"생성 실패 (status={result['status']}): "
                            f"{result.get('error', '알 수 없는 오류')} (status_url={status_url})"
                        )
                    return result

        if transient_error is not None:
            consecutive_failures += 1
            last_error = transient_error
            if consecutive_failures >= MAX_CONSECUTIVE_POLL_FAILURES:
                raise HiggsfieldError(
                    f"상태 조회가 {MAX_CONSECUTIVE_POLL_FAILURES}회 연속 실패했습니다. "
                    f"마지막 오류: {last_error}. 생성 작업은 계속 진행 중일 수 있으니 "
                    f"status_url로 직접 확인해보세요: {status_url}"
                )

        if time.monotonic() > deadline:
            raise HiggsfieldError(
                f"생성 대기 타임아웃 ({timeout_seconds}초 초과, status_url={status_url})"
            )
        time.sleep(delay + random.uniform(0, 0.5))
        delay = min(delay * 1.5, 10.0)


def _download_video(video_url: str) -> bytes:
    """결과 mp4를 다운로드한다. 실패해도 video_url은 7일 이상 유효하므로 메시지에 포함해
    사용자가 직접 받을 수 있게 한다."""
    try:
        r = requests.get(video_url, timeout=120)
    except requests.RequestException as e:
        raise HiggsfieldError(
            f"영상 다운로드 실패: {e}. 아래 링크는 7일 이상 유효하니 직접 다운로드할 수 있습니다: "
            f"{video_url}"
        ) from e
    if r.status_code >= 400:
        raise HiggsfieldError(
            f"영상 다운로드 실패 ({r.status_code}): {r.text}. 아래 링크는 7일 이상 유효하니 "
            f"직접 다운로드할 수 있습니다: {video_url}"
        )
    return r.content


def _submit_and_download(endpoint: str, payload: dict) -> bytes:
    """생성 요청 제출 → 완료까지 폴링 → 결과 mp4 다운로드.

    제출 POST는 멱등성 키가 없어 자동 재시도하지 않는다. 요청이 네트워크 오류로
    실패해도 서버에는 접수되어 과금됐을 수 있으므로, 재시도 전에 콘솔에서 확인하도록 안내한다.
    """
    try:
        r = requests.post(endpoint, headers=_auth_headers(), json=payload, timeout=30)
    except requests.RequestException as e:
        raise HiggsfieldError(
            f"영상 생성 요청 중 오류가 발생했습니다: {e}. 요청이 이미 접수되어 과금됐을 수 있으니, "
            f"재시도하기 전에 https://console.higgsfield.ai 에서 먼저 확인하세요."
        ) from e
    if r.status_code >= 400:
        raise HiggsfieldError(f"영상 생성 요청 실패 ({r.status_code}): {r.text}")
    submitted = r.json()
    status_url = submitted["status_url"]
    print(
        f"[Higgsfield] 생성 요청 접수: request_id={submitted.get('request_id')} status_url={status_url}",
        file=sys.stderr,
    )
    result = _poll_until_done(status_url)
    return _download_video(result["video"]["url"])


def generate_video_from_image(image_path: str, prompt: str, duration: int = 10) -> bytes:
    """사진을 9:16으로 크롭해 업로드한 뒤, 프롬프트대로 움직이는 영상(mp4 바이트)을 생성."""
    image_url = upload_image(crop_to_vertical(image_path))
    return _submit_and_download(
        KLING_IMAGE_TO_VIDEO_ENDPOINT,
        {"prompt": prompt, "image_url": image_url, "duration": duration},
    )


def generate_video_from_text(prompt: str, duration: int = 10, aspect_ratio: str = "9:16") -> bytes:
    """텍스트 프롬프트만으로 영상(mp4 바이트)을 생성."""
    return _submit_and_download(
        KLING_TEXT_TO_VIDEO_ENDPOINT,
        {"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio},
    )
