# Higgsfield 릴스 자동 생성 파이프라인 설계

## 배경

쥬쥬랜드(ZZL) 인스타그램은 이미 텔레그램 → Claude Vision 캡션 생성 → 승인 → 큐 → Make 웹훅 → Instagram(사진/영상 카루셀/릴스 포함)으로 자동 게시하는 파이프라인이 Oracle Cloud 서버(`152.69.239.249`)에서 `instagram_bot.py`(systemd 서비스 `zzl-instagram.service`)로 상시 운영 중이다. 사진뿐 아니라 **영상 → 릴스 게시까지 이미 완성되어 있다**:

- `handle_video` (텔레그램 VIDEO/영상 Document 수신) → `_extract_video_frames`(ffmpeg) → `generate_video_caption`(Claude Vision, `VIDEO_BRAND_PROMPT`) → 승인 채널에 영상 미리보기 + 승인/수정/거절 버튼 → 승인 시 `post_type="video"`로 큐 저장 → 예약 시각에 `post_video()` 실행 → `MAKE_WEBHOOK_URL`로 `{media_type: "video", video_url, caption, id}` POST → Make 시나리오(`Integration Webhooks, Instagram for Business`)의 Router "2nd video posting" 분기 → Instagram "Create a reel post"
- 영상은 텍스트 오버레이 없이 원본 그대로 올라가고, 브랜드 메시지는 캡션으로만 전달하는 것이 기존 방침(`VIDEO_BRAND_PROMPT`에 명시).

> 주의: 로컬 git 클론(`C:\Users\식대디\Documents\GitHub\zoozooland`)은 서버에 실제 배포된 코드보다 뒤처져 있다(로컬 864줄 vs 서버 1413줄, `git diff` 기준 1084줄 차이). 이 설계는 **SSH로 확인한 서버의 실제 배포 코드**를 기준으로 한다. 로컬 레포를 서버와 동기화하는 작업은 이 프로젝트의 범위 밖이며, 별도로 처리 필요.

## 목표

Higgsfield API(pay-as-you-go, 50+ 이미지/영상 생성 모델)를 이용해 쥬쥬랜드 릴스 소스를 AI로 생성하고, **기존에 이미 동작 중인 영상 승인·큐·게시 파이프라인에 그대로 얹는다.** 서버 측 코드는 건드리지 않는다.

### 이번 범위 (Phase 1 + Phase 3)

- **Phase 1**: 로컬 사진 1장 + 프롬프트 → Higgsfield 이미지→영상 생성 → 기존 파이프라인으로 전달
- **Phase 3**: 인스타그램 릴스 링크를 참고자료로 주면, Claude가 그 릴스의 스타일(카메라 무빙/템포/분위기)을 분석해 유사한 프롬프트를 작성 → Phase 1과 동일한 경로로 생성

### 범위 밖 (다음 단계, 이번엔 구현 안 함)

- 텔레그램에서 직접 사진/스토리 텍스트를 받아 자동으로 Higgsfield를 호출하는 기능 (Phase 2) — 이번엔 Claude Code에서 수동으로 트리거
- 서버 코드 수정, 로컬-서버 레포 동기화

## 트리거 방식

Claude Code(로컬)에서 사람이 명령을 내려 실행한다. 자동 스케줄링/자동 트리거는 없음.

```
python generate_reel.py photo <이미지경로> "<프롬프트>"
python generate_reel.py trend <참고할 릴스 URL> <이미지경로> "<보충 설명>"   # Claude가 프롬프트를 대신 작성
```

## 아키텍처

```
[Claude Code / 로컬 스크립트]
  1) higgsfield_client.py로 Higgsfield API 호출 (이미지→영상 또는 텍스트→영상)
  2) status_url 폴링 → 완료되면 Higgsfield가 호스팅하는 영상 URL 확보 (최소 7일 유지)
  3) 영상을 로컬로 다운로드 (mp4)
  4) 텔레그램 Bot API(sendVideo)로 승인 채널(APPROVAL_CHAT_ID)에 직접 전송
        │
        ▼
[Oracle 서버 - 기존 instagram_bot.py, 코드 변경 없음]
  handle_video가 감지 → 프레임 추출 → Claude Vision 캡션 생성 → 승인 카드 전송
        │  (사람이 승인/수정/거절 버튼 클릭)
        ▼
  큐 저장(post_type="video") → 예약 시각에 post_video() → Make 웹훅
        │
        ▼
  Make Router "2nd video posting" → Instagram "Create a reel post"
```

**왜 이 구조인가**: 캡션 생성, 승인 UX, 큐잉, 스케줄링, Make를 통한 릴스 게시가 이미 검증된 상태로 운영 중이므로, Higgsfield 생성 결과를 "텔레그램으로 영상을 보낸 것"과 동일하게 만들어 기존 파이프라인에 그대로 흘려보내는 것이 가장 안전하고 작은 변경이다. 서버 코드를 한 줄도 건드리지 않아 기존 사진/실제영상 파이프라인에 회귀 위험이 없다.

## 신규 컴포넌트 (로컬 전용, 서버 미배포)

