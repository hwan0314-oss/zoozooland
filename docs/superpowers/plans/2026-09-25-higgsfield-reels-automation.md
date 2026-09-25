# Higgsfield 릴스 자동 생성 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Higgsfield API로 쥬쥬랜드 릴스 영상을 생성해, 사용자 텔레그램 계정으로 승인 채널에 올려 이미 운영 중인 승인 → 큐 → Make → Instagram Reels 파이프라인에 태우는 로컬 CLI를 만든다.

**Architecture:** `reels/` 폴더에 4개 모듈을 신규로 만든다 — `higgsfield_client.py`(Higgsfield REST), `image_prep.py`(9:16 크롭), `telegram_sender.py`(Telethon 사용자 계정 전송), `generate_reel.py`(CLI). 서버의 `instagram_bot.py`는 수정하지 않는다. 텔레그램 봇은 자기(및 다른 봇)가 보낸 메시지를 받지 못하므로, 영상은 반드시 사용자 계정(Telethon)으로 올려야 서버 봇의 `handle_video`가 동작한다.

**Tech Stack:** Python 3.12, `requests`, `Pillow`, `telethon`(+ `hachoir`로 영상 메타데이터 추출), `python-dotenv`, `pytest` + `unittest.mock`

## Global Constraints

- 서버 코드(`instagram/instagram_bot.py`, Oracle Cloud 배포본)는 수정하지 않는다.
- 신규 코드는 전부 `reels/` 폴더에 둔다(로컬 전용, 서버 미배포).
- Higgsfield 베이스 URL `https://api.higgsfield.ai`, 인증 헤더 `Authorization: Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET}`.
- 모델: Kling 3.0 Standard — image-to-video `POST /kling-video/v3.0/std/image-to-video`(`prompt`, `image_url`, `duration`), text-to-video `POST /kling-video/v3.0/std/text-to-video`(`prompt`, `duration`, `aspect_ratio`).
- 영상 기본값: 9:16 세로, 10초(허용 3~15초). image-to-video는 비율 파라미터가 없으므로 입력 사진을 업로드 전에 9:16으로 가운데 크롭한다.
- 텔레그램 전송은 Telethon 사용자 세션으로만 한다(봇 토큰 사용 금지 — 서버 봇이 감지하지 못함). 로그인은 사용자가 직접 터미널에서 수행한다.
- 시크릿(`reels/.env`)과 Telethon 세션 파일(`*.session`), 생성 결과(`reels/output/`)는 git에 커밋하지 않는다.
- 기존 코드 관례: `load_dotenv(Path(__file__).parent / ".env")` + `os.environ[...]`, 패키지 없는 평범한 스크립트 파일.

---

## Task 1: 프로젝트 골격 + Higgsfield 이미지 업로드

**Files:**
- Create: `reels/requirements.txt`
- Create: `reels/.env.example`
- Create: `reels/.gitignore`
- Create: `reels/higgsfield_client.py`
- Create: `reels/tests/conftest.py`
- Test: `reels/tests/test_higgsfield_client.py`

**Interfaces:**
- Produces: `higgsfield_client.HiggsfieldError(Exception)`, `higgsfield_client._auth_headers() -> dict`, `higgsfield_client.upload_image(image_bytes: bytes, content_type: str = "image/jpeg") -> str`, 상수 `HF_API_BASE`, `KLING_IMAGE_TO_VIDEO_ENDPOINT`, `KLING_TEXT_TO_VIDEO_ENDPOINT`

- [ ] **Step 1: 테스트 인프라 + 실패하는 테스트 작성**

`reels/tests/conftest.py`:
```python
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["HF_API_KEY_ID"] = "test-key-id"
os.environ["HF_API_KEY_SECRET"] = "test-key-secret"
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "test-api-hash"
os.environ["APPROVAL_CHAT_ID"] = "-1001234567890"
```

