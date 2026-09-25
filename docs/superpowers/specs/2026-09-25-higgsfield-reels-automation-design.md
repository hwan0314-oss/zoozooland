# Higgsfield 릴스 자동 생성 파이프라인 설계

## 배경

쥬쥬랜드(ZZL) 인스타그램은 이미 텔레그램 → Claude Vision 캡션 생성 → 승인 → 큐 → Make 웹훅 → Instagram(사진/카루셀/릴스)으로 자동 게시하는 파이프라인이 Oracle Cloud 서버(`152.69.239.249`)에서 `instagram_bot.py`(systemd 서비스 `zzl-instagram.service`)로 상시 운영 중이다. 사진뿐 아니라 **영상 → 릴스 게시까지 이미 완성되어 있다**:

- `handle_video` (텔레그램 VIDEO/영상 Document 수신) → `_extract_video_frames`(ffmpeg) → `generate_video_caption`(Claude Vision, `VIDEO_BRAND_PROMPT`) → 승인 채널에 영상 미리보기 + 승인/수정/거절 버튼 → 승인 시 `post_type="video"`로 큐 저장 → 예약 시각에 `post_video()` 실행 → `MAKE_WEBHOOK_URL`로 `{media_type: "video", video_url, caption, id}` POST → Make 시나리오(`Integration Webhooks, Instagram for Business`)의 Router "2nd video posting" 분기 → Instagram "Create a reel post"
- 영상은 텍스트 오버레이 없이 원본 그대로 올라가고, 브랜드 메시지는 캡션으로만 전달하는 것이 기존 방침(`VIDEO_BRAND_PROMPT`에 명시).

> 주의: 로컬 git 클론(`C:\Users\식대디\Documents\GitHub\zoozooland`)은 서버에 실제 배포된 코드보다 뒤처져 있다(로컬 864줄 vs 서버 1413줄). 이 설계는 **SSH로 확인한 서버의 실제 배포 코드**를 기준으로 한다. 로컬 레포를 서버와 동기화하는 작업은 이 프로젝트의 범위 밖이다.

## 목표

Higgsfield API(종량제, 구독 불필요)로 쥬쥬랜드 릴스 영상을 AI로 생성하고, **이미 동작 중인 영상 승인·큐·게시 파이프라인에 그대로 얹는다.** 서버 측 코드는 건드리지 않는다.

### 이번 범위 (Phase 1 + Phase 3)

- **Phase 1**: 로컬 사진 1장 + 프롬프트 → Higgsfield 이미지→영상 생성 → 기존 파이프라인으로 전달 (텍스트만으로 생성하는 text→video도 지원)
- **Phase 3**: 인스타그램 릴스 링크를 참고자료로 주면, Claude가 그 릴스의 스타일(카메라 무빙/템포/분위기)을 분석해 유사한 프롬프트를 작성 → Phase 1과 동일한 명령으로 생성. 별도 코드 없음.

### 범위 밖

- 텔레그램에서 직접 사진/스토리 텍스트를 받아 자동으로 Higgsfield를 호출하는 기능 (Phase 2)
- 서버 코드 수정, 로컬-서버 레포 동기화

## 핵심 제약: 봇은 자기 메시지를 받지 못한다

텔레그램 봇은 자신이 보낸 메시지(그리고 다른 봇이 보낸 메시지)에 대한 업데이트를 받지 못한다. 따라서 서버 봇과 같은 봇 토큰으로 영상을 승인 채널에 보내면 `handle_video`가 동작하지 않는다. 이를 피하기 위해 **사용자 본인의 텔레그램 계정(Telethon, MTProto 사용자 클라이언트)으로 영상을 승인 채널에 올린다.** 서버 봇 입장에서는 직원이 채널에 영상을 올린 것과 동일하므로 기존 흐름이 그대로 이어진다.

## 트리거 방식

Claude Code(로컬)에서 사람이 명령을 내려 실행한다. 자동 스케줄링 없음.

```
python generate_reel.py photo <이미지경로> "<프롬프트>" [--duration 10]
python generate_reel.py text "<프롬프트>" [--duration 10] [--aspect-ratio 9:16]
```

## 아키텍처