로컬 저장 위치: `C:\Users\식대디\Documents\GitHub\zoozooland\reels\` (신규 폴더 — 기존 `instagram/`과 분리해 서버 배포 코드와 섞이지 않도록 함)

### `higgsfield_client.py`

- `generate_video_from_image(image_path: str, prompt: str, aspect_ratio="9:16", duration=10) -> bytes`
  Higgsfield 이미지→영상 모델 엔드포인트에 `prompt`+`image_url`(또는 base64) 전송 → `status_url` 폴링(완료까지, 최대 수 분) → 완료된 영상을 다운로드해 바이트로 반환
- `generate_video_from_text(prompt: str, aspect_ratio="9:16", duration=10) -> bytes`
  텍스트→영상 모델 호출, 동일한 폴링/다운로드 흐름
- 인증: `HF_API_KEY_ID` / `HF_API_KEY_SECRET` 환경변수 (`Authorization: Key {id}:{secret}`)
- 모델: 기본값은 비용 대비 품질이 무난한 모델 1개로 시작(콘솔에서 실제 카탈로그 확인 후 상수로 고정), 필요시 쉽게 교체 가능하도록 모델명을 설정값으로 분리
- 실패 시(생성 실패, 타임아웃) 예외를 그대로 올려서 CLI가 사람이 읽을 에러 메시지를 출력하게 함 — 텔레그램에는 아무 것도 보내지 않음(승인 채널은 "검증된 결과물만" 보는 채널로 유지)

### `generate_reel.py` (CLI, 로컬 수동 실행)

- `photo` 서브커맨드: 이미지 경로 + 프롬프트 → `generate_video_from_image` → mp4 저장 → 텔레그램 `sendVideo`로 `APPROVAL_CHAT_ID`에 전송
- `trend` 서브커맨드: 참고 릴스 URL + 이미지 경로 + 보충 설명 인자를 받되, **프롬프트 작성 자체는 이 스크립트가 아니라 Claude Code 세션이 담당**한다. 흐름:
  1. Claude가 브라우저 도구로 참고 릴스를 직접 관찰 (카메라 무빙/컷 타이밍/분위기 파악)
  2. Claude가 쥬쥬랜드 브랜드에 맞는 유사 스타일 프롬프트를 작성
  3. 그 프롬프트로 `photo` 경로와 동일하게 생성 실행
  - 즉 `trend`는 별도 자동 분석 코드가 아니라 "Claude가 프롬프트를 대신 써주는 워크플로"이며, 최종적으로는 `photo` 서브커맨드와 같은 함수를 호출
- 텔레그램 전송은 `python-telegram-bot`의 `Bot(token=TELEGRAM_BOT_TOKEN).send_video(chat_id=APPROVAL_CHAT_ID, video=<mp4 bytes>)` 직접 호출 (서버 봇 프로세스와 별개의 클라이언트로, 같은 봇 토큰을 재사용 — 텔레그램 Bot API는 동일 토큰으로 여러 클라이언트가 메시지를 "보내는" 것 자체는 문제 없음. 서버 봇은 long-polling으로 새 메시지를 받아 처리하므로 충돌 없음)

## 영상 스펙 (권장값, Higgsfield 호출 시 적용)

- 9:16 세로
- 8~15초 (Meta 릴스 탭 노출 조건은 5~90초지만, 비용·몰입도 고려해 짧게)
- 텍스트/로고 오버레이 없음 — 기존 `VIDEO_BRAND_PROMPT` 방침과 동일하게 캡션으로만 브랜드 메시지 전달

## 에러 처리

- Higgsfield 생성 실패/타임아웃: `generate_reel.py`가 로컬 터미널에 에러 출력, 프로세스 종료 (재시도는 사람이 판단해 재실행)
- 텔레그램 전송 실패: 마찬가지로 로컬에서 에러 출력. 이 시점 이후는 기존 파이프라인 책임 영역이라 별도 처리 불필요 (기존 파이프라인의 실패 알림 로직 — 예: "❌ 예약 포스팅 실패" — 을 그대로 재사용)

## 설정 / 시크릿

- 로컬 `.env`(신규 또는 기존 `instagram/.env.new` 재사용)에 추가: `HF_API_KEY_ID`, `HF_API_KEY_SECRET`
- `TELEGRAM_BOT_TOKEN`, `APPROVAL_CHAT_ID`는 기존 `.env.new`에 이미 존재 — 재사용

## 테스트/검증 방법

1. `higgsfield_client.py` 단독 테스트: 샘플 사진 1장으로 영상 생성 → 재생 가능한 mp4인지 로컬에서 확인
2. `generate_reel.py photo` 전체 흐름: 실행 → 승인 채널에 영상 미리보기 + 캡션 카드가 실제로 도착하는지 확인
3. 승인 버튼 클릭 → 큐(`queue.json`, 서버)에 `post_type="video"` 항목이 정상 추가되는지 확인(운영에 영향 없는 시간대에 테스트하거나, 승인 후 게시 전 큐에서 수동 제거로 실게시 방지)
4. (선택, 실제 게시 검증이 필요할 때만) 예약 시각 도달 시 Make 웹훅 호출 → Instagram Reels에 정상 게시되는지 최종 확인

## 비용 참고

Higgsfield는 선불 USD 잔액 기반 종량제(구독 불필요, 최소 충전 $5). 10초 클립 기준 모델별로 대략 $0.1~$1대 — 주 1~2회 사용 시 월 비용은 크지 않을 것으로 예상(정확한 금액은 실제 선택 모델의 콘솔 단가 확인 필요).

## 알려진 리스크 / 후속 과제

- 로컬 git 레포가 서버 배포본보다 뒤처져 있음 — 이번 작업으로 더 벌어지지 않도록 신규 파일은 로컬에만 두고 서버에 배포하지 않지만, 근본적으로는 별도 세션에서 로컬↔서버 동기화가 필요
- Higgsfield로 생성한 영상이 브랜드 톤(실제 동물원 촬영물 느낌)과 어울리는지는 실제 결과물을 보고 판단 필요 — 초기 몇 개는 특히 꼼꼼한 승인 검토 권장