`reels/tests/test_higgsfield_client.py`:
```python
from unittest.mock import Mock, patch

import pytest

import higgsfield_client


def test_upload_image_returns_public_url():
    upload_url_response = Mock(status_code=200)
    upload_url_response.json.return_value = {
        "public_url": "https://cdn.example.com/input/sample.jpeg",
        "upload_url": "https://storage.example.com/presigned-upload-url",
        "content_type": "image/jpeg",
        "upload_headers": {
            "Content-Type": "image/jpeg",
            "x-amz-tagging": "retention=temporary",
        },
    }
    put_response = Mock(status_code=200)

    with patch("higgsfield_client.requests.post", return_value=upload_url_response) as mock_post, \
         patch("higgsfield_client.requests.put", return_value=put_response) as mock_put:
        result = higgsfield_client.upload_image(b"fake-jpeg-bytes")

    assert result == "https://cdn.example.com/input/sample.jpeg"
    assert mock_post.call_args.args[0] == "https://api.higgsfield.ai/files/generate-upload-url"
    assert mock_post.call_args.kwargs["headers"] == {"Authorization": "Key test-key-id:test-key-secret"}
    assert mock_post.call_args.kwargs["json"] == {"content_type": "image/jpeg"}
    assert mock_put.call_args.args[0] == "https://storage.example.com/presigned-upload-url"
    assert mock_put.call_args.kwargs["data"] == b"fake-jpeg-bytes"
    assert mock_put.call_args.kwargs["headers"] == {
        "Content-Type": "image/jpeg",
        "x-amz-tagging": "retention=temporary",
    }


def test_upload_image_raises_on_upload_url_error():
    error_response = Mock(status_code=401, text='{"detail": "Invalid credentials"}')

    with patch("higgsfield_client.requests.post", return_value=error_response):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="401"):
            higgsfield_client.upload_image(b"fake-jpeg-bytes")
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'higgsfield_client'`

- [ ] **Step 3: 구현**

`reels/requirements.txt`:
```
requests>=2.31.0
python-dotenv>=1.0.0
Pillow>=10.0.0
telethon>=1.36.0
hachoir>=3.3.0
pytest>=7.4.0
```

`reels/.env.example`:
```
HF_API_KEY_ID=
HF_API_KEY_SECRET=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
APPROVAL_CHAT_ID=
```

`reels/.gitignore`:
```
.env
*.session
*.session-journal
output/
```

`reels/higgsfield_client.py`:
```python
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import requests

HF_API_BASE = "https://api.higgsfield.ai"
KLING_IMAGE_TO_VIDEO_ENDPOINT = f"{HF_API_BASE}/kling-video/v3.0/std/image-to-video"
KLING_TEXT_TO_VIDEO_ENDPOINT = f"{HF_API_BASE}/kling-video/v3.0/std/text-to-video"


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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && pip install -r requirements.txt && python -m pytest tests/test_higgsfield_client.py -v`
Expected: PASS — `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/requirements.txt reels/.env.example reels/.gitignore reels/higgsfield_client.py reels/tests/conftest.py reels/tests/test_higgsfield_client.py
git commit -m "feat(reels): add Higgsfield client with image upload"
```

---

## Task 2: Higgsfield 요청 상태 폴링

**Files:**
- Modify: `reels/higgsfield_client.py`
- Test: `reels/tests/test_higgsfield_client.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: `HiggsfieldError`, `_auth_headers()` (Task 1)
- Produces: `higgsfield_client._poll_until_done(status_url: str, timeout_seconds: float = 600.0) -> dict` (completed 응답 dict 반환), `higgsfield_client.TERMINAL_STATUSES`

- [ ] **Step 1: 실패하는 테스트 추가**

`reels/tests/test_higgsfield_client.py` 파일 끝에 추가:
```python
STATUS_URL = "https://api.higgsfield.ai/requests/r1/status"


def test_poll_until_done_returns_completed_result():
    queued = Mock(status_code=200)
    queued.json.return_value = {"status": "queued", "request_id": "r1"}
    completed = Mock(status_code=200)
    completed.json.return_value = {
        "status": "completed",
        "request_id": "r1",
        "video": {"url": "https://cdn.example.com/output.mp4"},
    }

    with patch("higgsfield_client.requests.get", side_effect=[queued, completed]) as mock_get, \
         patch("higgsfield_client.time.sleep") as mock_sleep:
        result = higgsfield_client._poll_until_done(STATUS_URL)

    assert result["video"]["url"] == "https://cdn.example.com/output.mp4"
    assert mock_get.call_count == 2
    assert mock_get.call_args.args[0] == STATUS_URL
    mock_sleep.assert_called_once()


