# Higgsfield 릴스 자동 생성 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Higgsfield API로 쥬쥬랜드 릴스 영상을 생성해, 이미 운영 중인 텔레그램 승인 → 큐 → Make → Instagram Reels 파이프라인에 그대로 흘려보내는 로컬 CLI를 만든다.

**Architecture:** `reels/` 폴더에 3개의 독립적인 모듈(`higgsfield_client.py`, `telegram_sender.py`, `generate_reel.py`)을 신규로 추가한다. 서버에 배포된 `instagram/instagram_bot.py`는 전혀 수정하지 않는다 — Higgsfield로 만든 영상을 텔레그램 Bot API로 승인 채널에 직접 전송하면, 이미 동작 중인 `handle_video` 핸들러가 그 이후 전 과정(캡션 생성/승인/큐/Make 게시)을 그대로 처리한다.

**Tech Stack:** Python 3.12, `requests` (Higgsfield REST 호출), `python-telegram-bot`(Bot API), `python-dotenv`, `pytest` + `unittest.mock`(테스트)

## Global Constraints

- 서버 코드(`instagram/instagram_bot.py`, Oracle Cloud 배포본)는 이번 작업에서 절대 수정하지 않는다.
- 신규 코드는 전부 `reels/` 폴더(로컬 전용, 서버 미배포)에 둔다.
- Higgsfield 인증 헤더: `Authorization: Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET}`, 베이스 URL `https://api.higgsfield.ai`.
- 생성 영상 기본값: 9:16 세로, 8~15초 권장(기본 10초). 텍스트/로고 오버레이 없음 — 브랜드 메시지는 텔레그램 승인 이후 단계(기존 파이프라인의 Claude Vision 캡션)에서만 전달.
- 모델은 Kling 3.0 Standard(`kling-video/v3.0/std/*`)를 기본값으로 사용한다(공식 문서에서 요청/응답 스키마를 직접 확인함).
- 기존 코드베이스 관례를 따른다: `python-dotenv`의 `load_dotenv(Path(__file__).parent / ".env")` + `os.environ[...]`로 필수 환경변수를 읽는다(`instagram/instagram_bot.py`와 동일 패턴). 패키지 구조 없이 평범한 스크립트 파일로 구성(기존 `instagram/` 폴더와 동일 스타일).

---

## Task 1: Higgsfield 클라이언트 — 인증 + 이미지 업로드

**Files:**
- Create: `reels/requirements.txt`
- Create: `reels/.env.example`
- Create: `reels/higgsfield_client.py`
- Create: `reels/tests/conftest.py`
- Test: `reels/tests/test_higgsfield_client.py`

**Interfaces:**
- Produces: `higgsfield_client.HiggsfieldError(Exception)`, `higgsfield_client.upload_image(image_path: str) -> str`

- [ ] **Step 1: 테스트 인프라 + 실패하는 테스트 작성**

`reels/tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

`reels/tests/test_higgsfield_client.py`:
```python
import os
from unittest.mock import patch, Mock

os.environ.setdefault("HF_API_KEY_ID", "test-key-id")
os.environ.setdefault("HF_API_KEY_SECRET", "test-key-secret")

import higgsfield_client


def test_upload_image_returns_public_url(tmp_path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")

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
        result = higgsfield_client.upload_image(str(image_path))

    assert result == "https://cdn.example.com/input/sample.jpeg"
    assert mock_post.call_args.kwargs["json"] == {"content_type": "image/jpeg"}
    assert mock_put.call_args.kwargs["data"] == b"fake-jpeg-bytes"
    assert mock_put.call_args.kwargs["headers"] == {
        "Content-Type": "image/jpeg",
        "x-amz-tagging": "retention=temporary",
    }


def test_upload_image_raises_on_upload_url_error(tmp_path):
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"fake-png-bytes")

    error_response = Mock(status_code=401, text='{"detail": "Invalid credentials"}')

    with patch("higgsfield_client.requests.post", return_value=error_response):
        try:
            higgsfield_client.upload_image(str(image_path))
            assert False, "HiggsfieldError가 발생해야 함"
        except higgsfield_client.HiggsfieldError as e:
            assert "401" in str(e)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'higgsfield_client'`

- [ ] **Step 3: 최소 구현 작성**

`reels/requirements.txt`:
```
requests>=2.31.0
python-telegram-bot>=21.0
python-dotenv>=1.0.0
pytest>=7.4.0
```

`reels/.env.example`:
```
HF_API_KEY_ID=
HF_API_KEY_SECRET=
TELEGRAM_BOT_TOKEN=
APPROVAL_CHAT_ID=
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

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class HiggsfieldError(Exception):
    pass