```
[Claude Code / 로컬 스크립트]
  1) (photo) 사진을 9:16 세로로 가운데 기준 자동 크롭 (EXIF 회전 보정 포함)
  2) (photo) Higgsfield 파일 업로드 → 공개 URL 확보
  3) Higgsfield Kling 3.0 Standard 호출 (image-to-video 또는 text-to-video)
  4) status_url 폴링 → 완료 시 영상 URL → mp4 다운로드
  5) mp4를 reels/output/에 저장 (텔레그램 전송이 실패해도 비용 들인 영상을 잃지 않도록)
  6) Telethon(사용자 계정)으로 승인 채널(APPROVAL_CHAT_ID)에 영상 게시
        │
        ▼
[Oracle 서버 - 기존 instagram_bot.py, 코드 변경 없음]
  handle_video → 프레임 추출 → Claude Vision 캡션 → 승인 카드
        │  (사람이 승인/수정/거절)
        ▼
  큐(post_type="video") → 예약 시각 post_video() → Make 웹훅 → Instagram Reels
```

## 신규 컴포넌트 (로컬 전용, `reels/` 폴더)

### `higgsfield_client.py`
- `upload_image(image_bytes: bytes, content_type: str = "image/jpeg") -> str` — `POST /files/generate-upload-url` → presigned URL에 PUT → `public_url` 반환
- `_poll_until_done(status_url, timeout_seconds=600.0) -> dict` — 2초에서 시작해 최대 10초까지 늘리는 백오프 + 지터, 종료 상태 `completed/failed/nsfw/canceled`
- `_submit_and_download(endpoint, payload) -> bytes` — 요청 제출 → 폴링 → 다운로드 공통 흐름
- `generate_video_from_image(image_path, prompt, duration=10) -> bytes` — 9:16 크롭 → 업로드 → `POST /kling-video/v3.0/std/image-to-video`
- `generate_video_from_text(prompt, duration=10, aspect_ratio="9:16") -> bytes` — `POST /kling-video/v3.0/std/text-to-video`
- 인증: `Authorization: Key {HF_API_KEY_ID}:{HF_API_KEY_SECRET}`
- 모든 실패는 `HiggsfieldError`로 올림

### `image_prep.py`
- `crop_to_vertical(image_path: str) -> bytes` — EXIF 회전 보정 후 가운데 기준 9:16 크롭, JPEG 바이트 반환. Kling image-to-video는 비율 파라미터가 없고 입력 이미지 비율을 따르므로 필요.

### `telegram_sender.py`
- `send_video_for_approval(video_bytes, filename="reel.mp4") -> int` — Telethon으로 승인 채널에 영상 게시, 메시지 ID 반환. 로그인 안 된 상태면 `TelegramSendError`.
- `python telegram_sender.py` 직접 실행 시 1회 대화형 로그인(전화번호 + 인증코드는 사용자가 직접 입력) → `reels/zzl_reels.session` 저장

### `generate_reel.py` (CLI)
- `photo`, `text` 서브커맨드. 공통 흐름은 `_generate_and_send(generate)` 하나로 처리: 생성 → `reels/output/`에 저장 → 텔레그램 전송

## 영상 스펙
- 9:16 세로, 기본 10초(Kling 허용 범위 3~15초, 권장 8~15초)
- 텍스트/로고 오버레이 없음 — 브랜드 메시지는 기존 파이프라인의 캡션으로만

## 에러 처리
- Higgsfield 실패/타임아웃: 로컬에 에러 출력, 종료 코드 1, 텔레그램엔 아무 것도 안 보냄
- 텔레그램 전송 실패(미로그인 등): 로컬에 에러 + 저장된 mp4 경로 출력 → 직접 업로드 가능
- 승인 이후 실패는 기존 파이프라인의 알림("❌ 예약 포스팅 실패")을 그대로 사용

## 설정 / 시크릿 (`reels/.env`, git 제외)
- `HF_API_KEY_ID`, `HF_API_KEY_SECRET` — console.higgsfield.ai
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` — my.telegram.org에서 사용자가 직접 발급
- `APPROVAL_CHAT_ID` — 서버 `.env`의 값과 동일해야 함
- `reels/.gitignore`로 `.env`, `*.session`, `output/` 제외

## 테스트/검증
1. 단위 테스트: Higgsfield/Telethon 호출은 mock, 크롭은 Pillow로 만든 실제 이미지로 검증
2. 수동 E2E: 실제 사진으로 `generate_reel.py photo` 실행 → 승인 채널에 영상 + 캡션 카드 + 버튼 도착 확인
3. (선택) 승인 → 예약 시각에 Instagram Reels 게시 확인

## 비용 참고
Higgsfield는 선불 USD 잔액 종량제(최소 충전 $5), 실패/NSFW 요청은 과금 안 됨. 주 1~2회 사용 시 월 비용 소액.

## 알려진 리스크 / 후속 과제
- 로컬 git 레포가 서버 배포본보다 뒤처져 있음 — 별도 세션에서 동기화 필요
- AI 생성 영상이 실제 동물원 촬영물 톤과 어울리는지는 결과물을 보고 판단 — 초기엔 승인 검토를 꼼꼼히