def test_poll_until_done_raises_on_failed_status():
    failed = Mock(status_code=200)
    failed.json.return_value = {"status": "failed", "request_id": "r1", "error": "Generation failed"}

    with patch("higgsfield_client.requests.get", return_value=failed):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="Generation failed"):
            higgsfield_client._poll_until_done(STATUS_URL)


def test_poll_until_done_raises_on_timeout():
    queued = Mock(status_code=200)
    queued.json.return_value = {"status": "queued", "request_id": "r1"}

    with patch("higgsfield_client.requests.get", return_value=queued), \
         patch("higgsfield_client.time.sleep"), \
         patch("higgsfield_client.time.monotonic", side_effect=[0, 1000]):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="타임아웃"):
            higgsfield_client._poll_until_done(STATUS_URL, timeout_seconds=5.0)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: 새 테스트 3개 FAIL (`AttributeError: ... '_poll_until_done'` 또는 `'time'`), 기존 2개 PASS

- [ ] **Step 3: 구현**

`reels/higgsfield_client.py` 맨 위 import 구역에 추가 (`import os` 바로 아래):
```python
import random
import time
```

`KLING_TEXT_TO_VIDEO_ENDPOINT` 정의 바로 아래에 추가:
```python
TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}
```

파일 끝에 추가:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: PASS — `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/higgsfield_client.py reels/tests/test_higgsfield_client.py
git commit -m "feat(reels): poll Higgsfield request status with backoff"
```

---

## Task 3: 사진 9:16 세로 크롭

**Files:**
- Create: `reels/image_prep.py`
- Test: `reels/tests/test_image_prep.py`

**Interfaces:**
- Produces: `image_prep.crop_to_vertical(image_path: str) -> bytes` (JPEG 바이트), 상수 `image_prep.TARGET_RATIO = 9 / 16`

- [ ] **Step 1: 실패하는 테스트 작성**

`reels/tests/test_image_prep.py`:
```python
import io

from PIL import Image, ImageDraw

import image_prep


def _size_of(jpeg_bytes: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(jpeg_bytes)) as img:
        return img.size


def test_exact_vertical_image_is_unchanged(tmp_path):
    path = tmp_path / "vertical.png"
    Image.new("RGB", (1080, 1920), "white").save(path)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (1080, 1920)


def test_wide_image_is_cropped_to_vertical(tmp_path):
    path = tmp_path / "wide.jpg"
    Image.new("RGB", (1600, 900), "white").save(path)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (506, 900)


def test_tall_image_is_cropped_to_vertical(tmp_path):
    path = tmp_path / "tall.jpg"
    Image.new("RGB", (900, 2000), "white").save(path)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (900, 1600)


def test_crop_keeps_the_center(tmp_path):
    path = tmp_path / "wide.png"
    img = Image.new("RGB", (1600, 900), "black")
    ImageDraw.Draw(img).rectangle((547, 0, 1052, 899), fill="white")
    img.save(path)

    with Image.open(io.BytesIO(image_prep.crop_to_vertical(str(path)))) as cropped:
        assert cropped.getpixel((5, 450)) > (240, 240, 240)
        assert cropped.getpixel((500, 450)) > (240, 240, 240)


def test_exif_rotation_is_applied_before_crop(tmp_path):
    path = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # 90도 회전해서 보여줘야 하는 폰 사진 (저장은 1600x900, 표시는 900x1600)
    Image.new("RGB", (1600, 900), "white").save(path, exif=exif)

    assert _size_of(image_prep.crop_to_vertical(str(path))) == (900, 1600)


def test_output_is_jpeg(tmp_path):
    path = tmp_path / "input.png"
    Image.new("RGBA", (1080, 1920), (255, 255, 255, 255)).save(path)

    with Image.open(io.BytesIO(image_prep.crop_to_vertical(str(path)))) as img:
        assert img.format == "JPEG"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_image_prep.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'image_prep'`