def _auth_headers() -> dict:
    key_id = os.environ["HF_API_KEY_ID"]
    key_secret = os.environ["HF_API_KEY_SECRET"]
    return {"Authorization": f"Key {key_id}:{key_secret}"}


def upload_image(image_path: str) -> str:
    """로컬 이미지를 Higgsfield 스토리지에 업로드하고 공개 URL을 반환."""
    path = Path(image_path)
    content_type = _CONTENT_TYPES[path.suffix.lower()]

    r = requests.post(
        f"{HF_API_BASE}/files/generate-upload-url",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"content_type": content_type},
        timeout=30,
    )
    if r.status_code >= 400:
        raise HiggsfieldError(f"업로드 URL 발급 실패 ({r.status_code}): {r.text}")
    upload_info = r.json()

    put_r = requests.put(
        upload_info["upload_url"],
        headers=upload_info["upload_headers"],
        data=path.read_bytes(),
        timeout=60,
    )
    if put_r.status_code >= 400:
        raise HiggsfieldError(f"이미지 업로드 실패 ({put_r.status_code}): {put_r.text}")

    return upload_info["public_url"]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: PASS — `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/requirements.txt reels/.env.example reels/higgsfield_client.py reels/tests/
git commit -m "feat(reels): add Higgsfield client with image upload"
```

---

## Task 2: Higgsfield 클라이언트 — 상태 폴링

**Files:**
- Modify: `reels/higgsfield_client.py` (파일 끝에 추가)
- Test: `reels/tests/test_higgsfield_client.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: `higgsfield_client.HiggsfieldError`, `higgsfield_client._auth_headers()` (Task 1)
- Produces: `higgsfield_client._poll_until_done(status_url: str, timeout_seconds: float = 600.0) -> dict`, `higgsfield_client.TERMINAL_STATUSES: set[str]`

- [ ] **Step 1: 실패하는 테스트 추가**

`reels/tests/test_higgsfield_client.py` 파일 끝에 추가:
```python
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
        result = higgsfield_client._poll_until_done("https://api.higgsfield.ai/requests/r1/status")

    assert result["video"]["url"] == "https://cdn.example.com/output.mp4"
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once()


def test_poll_until_done_raises_on_failed_status():
    failed = Mock(status_code=200)
    failed.json.return_value = {"status": "failed", "request_id": "r1", "error": "Generation failed"}

    with patch("higgsfield_client.requests.get", return_value=failed):
        try:
            higgsfield_client._poll_until_done("https://api.higgsfield.ai/requests/r1/status")
            assert False, "HiggsfieldError가 발생해야 함"
        except higgsfield_client.HiggsfieldError as e:
            assert "Generation failed" in str(e)


def test_poll_until_done_raises_on_timeout():
    queued = Mock(status_code=200)
    queued.json.return_value = {"status": "queued", "request_id": "r1"}

    with patch("higgsfield_client.requests.get", return_value=queued), \
         patch("higgsfield_client.time.sleep"), \
         patch("higgsfield_client.time.monotonic", side_effect=[0, 1000]):
        try:
            higgsfield_client._poll_until_done(
                "https://api.higgsfield.ai/requests/r1/status", timeout_seconds=5.0
            )
            assert False, "HiggsfieldError가 발생해야 함"
        except higgsfield_client.HiggsfieldError as e:
            assert "타임아웃" in str(e)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: FAIL — `AttributeError: module 'higgsfield_client' has no attribute '_poll_until_done'` (새로 추가한 3개 테스트만 실패, 기존 2개는 PASS 유지)

- [ ] **Step 3: 최소 구현 작성**