- [ ] **Step 3: 구현**

`reels/image_prep.py`:
```python
import io

from PIL import Image, ImageOps

TARGET_RATIO = 9 / 16


def crop_to_vertical(image_path: str) -> bytes:
    """EXIF 회전을 보정한 뒤 가운데를 기준으로 9:16 세로로 잘라 JPEG 바이트로 반환.
    Kling image-to-video는 비율 파라미터가 없고 입력 이미지 비율을 그대로 따른다."""
    with Image.open(image_path) as src:
        img = ImageOps.exif_transpose(src).convert("RGB")

    width, height = img.size
    if width / height > TARGET_RATIO:
        new_width = round(height * TARGET_RATIO)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    else:
        new_height = round(width / TARGET_RATIO)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_image_prep.py -v`
Expected: PASS — `6 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/image_prep.py reels/tests/test_image_prep.py
git commit -m "feat(reels): center-crop input photos to 9:16"
```

---

## Task 4: 영상 생성 함수 (image-to-video / text-to-video)

**Files:**
- Modify: `reels/higgsfield_client.py`
- Test: `reels/tests/test_higgsfield_client.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: `upload_image`, `_poll_until_done`, `_auth_headers`, `HiggsfieldError`, 엔드포인트 상수 (Task 1, 2), `image_prep.crop_to_vertical` (Task 3)
- Produces: `higgsfield_client.generate_video_from_image(image_path: str, prompt: str, duration: int = 10) -> bytes`, `higgsfield_client.generate_video_from_text(prompt: str, duration: int = 10, aspect_ratio: str = "9:16") -> bytes`

- [ ] **Step 1: 실패하는 테스트 추가**

`reels/tests/test_higgsfield_client.py` 파일 끝에 추가:
```python
def _submit_response(request_id: str) -> Mock:
    response = Mock(status_code=200)
    response.json.return_value = {
        "status": "queued",
        "request_id": request_id,
        "status_url": f"https://api.higgsfield.ai/requests/{request_id}/status",
    }
    return response


def _completed_response(video_url: str) -> Mock:
    response = Mock(status_code=200)
    response.json.return_value = {"status": "completed", "video": {"url": video_url}}
    return response


def test_generate_video_from_image_uploads_cropped_photo_and_returns_video():
    upload_url_response = Mock(status_code=200)
    upload_url_response.json.return_value = {
        "public_url": "https://cdn.example.com/input/cropped.jpeg",
        "upload_url": "https://storage.example.com/presigned",
        "upload_headers": {"Content-Type": "image/jpeg"},
    }
    download_response = Mock(status_code=200, content=b"fake-video-bytes")

    with patch("higgsfield_client.crop_to_vertical", return_value=b"cropped-jpeg") as mock_crop, \
         patch(
             "higgsfield_client.requests.post",
             side_effect=[upload_url_response, _submit_response("r1")],
         ) as mock_post, \
         patch("higgsfield_client.requests.put", return_value=Mock(status_code=200)) as mock_put, \
         patch(
             "higgsfield_client.requests.get",
             side_effect=[_completed_response("https://cdn.example.com/output.mp4"), download_response],
         ) as mock_get:
        result = higgsfield_client.generate_video_from_image(
            "alpaca.jpg", "알파카가 건초를 먹는 모습", duration=8
        )

    assert result == b"fake-video-bytes"
    mock_crop.assert_called_once_with("alpaca.jpg")
    assert mock_put.call_args.kwargs["data"] == b"cropped-jpeg"
    submit_call = mock_post.call_args_list[1]
    assert submit_call.args[0] == "https://api.higgsfield.ai/kling-video/v3.0/std/image-to-video"
    assert submit_call.kwargs["json"] == {
        "prompt": "알파카가 건초를 먹는 모습",
        "image_url": "https://cdn.example.com/input/cropped.jpeg",
        "duration": 8,
    }
    assert mock_get.call_args_list[0].args[0] == "https://api.higgsfield.ai/requests/r1/status"
    assert mock_get.call_args_list[1].args[0] == "https://cdn.example.com/output.mp4"


def test_generate_video_from_text_returns_video():
    download_response = Mock(status_code=200, content=b"fake-video-bytes-2")

    with patch("higgsfield_client.requests.post", return_value=_submit_response("r2")) as mock_post, \
         patch(
             "higgsfield_client.requests.get",
             side_effect=[_completed_response("https://cdn.example.com/output2.mp4"), download_response],
         ):
        result = higgsfield_client.generate_video_from_text(
            "알파카 아침 산책", duration=10, aspect_ratio="9:16"
        )

    assert result == b"fake-video-bytes-2"
    assert mock_post.call_args.args[0] == "https://api.higgsfield.ai/kling-video/v3.0/std/text-to-video"
    assert mock_post.call_args.kwargs["json"] == {
        "prompt": "알파카 아침 산책",
        "duration": 10,
        "aspect_ratio": "9:16",
    }


def test_generate_video_raises_when_submission_rejected():
    rejected = Mock(status_code=403, text='{"detail": "Insufficient credits"}')

    with patch("higgsfield_client.requests.post", return_value=rejected):
        with pytest.raises(higgsfield_client.HiggsfieldError, match="403"):
            higgsfield_client.generate_video_from_text("알파카 아침 산책")
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: 새 테스트 3개 FAIL (`AttributeError: ... 'crop_to_vertical'` / `'generate_video_from_text'`), 기존 5개 PASS

- [ ] **Step 3: 구현**

`reels/higgsfield_client.py`의 `import requests` 바로 아래에 추가:
```python
from image_prep import crop_to_vertical
```

파일 끝에 추가:
```python
def _download_video(video_url: str) -> bytes:
    r = requests.get(video_url, timeout=120)
    if r.status_code >= 400:
        raise HiggsfieldError(f"영상 다운로드 실패 ({r.status_code}): {r.text}")
    return r.content


def _submit_and_download(endpoint: str, payload: dict) -> bytes:
    """생성 요청 제출 → 완료까지 폴링 → 결과 mp4 다운로드."""
    r = requests.post(endpoint, headers=_auth_headers(), json=payload, timeout=30)
    if r.status_code >= 400:
        raise HiggsfieldError(f"영상 생성 요청 실패 ({r.status_code}): {r.text}")
    result = _poll_until_done(r.json()["status_url"])
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/ -v`
Expected: PASS — `14 passed` (higgsfield 8 + image_prep 6)

- [ ] **Step 5: 커밋**

```bash
git add reels/higgsfield_client.py reels/tests/test_higgsfield_client.py
git commit -m "feat(reels): generate videos via Kling 3.0 image/text-to-video"
```

---

## Task 5: 사용자 계정으로 승인 채널 전송 (Telethon)

**Files:**
- Create: `reels/telegram_sender.py`
- Test: `reels/tests/test_telegram_sender.py`

**Interfaces:**
- Produces: `telegram_sender.TelegramSendError(Exception)`, `telegram_sender.send_video_for_approval(video_bytes: bytes, filename: str = "reel.mp4") -> int` (게시된 메시지 ID), `telegram_sender.SESSION_PATH`. `python telegram_sender.py` 직접 실행 = 1회 대화형 로그인.

- [ ] **Step 1: 실패하는 테스트 작성**