`reels/higgsfield_client.py` 파일 끝에 추가 (파일 상단 import 구역에 `import time`, `import random`도 추가):
```python
import time
import random

TERMINAL_STATUSES = {"completed", "failed", "nsfw", "canceled"}


def _poll_until_done(status_url: str, timeout_seconds: float = 600.0) -> dict:
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

(참고: `import time`, `import random`은 파일 최상단 `import requests` 근처로 옮겨도 무방하지만, 최소 변경을 위해 이 블록 위치에 함께 추가해도 동작에는 문제 없음)

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: PASS — `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/higgsfield_client.py reels/tests/test_higgsfield_client.py
git commit -m "feat(reels): add Higgsfield request status polling"
```

---

## Task 3: Higgsfield 클라이언트 — 영상 생성 함수

**Files:**
- Modify: `reels/higgsfield_client.py` (파일 끝에 추가)
- Test: `reels/tests/test_higgsfield_client.py` (파일 끝에 추가)

**Interfaces:**
- Consumes: `upload_image`, `_poll_until_done`, `_auth_headers`, `HiggsfieldError`, `KLING_IMAGE_TO_VIDEO_ENDPOINT`, `KLING_TEXT_TO_VIDEO_ENDPOINT` (Task 1, 2)
- Produces: `higgsfield_client.generate_video_from_image(image_path: str, prompt: str, duration: int = 10) -> bytes`, `higgsfield_client.generate_video_from_text(prompt: str, duration: int = 10, aspect_ratio: str = "9:16") -> bytes`

- [ ] **Step 1: 실패하는 테스트 추가**

`reels/tests/test_higgsfield_client.py` 파일 끝에 추가:
```python
def test_generate_video_from_image_returns_bytes(tmp_path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")

    upload_response = Mock(status_code=200)
    upload_response.json.return_value = {
        "public_url": "https://cdn.example.com/input/sample.jpeg",
        "upload_url": "https://storage.example.com/presigned",
        "upload_headers": {"Content-Type": "image/jpeg"},
    }
    put_response = Mock(status_code=200)
    submit_response = Mock(status_code=200)
    submit_response.json.return_value = {
        "status": "queued",
        "request_id": "r1",
        "status_url": "https://api.higgsfield.ai/requests/r1/status",
    }
    poll_response = Mock(status_code=200)
    poll_response.json.return_value = {
        "status": "completed",
        "request_id": "r1",
        "video": {"url": "https://cdn.example.com/output.mp4"},
    }
    download_response = Mock(status_code=200, content=b"fake-video-bytes")

    with patch(
        "higgsfield_client.requests.post", side_effect=[upload_response, submit_response]
    ) as mock_post, \
         patch("higgsfield_client.requests.put", return_value=put_response), \
         patch("higgsfield_client.requests.get", side_effect=[poll_response, download_response]), \
         patch("higgsfield_client.time.sleep"):
        result = higgsfield_client.generate_video_from_image(
            str(image_path), "알파카가 건초를 먹는 모습", duration=8
        )

    assert result == b"fake-video-bytes"
    submit_call = mock_post.call_args_list[1]
    assert submit_call.args[0] == higgsfield_client.KLING_IMAGE_TO_VIDEO_ENDPOINT
    assert submit_call.kwargs["json"] == {
        "prompt": "알파카가 건초를 먹는 모습",
        "image_url": "https://cdn.example.com/input/sample.jpeg",
        "duration": 8,
    }


def test_generate_video_from_text_returns_bytes():
    submit_response = Mock(status_code=200)
    submit_response.json.return_value = {
        "status": "queued",
        "request_id": "r2",
        "status_url": "https://api.higgsfield.ai/requests/r2/status",
    }
    poll_response = Mock(status_code=200)
    poll_response.json.return_value = {
        "status": "completed",
        "request_id": "r2",
        "video": {"url": "https://cdn.example.com/output2.mp4"},
    }
    download_response = Mock(status_code=200, content=b"fake-video-bytes-2")

    with patch("higgsfield_client.requests.post", return_value=submit_response) as mock_post, \
         patch("higgsfield_client.requests.get", side_effect=[poll_response, download_response]), \
         patch("higgsfield_client.time.sleep"):
        result = higgsfield_client.generate_video_from_text(
            "알파카 아침 산책", duration=10, aspect_ratio="9:16"
        )

    assert result == b"fake-video-bytes-2"
    assert mock_post.call_args.args[0] == higgsfield_client.KLING_TEXT_TO_VIDEO_ENDPOINT
    assert mock_post.call_args.kwargs["json"] == {
        "prompt": "알파카 아침 산책",
        "duration": 10,
        "aspect_ratio": "9:16",
    }
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: FAIL — `AttributeError: module 'higgsfield_client' has no attribute 'generate_video_from_image'` (새 테스트 2개만 실패, 기존 5개는 PASS 유지)

- [ ] **Step 3: 최소 구현 작성**

`reels/higgsfield_client.py` 파일 끝에 추가:
```python
def _download_video(video_url: str) -> bytes:
    r = requests.get(video_url, timeout=120)
    if r.status_code >= 400:
        raise HiggsfieldError(f"영상 다운로드 실패 ({r.status_code}): {r.text}")
    return r.content


def generate_video_from_image(image_path: str, prompt: str, duration: int = 10) -> bytes:
    """사진 1장을 프롬프트에 따라 영상으로 애니메이션화하고 mp4 바이트를 반환."""
    image_url = upload_image(image_path)
    r = requests.post(
        KLING_IMAGE_TO_VIDEO_ENDPOINT,
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"prompt": prompt, "image_url": image_url, "duration": duration},
        timeout=30,
    )
    if r.status_code >= 400:
        raise HiggsfieldError(f"영상 생성 요청 실패 ({r.status_code}): {r.text}")
    submission = r.json()
    result = _poll_until_done(submission["status_url"])
    return _download_video(result["video"]["url"])


def generate_video_from_text(prompt: str, duration: int = 10, aspect_ratio: str = "9:16") -> bytes:
    """텍스트 프롬프트만으로 영상을 생성하고 mp4 바이트를 반환."""
    r = requests.post(
        KLING_TEXT_TO_VIDEO_ENDPOINT,
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"prompt": prompt, "duration": duration, "aspect_ratio": aspect_ratio},
        timeout=30,
    )
    if r.status_code >= 400:
        raise HiggsfieldError(f"영상 생성 요청 실패 ({r.status_code}): {r.text}")
    submission = r.json()
    result = _poll_until_done(submission["status_url"])
    return _download_video(result["video"]["url"])
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_higgsfield_client.py -v`
Expected: PASS — `7 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/higgsfield_client.py reels/tests/test_higgsfield_client.py
git commit -m "feat(reels): add image-to-video and text-to-video generation"
```

---

## Task 4: 텔레그램 승인 채널 전송

**Files:**
- Create: `reels/telegram_sender.py`
- Test: `reels/tests/test_telegram_sender.py`

**Interfaces:**
- Produces: `telegram_sender.send_video_for_approval(video_bytes: bytes, filename: str = "reel.mp4") -> int`

- [ ] **Step 1: 실패하는 테스트 작성**

`reels/tests/test_telegram_sender.py`:
```python
import os
from unittest.mock import patch, AsyncMock, Mock

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")
os.environ.setdefault("APPROVAL_CHAT_ID", "-1001234567890")

import telegram_sender


def test_send_video_for_approval_returns_message_id():
    fake_message = Mock(message_id=42)

    with patch("telegram_sender.Bot") as mock_bot_cls:
        mock_bot = mock_bot_cls.return_value
        mock_bot.send_video = AsyncMock(return_value=fake_message)

        result = telegram_sender.send_video_for_approval(b"fake-video-bytes", filename="test.mp4")

    assert result == 42
    mock_bot_cls.assert_called_once_with(token="test-bot-token")
    mock_bot.send_video.assert_awaited_once_with(
        chat_id=-1001234567890, video=b"fake-video-bytes", filename="test.mp4"
    )
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_telegram_sender.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'telegram_sender'`

- [ ] **Step 3: 최소 구현 작성**

`reels/telegram_sender.py`:
```python
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from telegram import Bot

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
APPROVAL_CHAT_ID = int(os.environ["APPROVAL_CHAT_ID"])


def send_video_for_approval(video_bytes: bytes, filename: str = "reel.mp4") -> int:
    """생성된 영상을 텔레그램 승인 채널로 전송하고 메시지 ID를 반환.
    승인 이후 처리는 서버의 기존 handle_video 파이프라인이 담당한다."""

    async def _send() -> int:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        message = await bot.send_video(chat_id=APPROVAL_CHAT_ID, video=video_bytes, filename=filename)
        return message.message_id

    return asyncio.run(_send())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_telegram_sender.py -v`
Expected: PASS — `1 passed`

- [ ] **Step 5: 커밋**

```bash
git add reels/telegram_sender.py reels/tests/test_telegram_sender.py
git commit -m "feat(reels): send generated video to Telegram approval channel"
```

---

## Task 5: CLI 진입점 (`generate_reel.py`)

**Files:**
- Create: `reels/generate_reel.py`
- Test: `reels/tests/test_generate_reel.py`

**Interfaces:**
- Consumes: `higgsfield_client.generate_video_from_image`, `higgsfield_client.generate_video_from_text`, `higgsfield_client.HiggsfieldError` (Task 1-3), `telegram_sender.send_video_for_approval` (Task 4)
- Produces: `generate_reel.main(argv: list[str] | None = None) -> int`, CLI 서브커맨드 `photo`, `text`

- [ ] **Step 1: 실패하는 테스트 작성**

`reels/tests/test_generate_reel.py`:
```python
import os
from unittest.mock import patch

os.environ.setdefault("HF_API_KEY_ID", "test-key-id")
os.environ.setdefault("HF_API_KEY_SECRET", "test-key-secret")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-bot-token")
os.environ.setdefault("APPROVAL_CHAT_ID", "-1001234567890")

import generate_reel


def test_photo_command_sends_generated_video_for_approval(tmp_path, capsys):
    image_path = tmp_path / "alpaca.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")

    with patch(
        "generate_reel.generate_video_from_image", return_value=b"fake-video-bytes"
    ) as mock_generate, \
         patch("generate_reel.send_video_for_approval", return_value=99) as mock_send:
        exit_code = generate_reel.main(["photo", str(image_path), "알파카 아침 산책", "--duration", "8"])

    assert exit_code == 0
    mock_generate.assert_called_once_with(str(image_path), "알파카 아침 산책", duration=8)
    mock_send.assert_called_once_with(b"fake-video-bytes")
    assert "99" in capsys.readouterr().out


def test_photo_command_reports_error_and_skips_telegram_on_generation_failure(tmp_path):
    image_path = tmp_path / "alpaca.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")

    with patch(
        "generate_reel.generate_video_from_image",
        side_effect=generate_reel.HiggsfieldError("생성 실패"),
    ), \
         patch("generate_reel.send_video_for_approval") as mock_send:
        exit_code = generate_reel.main(["photo", str(image_path), "알파카 아침 산책"])

    assert exit_code == 1
    mock_send.assert_not_called()


def test_text_command_sends_generated_video_for_approval():
    with patch(
        "generate_reel.generate_video_from_text", return_value=b"fake-video-bytes"
    ) as mock_generate, \
         patch("generate_reel.send_video_for_approval", return_value=100) as mock_send:
        exit_code = generate_reel.main(
            ["text", "알파카 아침 산책", "--duration", "9", "--aspect-ratio", "9:16"]
        )

    assert exit_code == 0
    mock_generate.assert_called_once_with("알파카 아침 산책", duration=9, aspect_ratio="9:16")
    mock_send.assert_called_once_with(b"fake-video-bytes")
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `cd reels && python -m pytest tests/test_generate_reel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'generate_reel'`

- [ ] **Step 3: 최소 구현 작성**

`reels/generate_reel.py`:
```python
import argparse
import sys

from higgsfield_client import generate_video_from_image, generate_video_from_text, HiggsfieldError
from telegram_sender import send_video_for_approval


def run_photo(image_path: str, prompt: str, duration: int) -> int:
    try:
        video_bytes = generate_video_from_image(image_path, prompt, duration=duration)
    except HiggsfieldError as e:
        print(f"[Higgsfield 생성 실패] {e}", file=sys.stderr)
        return 1
    message_id = send_video_for_approval(video_bytes)
    print(f"승인 채널에 전송 완료 (message_id={message_id}). 텔레그램에서 승인/수정/거절 해주세요.")
    return 0


def run_text(prompt: str, duration: int, aspect_ratio: str) -> int:
    try:
        video_bytes = generate_video_from_text(prompt, duration=duration, aspect_ratio=aspect_ratio)
    except HiggsfieldError as e:
        print(f"[Higgsfield 생성 실패] {e}", file=sys.stderr)
        return 1
    message_id = send_video_for_approval(video_bytes)
    print(f"승인 채널에 전송 완료 (message_id={message_id}). 텔레그램에서 승인/수정/거절 해주세요.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Higgsfield로 쥬쥬랜드 릴스 생성 후 텔레그램 승인 채널로 전송"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    photo_p = sub.add_parser("photo", help="사진 1장을 영상으로 애니메이션화")
    photo_p.add_argument("image_path")
    photo_p.add_argument("prompt")
    photo_p.add_argument("--duration", type=int, default=10)

    text_p = sub.add_parser("text", help="텍스트 프롬프트만으로 영상 생성")
    text_p.add_argument("prompt")
    text_p.add_argument("--duration", type=int, default=10)
    text_p.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "16:9", "1:1"])

    args = parser.parse_args(argv)

    if args.command == "photo":
        return run_photo(args.image_path, args.prompt, args.duration)
    return run_text(args.prompt, args.duration, args.aspect_ratio)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd reels && python -m pytest tests/test_generate_reel.py -v`
Expected: PASS — `3 passed`

- [ ] **Step 5: 전체 테스트 스위트 통과 확인**

Run: `cd reels && python -m pytest tests/ -v`
Expected: PASS — `11 passed`

- [ ] **Step 6: 커밋**

```bash
git add reels/generate_reel.py reels/tests/test_generate_reel.py
git commit -m "feat(reels): add CLI entry point for photo/text reel generation"
```

---

## Task 6: 수동 End-to-End 스모크 테스트

자동화된 테스트가 아니라, 실제 Higgsfield 계정과 실제 운영 중인 텔레그램 봇으로 전체 경로가 맞물려 동작하는지 사람이 직접 확인하는 단계다. 여기서부터는 실제 비용(Higgsfield 크레딧)이 발생한다.

**Files:** 없음 (Task 1-5에서 만든 `reels/generate_reel.py` 사용)

- [ ] **Step 1: `.env` 준비**

`reels/.env.example`을 복사해 `reels/.env` 생성. `HF_API_KEY_ID`/`HF_API_KEY_SECRET`은 [console.higgsfield.ai](https://console.higgsfield.ai)에서 발급. `TELEGRAM_BOT_TOKEN`/`APPROVAL_CHAT_ID`는 `instagram/.env.new`에 이미 있는 값을 그대로 복사(같은 봇·같은 승인 채널을 재사용).

- [ ] **Step 2: 의존성 설치**

Run: `cd reels && pip install -r requirements.txt`

- [ ] **Step 3: 실제 사진으로 생성 실행**

Run: `cd reels && python generate_reel.py photo <실제 동물 사진 경로> "따뜻한 아침 햇살 아래 알파카가 건초를 먹는 모습, 시네마틱"`
Expected: 터미널에 `승인 채널에 전송 완료 (message_id=...)` 출력. 실패 시 `[Higgsfield 생성 실패] ...` 메시지로 원인(인증/모델/타임아웃) 확인 가능.

- [ ] **Step 4: 텔레그램에서 확인**

APPROVAL_CHAT_ID 채널을 열어 영상 미리보기 + Claude Vision이 생성한 캡션 카드 + 승인/수정/거절 버튼이 도착했는지 확인한다(이 부분은 기존 파이프라인이 처리하므로 새 코드 없이 그대로 동작해야 함).

- [ ] **Step 5: 실게시 여부 결정**

바로 실게시하고 싶지 않다면 승인 버튼을 누르지 말고 종료(큐에 안 들어가므로 게시 안 됨). 실제 게시까지 확인하려면 승인 버튼을 눌러 큐에 넣고, 예약 시각에 Make를 거쳐 Instagram Reels에 게시되는지 최종 확인한다.

---

## Self-Review 결과

- **스펙 커버리지**: `higgsfield_client.py`(Task 1-3), `telegram_sender.py`(Task 4), `generate_reel.py` photo/text 서브커맨드(Task 5), 수동 E2E 검증(Task 6) — 스펙의 "신규 컴포넌트"·"테스트/검증 방법" 섹션을 모두 커버함. `trend` 서브커맨드는 스펙에 명시된 대로 별도 코드가 아니라 Claude가 프롬프트를 작성해 `text`/`photo` 커맨드를 호출하는 워크플로이므로 구현 대상에서 제외(스펙과 일치).
- **타입 일관성 확인**: `generate_video_from_image`/`generate_video_from_text`가 Task 3에서 정의한 시그니처를 Task 5의 `run_photo`/`run_text`가 그대로 사용함. `send_video_for_approval(video_bytes: bytes, filename: str = "reel.mp4") -> int` 시그니처가 Task 4와 Task 5에서 일치함.
- **플레이스홀더 스캔**: 없음 — 모든 코드 블록이 완전한 구현.