`reels/tests/test_telegram_sender.py`:
```python
from unittest.mock import AsyncMock, Mock, patch

import pytest

import telegram_sender


def _mock_client(mock_client_cls, authorized=True, entity_side_effect=None):
    client = mock_client_cls.return_value
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.is_user_authorized = AsyncMock(return_value=authorized)
    client.get_input_entity = AsyncMock(side_effect=entity_side_effect or ["channel-entity"])
    client.get_dialogs = AsyncMock()
    client.send_file = AsyncMock(return_value=Mock(id=42))
    return client


def test_send_video_posts_to_approval_channel_as_user():
    with patch("telegram_sender.TelegramClient") as mock_client_cls:
        client = _mock_client(mock_client_cls)
        result = telegram_sender.send_video_for_approval(b"fake-video-bytes", filename="test.mp4")

    assert result == 42
    mock_client_cls.assert_called_once_with(str(telegram_sender.SESSION_PATH), 12345, "test-api-hash")
    client.get_input_entity.assert_awaited_once_with(-1001234567890)
    entity, video = client.send_file.call_args.args
    assert entity == "channel-entity"
    assert video.getvalue() == b"fake-video-bytes"
    assert video.name == "test.mp4"
    assert client.send_file.call_args.kwargs == {"supports_streaming": True}
    client.disconnect.assert_awaited_once()


def test_send_video_requires_login():
    with patch("telegram_sender.TelegramClient") as mock_client_cls:
        client = _mock_client(mock_client_cls, authorized=False)
        with pytest.raises(telegram_sender.TelegramSendError, match="로그인"):
            telegram_sender.send_video_for_approval(b"fake-video-bytes")

    client.send_file.assert_not_awaited()
    client.disconnect.assert_awaited_once()


def test_send_video_loads_dialogs_when_channel_not_cached():
    with patch("telegram_sender.TelegramClient") as mock_client_cls:
        client = _mock_client(
            mock_client_cls,
            entity_side_effect=[ValueError("Could not find the input entity"), "channel-entity"],
        )
        telegram_sender.send_video_for_approval(b"fake-video-bytes")

    client.get_dialogs.assert_awaited_once()
    assert client.send_file.call_args.args[0] == "channel-entity"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_telegram_sender.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'telegram_sender'`

- [ ] **Step 3: 구현**

`reels/telegram_sender.py`:
```python
import asyncio
import io
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from telethon import TelegramClient

TELEGRAM_API_ID = int(os.environ["TELEGRAM_API_ID"])
TELEGRAM_API_HASH = os.environ["TELEGRAM_API_HASH"]
APPROVAL_CHAT_ID = int(os.environ["APPROVAL_CHAT_ID"])
SESSION_PATH = Path(__file__).parent / "zzl_reels"  # Telethon이 .session 확장자를 붙임


class TelegramSendError(Exception):
    pass


def _new_client() -> TelegramClient:
    return TelegramClient(str(SESSION_PATH), TELEGRAM_API_ID, TELEGRAM_API_HASH)


async def _send(video_bytes: bytes, filename: str) -> int:
    client = _new_client()
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise TelegramSendError(
                "텔레그램 로그인이 필요합니다. 터미널에서 먼저 `python telegram_sender.py`를 실행하세요."
            )
        try:
            entity = await client.get_input_entity(APPROVAL_CHAT_ID)
        except ValueError:
            # 새 세션은 채널의 access hash를 모르므로 대화 목록을 한 번 불러와 캐시를 채운다
            await client.get_dialogs()
            entity = await client.get_input_entity(APPROVAL_CHAT_ID)
        video = io.BytesIO(video_bytes)
        video.name = filename
        message = await client.send_file(entity, video, supports_streaming=True)
        return message.id
    finally:
        await client.disconnect()


def send_video_for_approval(video_bytes: bytes, filename: str = "reel.mp4") -> int:
    """사용자 계정으로 승인 채널에 영상을 올린다. 봇 토큰으로 보내면 서버 봇이 자기 메시지를
    받지 못해 handle_video가 동작하지 않으므로 반드시 사용자 세션을 쓴다."""
    return asyncio.run(_send(video_bytes, filename))


async def _login() -> None:
    client = _new_client()
    await client.start()
    me = await client.get_me()
    print(f"로그인 완료: {me.first_name} (세션 파일: {SESSION_PATH}.session)")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(_login())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_telegram_sender.py -v`
Expected: PASS — `3 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/telegram_sender.py reels/tests/test_telegram_sender.py
git commit -m "feat(reels): post generated video to approval channel via user session"
```

---

## Task 6: CLI 진입점 (`generate_reel.py`)

**Files:**
- Create: `reels/generate_reel.py`
- Test: `reels/tests/test_generate_reel.py`

**Interfaces:**
- Consumes: `higgsfield_client.generate_video_from_image`, `generate_video_from_text`, `HiggsfieldError` (Task 4), `telegram_sender.send_video_for_approval`, `TelegramSendError` (Task 5)
- Produces: `generate_reel.main(argv: list[str] | None = None) -> int`, `generate_reel.OUTPUT_DIR`, 서브커맨드 `photo`, `text`

- [ ] **Step 1: 실패하는 테스트 작성**

`reels/tests/test_generate_reel.py`:
```python
from unittest.mock import patch

import generate_reel


def test_photo_command_saves_video_and_sends_it(tmp_path, capsys):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch(
             "generate_reel.generate_video_from_image", return_value=b"fake-video-bytes"
         ) as mock_generate, \
         patch("generate_reel.send_video_for_approval", return_value=99) as mock_send:
        exit_code = generate_reel.main(["photo", "alpaca.jpg", "알파카 아침 산책", "--duration", "8"])

    assert exit_code == 0
    mock_generate.assert_called_once_with("alpaca.jpg", "알파카 아침 산책", duration=8)
    saved = list(tmp_path.glob("reel_*.mp4"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == b"fake-video-bytes"
    mock_send.assert_called_once_with(b"fake-video-bytes", filename=saved[0].name)
    assert "message_id=99" in capsys.readouterr().out


def test_text_command_passes_duration_and_aspect_ratio(tmp_path):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch(
             "generate_reel.generate_video_from_text", return_value=b"fake-video-bytes"
         ) as mock_generate, \
         patch("generate_reel.send_video_for_approval", return_value=100):
        exit_code = generate_reel.main(
            ["text", "알파카 아침 산책", "--duration", "9", "--aspect-ratio", "9:16"]
        )

    assert exit_code == 0
    mock_generate.assert_called_once_with("알파카 아침 산책", duration=9, aspect_ratio="9:16")


def test_generation_failure_skips_saving_and_sending(tmp_path, capsys):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch(
             "generate_reel.generate_video_from_image",
             side_effect=generate_reel.HiggsfieldError("Insufficient credits"),
         ), \
         patch("generate_reel.send_video_for_approval") as mock_send:
        exit_code = generate_reel.main(["photo", "alpaca.jpg", "알파카 아침 산책"])

    assert exit_code == 1
    mock_send.assert_not_called()
    assert list(tmp_path.iterdir()) == []
    assert "Insufficient credits" in capsys.readouterr().err


def test_telegram_failure_keeps_saved_video_and_reports_path(tmp_path, capsys):
    with patch("generate_reel.OUTPUT_DIR", tmp_path), \
         patch("generate_reel.generate_video_from_text", return_value=b"fake-video-bytes"), \
         patch(
             "generate_reel.send_video_for_approval",
             side_effect=generate_reel.TelegramSendError("텔레그램 로그인이 필요합니다."),
         ):
        exit_code = generate_reel.main(["text", "알파카 아침 산책"])

    assert exit_code == 1
    saved = list(tmp_path.glob("reel_*.mp4"))
    assert len(saved) == 1
    assert str(saved[0]) in capsys.readouterr().err
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_generate_reel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generate_reel'`

- [ ] **Step 3: 구현**

`reels/generate_reel.py`:
```python
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from higgsfield_client import HiggsfieldError, generate_video_from_image, generate_video_from_text
from telegram_sender import TelegramSendError, send_video_for_approval

OUTPUT_DIR = Path(__file__).parent / "output"


def _generate_and_send(generate: Callable[[], bytes]) -> int:
    try:
        video_bytes = generate()
    except HiggsfieldError as e:
        print(f"[Higgsfield 생성 실패] {e}", file=sys.stderr)
        return 1

    # 전송이 실패해도 비용을 들여 만든 영상을 잃지 않도록 먼저 저장
    OUTPUT_DIR.mkdir(exist_ok=True)
    video_path = OUTPUT_DIR / f"reel_{datetime.now():%Y%m%d_%H%M%S}.mp4"
    video_path.write_bytes(video_bytes)
    print(f"영상 저장: {video_path}")

    try:
        message_id = send_video_for_approval(video_bytes, filename=video_path.name)
    except TelegramSendError as e:
        print(f"[텔레그램 전송 실패] {e}\n저장된 영상을 직접 승인 채널에 올려도 됩니다: {video_path}", file=sys.stderr)
        return 1

    print(f"승인 채널에 전송 완료 (message_id={message_id}). 텔레그램에서 승인/수정/거절 해주세요.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Higgsfield로 쥬쥬랜드 릴스 영상을 생성해 텔레그램 승인 채널에 올린다"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    photo_p = sub.add_parser("photo", help="사진 1장을 9:16 영상으로 애니메이션화")
    photo_p.add_argument("image_path")
    photo_p.add_argument("prompt")
    photo_p.add_argument("--duration", type=int, default=10, choices=range(3, 16), metavar="3-15")

    text_p = sub.add_parser("text", help="텍스트 프롬프트만으로 영상 생성")
    text_p.add_argument("prompt")
    text_p.add_argument("--duration", type=int, default=10, choices=range(3, 16), metavar="3-15")
    text_p.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "16:9", "1:1"])

    args = parser.parse_args(argv)

    if args.command == "photo":
        return _generate_and_send(
            lambda: generate_video_from_image(args.image_path, args.prompt, duration=args.duration)
        )
    return _generate_and_send(
        lambda: generate_video_from_text(args.prompt, duration=args.duration, aspect_ratio=args.aspect_ratio)
    )


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 전체 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/ -v`
Expected: PASS — `21 passed` (higgsfield 8 + image_prep 6 + telegram_sender 3 + generate_reel 4)

- [ ] **Step 5: 커밋**

```bash
git add reels/generate_reel.py reels/tests/test_generate_reel.py
git commit -m "feat(reels): add CLI to generate a reel and send it for approval"
```

---

## Task 7: 수동 End-to-End 확인 (사람이 직접 수행)

실제 계정과 운영 중인 봇으로 전체 경로를 확인한다. 여기서부터 실제 비용(Higgsfield 잔액)이 발생하고, 로그인/키 발급은 반드시 사용자가 직접 한다.

**Files:** 없음

- [ ] **Step 1: Higgsfield 키 발급** — [console.higgsfield.ai](https://console.higgsfield.ai)에서 API 키 생성, 잔액 충전(최소 $5)
- [ ] **Step 2: 텔레그램 API 키 발급** — [my.telegram.org](https://my.telegram.org) → API development tools → `api_id`, `api_hash` 발급
- [ ] **Step 3: 서버의 승인 채널 ID 확인**

Run: `ssh -i ~/.ssh/zzl_oracle.key ubuntu@152.69.239.249 "grep APPROVAL_CHAT_ID /home/ubuntu/zoozooland/instagram/.env"`
Expected: `APPROVAL_CHAT_ID=-100...` — 이 값을 그대로 사용 (로컬 `.env.new`의 값과 다를 수 있음)

- [ ] **Step 4: `reels/.env` 작성** — `.env.example`을 복사해 위 값들 채우기
- [ ] **Step 5: 텔레그램 로그인 (1회)** — 본인 터미널에서 `cd reels && python telegram_sender.py` 실행 → 전화번호, 인증코드 입력 → `로그인 완료` 출력 확인
- [ ] **Step 6: 실제 사진으로 생성**

Run: `cd reels && python generate_reel.py photo <동물 사진 경로> "따뜻한 아침 햇살 아래 알파카가 건초를 먹는 모습, 시네마틱"`
Expected: `영상 저장: ...` → `승인 채널에 전송 완료 (message_id=...)`

- [ ] **Step 7: 텔레그램 확인** — 승인 채널에 올라간 영상 아래로 서버 봇이 보낸 영상 미리보기 + 캡션 카드 + 승인/수정/거절 버튼이 도착하는지 확인. 실게시를 원치 않으면 승인하지 않고 거절.
