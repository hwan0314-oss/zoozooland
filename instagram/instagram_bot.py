import asyncio
import base64
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone, timedelta, time as dtime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import time
import httpx
import requests
import anthropic
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─── Config ───────────────────────────────────────────────────────────────────

BOT_TOKEN            = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
APPROVAL_CHAT_ID     = int(os.environ.get("APPROVAL_CHAT_ID", "-1003990713280"))
IMGBB_API_KEY        = os.environ["IMGBB_API_KEY"]
MAKE_WEBHOOK_URL     = os.environ["MAKE_WEBHOOK_URL"]
MEDIA_BASE_URL       = "http://152.69.239.249/media"

# 기본 connect timeout(5s)이 너무 짧아 일시적 네트워크 지연에도 끊겨서 read timeout은 넉넉히 유지
_ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=httpx.Timeout(600.0, connect=20.0))

QUEUE_FILE      = Path(__file__).parent / "queue.json"
QUEUE_MEDIA_DIR = Path(__file__).parent / "queue_media"
QUEUE_MEDIA_DIR.mkdir(exist_ok=True)

KST = timezone(timedelta(hours=9))

_pending_groups: dict = {}

# ─── Prompts ──────────────────────────────────────────────────────────────────

BRAND_PROMPT = """\
너는 ZZL(쥬쥬랜드) 인스타그램 콘텐츠 기획자 겸 카피라이터야.

## 브랜드 정보
- 브랜드명: 쥬쥬랜드 (ZZL / zoozooland)
- 업종: 동물원 & 체험형 레저시설
- 브랜드 컬러: 딥그린(#44B134) + 블랙
- 톤: 힙하되 과하지 않게. 짧고 임팩트 있게.

## 콘텐츠 컨셉
"동물이 보여주는 인간 이야기"
- 동물 사진을 보고 그 동물의 실제 습성/행동을 인간관계·감정·일상으로 연결
- 동물에 대한 단순 설명 NO
- 공감, 저장, 공유를 유발하는 카피 작성

## 1. 콘텐츠 유형 — 사진을 분석해서 가장 적합한 1개를 선택하고 이유를 댈 것

**유머형**
- "직장동료 같은 동물", "카톡 씹는 친구 vs 이 동물" 식의 가볍고 공감되는 톤
- 빵 터지는 포인트가 있는 굵고 임팩트 있는 카피
- 보는 사람이 "이거 완전 나" 하며 바로 저장하거나 지인한테 보내고 싶게

**다큐형**
- 자연 다큐 내레이터처럼 담담하고 절제된 톤으로 동물의 행동/습성을 관찰해서 서술
- 설명이 아닌 관찰: "~한다", "~이다" 식의 짧고 건조한 문장 구조
- 마지막에 인간 관계·감정으로 조용히 연결 — 감동을 강요하지 않고 여운으로 남기기
- 동물 생태 사실만(관찰 가능한 것), 출처 없는 수치·연구 인용 금지

**공감형**
- 서정적 감성 카피 또는 극한 공감 — 저장하게 만드는 여운이 목표
- 메인: 한국어 2줄 이내, 짧고 밀도 있게
- 서브: 영문 이탤릭 한 줄로 받쳐주기 (예: "that's why they call it lovebird")
- "나 이거야" 공감이든 "이 감정 딱이다" 서정이든, 보는 사람의 내면을 건드리는 방향

## 2. 포맷 — 단일 또는 캐러셀(2장) 중 선택
사진이 1장이어도 유형상 캐러셀이 더 효과적이면 캐러셀을 추천해.
캐러셀이면 같은 사진을 배경으로 두 번 쓰고 텍스트 레이어만 슬라이드별로 다르게 구성해.

## 3. 피사체 위치 분석 & 텍스트 배치
사진 속 동물(피사체)이 프레임의 어느 영역에 있는지 파악하고,
텍스트가 피사체를 가리지 않을 여백 위치를 아래 중 하나로 정해:
- top / bottom / left / right / center / split (상하 분리, 다큐형 전용)

**유형별 배치·스타일 가이드**
- 유머형 → top 또는 left/right 여백. 굵고 임팩트 있는 폰트 톤
- 다큐형 → bottom 또는 split. 차분한 명조 계열 폰트 톤. split 시 상단엔 관찰 문장, 하단엔 인간적 연결 문장
- 공감형 → bottom 또는 center. 부드러운 감성 폰트 톤

## 캡션 (인스타 본문)
**목표: 이 유형이 노리는 반응(공감·저장·공유·참여) 하나를 확실히 때려라.**
정해진 단계 없어 — 사진과 유형에 따라 아래처럼 완전히 다른 흐름으로 써도 된다.

예시 A (유머형 — 짧고 빵 터지게):
"이 눈빛 아는 사람 손 🙋\\n뭔가 물어봤는데 '응~ 그냥~' 하는 그 친구.\\n#ZZL ..."

예시 B (다큐형 — 담담한 관찰 → 조용한 연결):
"알파카는 무리를 이루지만, 무리 안에서도 저마다 거리를 둔다.\\n서로를 밀어내는 것이 아니라, 각자의 온도를 지키는 방식이다.\\n.\\n가까이 있으되, 겹치지 않는다.\\n#ZZL ..."

예시 C (공감형 — 서정/감성으로 여운):
"누군가 가까이 있는데\\n이상하게 오늘따라 더 외롭다.\\n.\\n그래도 옆에 있어줘서 고마워.\\n#ZZL ..."

⚠️ 절대 금지 — 알고리즘 페널티 유발: "태그해줘" / "댓글로 알려주세요" / "공유해줘" / "전달만 해도" / "이런 사람 태그" 등 명시적 참여 유도 문구는 Instagram 정책상 도달률이 감소하므로 어떤 유형에서도 사용 금지.

규칙: 해시태그는 항상 마지막 / 출처 없는 수치·연구 인용 금지 / 이모지 1~2개 이내 / 1인칭(나는·내가) 금지
해시태그 구성: #ZZL #쥬쥬랜드 #ZZLstagram + 아래 풀에서 콘텐츠 분위기에 맞는 3~4개 선택 + 동물명 + 관련 감성 태그
- 데이트 탐색: #데이트코스 #데이트장소 #주말데이트 #커플데이트 #동물원데이트
- 가족/아이 탐색: #가족나들이 #아이랑가볼만한곳 #아이와함께 #주말나들이 #가족여행 #아이나들이
- 일반 나들이: #나들이 #나들이코스 #동물원

## 출력 형식
사진을 분석한 뒤, 아래 구조의 **JSON 코드블록 하나만** 출력해 (앞뒤에 다른 설명 문장 붙이지 말 것):

```json
{
  "analysis": "동물 종류/행동/분위기/카피 연결 포인트 — 1~2문장으로 간결하게",
  "content_type": "유머형 | 다큐형 | 공감형 중 하나",
  "type_reason": "이 유형을 고른 이유 — 한 문장으로 간결하게",
  "format": "단일 | 캐러셀",
  "text_position": "top | bottom | left | right | center | split",
  "card_style": "bar | dot | none",
  "slides": [
    {"main": "슬라이드1 메인 카피", "sub": "슬라이드1 서브 카피"}
  ],
  "caption": "캡션 전문 (해시태그 포함, 줄바꿈은 \\n으로) — 절대 중간에 끊기지 않게 끝까지 작성"
}
```

- card_style: none 고정 (bar/dot 사용 안 함)
- ⚠️ 반드시 유효한 JSON 문법을 지켜: 문자열 안에서 줄바꿈은 실제 개행이 아니라 \\n으로, 큰따옴표(")를 쓸 일이 있으면 작은따옴표(')나 따옴표 없이 표현해서 JSON이 깨지지 않게 해.
- analysis/type_reason는 짧게 쓰고, caption은 끝까지 충실하게 작성해 (절대 도중에 잘리면 안 됨).
- "단일" 포맷이면 slides 배열에 항목을 1개만, "캐러셀"이면 2개를 넣어.
- "다큐형"에서 split 레이아웃 선택 시: main에는 "인간적 연결 문장"(하단 강조용), sub에는 "관찰 문장"(상단 보조용)을 넣어 — main은 하단에 크게, sub는 상단에 작게 렌더링돼.
- 그 외 유형은 main=메인 카피(한국어), sub=서브 카피(영문 이탤릭 한 줄)로 기존 카드 구조와 동일하게 유지해.\
"""

VIDEO_BRAND_PROMPT = """\
너는 ZZL(쥬쥬랜드) 인스타그램 콘텐츠 기획자 겸 카피라이터야.
지금 받은 이미지들은 영상에서 시간 순서대로 추출한 여러 장면(프레임)이야 — 영상 자체가 아니라 정지 화면들이니,
여러 장면을 종합해서 영상 전체의 흐름과 분위기를 파악하고, 영상이라는 형식(릴스)을 감안해서 캡션을 써.

## 브랜드 정보
- 브랜드명: 쥬쥬랜드 (ZZL / zoozooland)
- 업종: 동물원 & 체험형 레저시설
- 브랜드 컬러: 딥그린(#44B134) + 블랙
- 톤: 힙하되 과하지 않게. 짧고 임팩트 있게.

## 콘텐츠 컨셉
"동물이 보여주는 인간 이야기" — 동물의 실제 습성/행동을 인간관계·감정·일상으로 연결.
동물에 대한 단순 설명 NO. 공감, 저장, 공유를 유발하는 캡션 작성.

이 영상은 카드 텍스트 오버레이 없이 원본 그대로 올라가고, 캡션(본문)만으로 메시지를 전달해야 해.

## 캡션 (인스타 본문)
**목표: 공감·저장·공유·참여 중 하나를 확실히 때려라.** 정해진 단계 없음 — 영상 분위기에 따라 자유롭게.

예시 A (유머형 — 짧고 빵 터지게):
"이 눈빛 아는 사람 손 🙋\\n뭔가 물어봤는데 '응~ 그냥~' 하는 그 친구.\\n#ZZL ..."

예시 B (다큐형 — 담담한 관찰 → 조용한 연결):
"알파카는 무리를 이루지만, 무리 안에서도 저마다 거리를 둔다.\\n서로를 밀어내는 것이 아니라, 각자의 온도를 지키는 방식이다.\\n.\\n가까이 있으되, 겹치지 않는다.\\n#ZZL ..."

예시 C (공감형 — 서정/감성으로 여운):
"누군가 가까이 있는데\\n이상하게 오늘따라 더 외롭다.\\n.\\n그래도 옆에 있어줘서 고마워.\\n#ZZL ..."

⚠️ 절대 금지 — 알고리즘 페널티 유발: "태그해줘" / "댓글로 알려주세요" / "공유해줘" / "전달만 해도" / "이런 사람 태그" 등 명시적 참여 유도 문구는 Instagram 정책상 도달률이 감소하므로 어떤 유형에서도 사용 금지.

규칙: 해시태그는 항상 마지막 / 출처 없는 수치·연구 인용 금지 / 이모지 1~2개 이내 / 1인칭(나는·내가) 금지
해시태그 구성: #ZZL #쥬쥬랜드 #ZZLstagram + 아래 풀에서 콘텐츠 분위기에 맞는 3~4개 선택 + 동물명 + 관련 감성 태그
- 데이트 탐색: #데이트코스 #데이트장소 #주말데이트 #커플데이트 #동물원데이트
- 가족/아이 탐색: #가족나들이 #아이랑가볼만한곳 #아이와함께 #주말나들이 #가족여행 #아이나들이
- 일반 나들이: #나들이 #나들이코스 #동물원

## 출력 형식
아래 구조의 **JSON 코드블록 하나만** 출력해 (앞뒤에 다른 설명 문장 붙이지 말 것):

```json
{
  "analysis": "장면/동물/분위기/카피 연결 포인트 — 1~2문장으로 간결하게",
  "title": "콘텐츠를 한눈에 알아볼 짧은 한국어 제목 (내부 관리용, 인스타에는 올라가지 않음)",
  "caption": "캡션 전문 (해시태그 포함, 줄바꿈은 \\n으로) — 절대 중간에 끊기지 않게 끝까지 작성"
}
```

⚠️ 반드시 유효한 JSON 문법을 지켜: 문자열 안에서 줄바꿈은 실제 개행이 아니라 \\n으로, 큰따옴표(")를 쓸 일이 있으면 작은따옴표(')나 따옴표 없이 표현해서 JSON이 깨지지 않게 해.\
"""

MULTI_BRAND_PROMPT = """\
너는 ZZL(쥬쥬랜드) 인스타그램 카드뉴스 카피라이터야.
위 사진들은 카루셀로 게시될 여러 장의 사진이야.

브랜드 컨셉: "동물이 보여주는 인간 이야기"
톤: 힙하되 과하지 않게. 짧고 임팩트 있게.

사진들을 하나의 스토리로 연결해서 아래 형식으로 출력해:

[사진 분석]
- 각 사진의 동물, 행동, 스토리 연결 포인트

[슬라이드 순서]
번호로 최적 순서 제안

[카드 메인 카피]
(전체를 관통하는 메인 카피, 2줄 이내)

[카드 서브 카피]
(영문, 이탤릭 감성, 한 줄)

[캡션 전문]
(스토리텔링 캡션 + #ZZL #쥬쥬랜드 #ZZLstagram 포함)\
"""


# ─── Queue ────────────────────────────────────────────────────────────────────

def load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: list):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def get_post_time(date_str: str) -> str:
    """날짜 기준 포스팅 시간 반환 (평일 12:00 / 주말 21:00)."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return "12:00" if d.weekday() < 5 else "21:00"


def _today_post_hour() -> tuple[int, int]:
    """오늘 포스팅 시각 (hour, minute) KST."""
    return (12, 0) if datetime.now(KST).weekday() < 5 else (21, 0)


def get_next_available_date() -> str:
    now = datetime.now(KST)
    today = now.date()
    ph, pm = _today_post_hour()
    candidate = today if (now.hour < ph or (now.hour == ph and now.minute < pm)) else today + timedelta(days=1)
    scheduled = {i["scheduled_date"] for i in load_queue()}
    while candidate.isoformat() in scheduled:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def add_to_queue(item_id: str, post_type: str, media_path: str, caption: str,
                 main_copy: str, sub_copy: str, raw_output: str,
                 extra_media: list = None) -> str:
    scheduled_date = get_next_available_date()
    queue = load_queue()
    queue.append({
        "id": item_id,
        "scheduled_date": scheduled_date,
        "post_type": post_type,
        "media_path": str(media_path),
        "extra_media": extra_media or [],
        "caption": caption,
        "main_copy": main_copy,
        "sub_copy": sub_copy,
        "raw_output": raw_output,
        "created_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    })
    save_queue(queue)
    return scheduled_date


def cancel_queue_item(item_id: str) -> bool:
    queue = load_queue()
    target = next((i for i in queue if i["id"] == item_id), None)
    if not target:
        return False
    cancelled_date = target["scheduled_date"]
    queue = [i for i in queue if i["id"] != item_id]
    for item in queue:
        if item["scheduled_date"] > cancelled_date:
            d = datetime.strptime(item["scheduled_date"], "%Y-%m-%d")
            item["scheduled_date"] = (d - timedelta(days=1)).strftime("%Y-%m-%d")
    save_queue(queue)
    _delete_queue_media(target)
    return True


def _delete_queue_media(item: dict):
    for p in [item.get("media_path")] + (item.get("extra_media") or []):
        if p and os.path.exists(p):
            os.unlink(p)


def save_media_to_queue(image_bytes: bytes, item_id: str, suffix: str = "photo") -> str:
    path = QUEUE_MEDIA_DIR / f"{item_id}_{suffix}.jpg"
    path.write_bytes(image_bytes)
    return str(path)


def save_video_to_queue(video_bytes: bytes, item_id: str) -> str:
    path = QUEUE_MEDIA_DIR / f"{item_id}_video.mp4"
    path.write_bytes(video_bytes)
    return str(path)


def _extract_video_frames(video_bytes: bytes) -> list[bytes]:
    """영상의 20%/50%/80% 지점 프레임 3장을 JPEG로 추출 (캡션 생성용, Claude Vision은 영상을 직접 못 읽음)."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vid_f:
        vid_f.write(video_bytes)
        vid_path = vid_f.name
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", vid_path],
            capture_output=True, text=True,
        )
        try:
            duration = float(probe.stdout.strip())
        except ValueError:
            duration = 0.0
        seeks = [duration * f for f in (0.2, 0.5, 0.8)] if duration > 0 else [0.0]

        frames = []
        for i, seek in enumerate(seeks):
            img_path = f"{vid_path}.{i}.jpg"
            result = subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{seek:.2f}", "-i", vid_path, "-frames:v", "1", "-q:v", "2", img_path],
                capture_output=True,
            )
            if result.returncode == 0 and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                frames.append(Path(img_path).read_bytes())
            if os.path.exists(img_path):
                os.unlink(img_path)
        if not frames:
            raise RuntimeError("ffmpeg 프레임 추출 실패 (영상 디코딩 불가)")
        return frames
    finally:
        if os.path.exists(vid_path):
            os.unlink(vid_path)


# ─── Instagram Posting (Make 웹훅) ────────────────────────────────────────────

def _upload_imgbb(image_bytes: bytes) -> str:
    """imgbb에 이미지 업로드 후 공개 URL 반환."""
    r = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY},
        files={"image": ("photo.jpg", image_bytes, "image/jpeg")},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"]["url"]


def post_photo(image_bytes: bytes, caption: str, item_id: str = "") -> str:
    """사진을 Make 웹훅으로 전송 → Instagram 포스팅."""
    image_url = _upload_imgbb(image_bytes)
    r = requests.post(
        MAKE_WEBHOOK_URL,
        data={"media_type": "photo", "image_url": image_url, "caption": caption, "id": item_id},
        timeout=30,
    )
    r.raise_for_status()
    return "make-posted"


def post_carousel(image_bytes_list: list, caption: str, item_id: str = "") -> str:
    """카루셀 첫 번째 카드를 Make 웹훅으로 전송."""
    image_url = _upload_imgbb(image_bytes_list[0])
    r = requests.post(
        MAKE_WEBHOOK_URL,
        data={"media_type": "photo", "image_url": image_url, "caption": caption, "id": item_id},
        timeout=30,
    )
    r.raise_for_status()
    return "make-posted"


def post_video(item_id: str, caption: str) -> str:
    """큐에 저장된(=nginx로 서빙 중인) 영상을 Make 웹훅으로 전송 → Instagram 릴스 포스팅."""
    video_url = f"{MEDIA_BASE_URL}/{item_id}_video.mp4"
    r = requests.post(
        MAKE_WEBHOOK_URL,
        data={"media_type": "video", "video_url": video_url, "caption": caption, "id": item_id},
        timeout=30,
    )
    r.raise_for_status()
    return "make-posted"


# ─── Card Image Rendering (Playwright) ────────────────────────────────────────

_CARD_FONTS = """\
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,400;1,600&family=Black+Han+Sans&family=Nanum+Myeongjo:wght@400;700&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 1080px; height: 1080px; overflow: hidden; background: #121212; }
.zzl-mark {
  position: absolute;
  top: 44px; left: 60px;
  font-family: 'Pretendard', sans-serif;
  font-size: 16px;
  font-weight: 300;
  letter-spacing: 0.18em;
  color: rgba(255,255,255,0.22);
  z-index: 10;
}
"""

# 위치별 카드 레이아웃 (텍스트 블록 정렬 + 스크림 그라디언트 방향)
_POSITION_LAYOUT = {
    "bottom": dict(
        justify="flex-end", align="flex-start", text_align="left",
        scrim_css="bottom: 0; left: 0; width: 100%; height: 55%;"
                  "background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.4) 60%, rgba(0,0,0,0) 100%);"),
    "top": dict(
        justify="flex-start", align="flex-start", text_align="left",
        scrim_css="top: 0; left: 0; width: 100%; height: 55%;"
                  "background: linear-gradient(to bottom, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.4) 60%, rgba(0,0,0,0) 100%);"),
    "left": dict(
        justify="center", align="flex-start", text_align="left",
        scrim_css="top: 0; left: 0; width: 62%; height: 100%;"
                  "background: linear-gradient(to right, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.35) 65%, rgba(0,0,0,0) 100%);"),
    "right": dict(
        justify="center", align="flex-end", text_align="right",
        scrim_css="top: 0; right: 0; width: 62%; height: 100%;"
                  "background: linear-gradient(to left, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.35) 65%, rgba(0,0,0,0) 100%);"),
    "center": dict(
        justify="center", align="center", text_align="center",
        scrim_css="top: 0; left: 0; width: 100%; height: 100%;"
                  "background: radial-gradient(circle, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.72) 100%);"),
}

# 유형별 타이포그래피 톤
_TYPE_TYPOGRAPHY = {
    "유머형": dict(
        main_family="'Black Han Sans', 'Pretendard', 'Apple SD Gothic Neo', sans-serif",
        main_size="78px", main_weight="400", main_color="#FFFFFF",
        sub_family="'Pretendard', 'Apple SD Gothic Neo', sans-serif", sub_style="normal",
        sub_weight="500", sub_size="30px", sub_color="rgba(255,255,255,0.7)"),
    "다큐형": dict(
        main_family="'Nanum Myeongjo', Georgia, serif",
        main_size="52px", main_weight="400", main_color="#FFFFFF",
        sub_family="'Nanum Myeongjo', Georgia, serif", sub_style="normal",
        sub_weight="400", sub_size="26px", sub_color="rgba(255,255,255,0.65)"),
    "공감형": dict(
        main_family="'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
        main_size="66px", main_weight="700", main_color="#FFFFFF",
        sub_family="'Cormorant Garamond', Georgia, serif", sub_style="italic",
        sub_weight="400", sub_size="32px", sub_color="rgba(255,255,255,0.75)"),
}


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _build_card_html(image_b64: str, main_copy: str, sub_copy: str,
                      content_type: str = "감성형", position: str = "bottom",
                      card_style: str = "bar") -> str:
    main_html = _esc(main_copy).replace("\n", "<br>")
    sub_html  = _esc(sub_copy).replace("\n", "<br>")
    typo = _TYPE_TYPOGRAPHY.get(content_type, _TYPE_TYPOGRAPHY["공감형"])
    _accent = ""
    _dot_html = ""

    if position == "split":
        # 정보+감동형 전용: 상단에 생태 정보(작게, sub) + 하단에 관계 메시지(강조, main)
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
{_CARD_FONTS}
.card {{
  width: 1080px; height: 1080px;
  position: relative;
  background-image: url('data:image/jpeg;base64,{image_b64}');
  background-size: cover;
  background-position: center;
}}
.scrim-top {{
  position: absolute;
  top: 0; left: 0; width: 100%; height: 32%;
  background: linear-gradient(to bottom, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0) 100%);
  pointer-events: none;
}}
.scrim-bottom {{
  position: absolute;
  bottom: 0; left: 0; width: 100%; height: 48%;
  background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.4) 60%, rgba(0,0,0,0) 100%);
  pointer-events: none;
}}
.info-block {{
  position: absolute;
  top: 56px; left: 60px; right: 60px;
  z-index: 10;
  font-family: {typo['sub_family']};
  font-style: {typo['sub_style']};
  font-weight: {typo['sub_weight']};
  font-size: {typo['sub_size']};
  color: {typo['sub_color']};
  line-height: 1.4;
  word-break: keep-all;
  overflow-wrap: break-word;
}}
.message-block {{
  position: absolute;
  bottom: 60px; left: 60px; right: 60px;
  z-index: 10;
  font-family: {typo['main_family']};
  font-weight: {typo['main_weight']};
  font-size: {typo['main_size']};
  color: {typo['main_color']};
  line-height: 1.2;
  letter-spacing: -0.025em;
  word-break: keep-all;
  overflow-wrap: break-word;
}}
</style>
</head>
<body>
<div class="card">
  <div class="scrim-top"></div>
  <div class="scrim-bottom"></div>
  <span class="zzl-mark">ZZL</span>
  <div class="info-block">{sub_html}</div>
  <div class="message-block">{_dot_html}{main_html}</div>
</div>
</body>
</html>"""

    layout = _POSITION_LAYOUT.get(position, _POSITION_LAYOUT["bottom"])
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
{_CARD_FONTS}
.card {{
  width: 1080px; height: 1080px;
  position: relative;
  background-image: url('data:image/jpeg;base64,{image_b64}');
  background-size: cover;
  background-position: center;
  display: flex;
  flex-direction: column;
  justify-content: {layout['justify']};
  align-items: {layout['align']};
  padding: 60px;
}}
.scrim {{
  position: absolute;
  {layout['scrim_css']}
  pointer-events: none;
}}
.text-block {{
  position: relative;
  z-index: 10;
  max-width: 760px;
  text-align: {layout['text_align']};
  {_accent}
}}
.main-copy {{
  font-family: {typo['main_family']};
  font-size: {typo['main_size']};
  font-weight: {typo['main_weight']};
  color: {typo['main_color']};
  line-height: 1.18;
  letter-spacing: -0.025em;
  margin-bottom: 16px;
  word-break: keep-all;
  overflow-wrap: break-word;
}}
.sub-copy {{
  font-family: {typo['sub_family']};
  font-style: {typo['sub_style']};
  font-weight: {typo['sub_weight']};
  font-size: {typo['sub_size']};
  color: {typo['sub_color']};
  line-height: 1.3;
  letter-spacing: 0.01em;
  word-break: keep-all;
  overflow-wrap: break-word;
}}
</style>
</head>
<body>
<div class="card">
  <div class="scrim"></div>
  <span class="zzl-mark">ZZL</span>
  <div class="text-block">
    {_dot_html}<div class="main-copy">{main_html}</div>
    <div class="sub-copy">{sub_html}</div>
  </div>
</div>
</body>
</html>"""


async def render_card_image(image_bytes: bytes, main_copy: str, sub_copy: str,
                             content_type: str = "감성형", position: str = "bottom",
                             card_style: str = "bar") -> bytes:
    """Playwright로 HTML 카드를 렌더링해서 JPEG bytes 반환."""
    from playwright.async_api import async_playwright

    b64 = base64.b64encode(image_bytes).decode()
    html = _build_card_html(b64, main_copy, sub_copy, content_type, position, card_style)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = await browser.new_page(viewport={"width": 1080, "height": 1080})
        await page.set_content(html, wait_until="networkidle", timeout=30000)
        screenshot = await page.screenshot(type="jpeg", quality=92, full_page=False)
        await browser.close()

    return screenshot


# ─── Claude API ────────────────────────────────────────────────────────────────

def _repair_json(text: str) -> str:
    """Claude가 문자열 안의 줄바꿈/따옴표를 이스케이프하지 않고 출력해 JSON이 깨지는 경우를 보정.
    문자열 안의 실제 개행은 \\n으로 바꾸고, 종료 따옴표가 아닌 듯한(뒤에 , : } ] 가 오지 않는) 따옴표는 \\"로 이스케이프한다."""
    out = []
    in_string = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if in_string:
            if ch == "\\" and i + 1 < n:
                out.append(ch); out.append(text[i + 1])
                i += 2
                continue
            if ch == "\n":
                out.append("\\n")
                i += 1
                continue
            if ch == "\r":
                i += 1
                continue
            if ch == '"':
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in ",:}]":
                    out.append(ch)
                    in_string = False
                else:
                    out.append('\\"')
                i += 1
                continue
            out.append(ch)
            i += 1
        else:
            out.append(ch)
            if ch == '"':
                in_string = True
            i += 1
    return "".join(out)


def _parse_single_content(raw: str) -> dict:
    """BRAND_PROMPT의 JSON 출력(유형/포맷/배치/슬라이드)을 파싱."""
    text = raw.strip()
    if "```" in text:
        fence = "```json" if "```json" in text else "```"
        text = text.split(fence, 1)[1].split("```", 1)[0]
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        try:
            data = json.loads(_repair_json(text))
        except json.JSONDecodeError:
            print(f"[_parse_single_content] JSON 파싱 실패: {e}\n--- raw ---\n{raw}\n-----------")
            raise
    slides = data.get("slides") or [{"main": "", "sub": ""}]
    return {
        "analysis":      data.get("analysis", ""),
        "content_type":  data.get("content_type", "감성형"),
        "type_reason":   data.get("type_reason", ""),
        "format":        data.get("format", "단일"),
        "text_position": data.get("text_position", "bottom"),
        "card_style":    data.get("card_style", "bar"),
        "slides":        slides,
        "main_copy":     slides[0].get("main", ""),
        "sub_copy":      slides[0].get("sub", ""),
        "caption":       data.get("caption", ""),
        "raw":           raw,
    }


def _parse_video_content(raw: str) -> dict:
    """VIDEO_BRAND_PROMPT의 JSON 출력(제목/캡션)을 파싱."""
    text = raw.strip()
    if "```" in text:
        fence = "```json" if "```json" in text else "```"
        text = text.split(fence, 1)[1].split("```", 1)[0]
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        try:
            data = json.loads(_repair_json(text))
        except json.JSONDecodeError:
            print(f"[_parse_video_content] JSON 파싱 실패: {e}\n--- raw ---\n{raw}\n-----------")
            raise
    return {
        "analysis": data.get("analysis", ""),
        "title":    data.get("title", ""),
        "caption":  data.get("caption", ""),
        "raw":      raw,
    }


def generate_video_caption(frames: list[bytes]) -> dict:
    client = _ANTHROPIC_CLIENT
    parts = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
              "data": base64.b64encode(f).decode()}} for f in frames]
    parts.append({"type": "text", "text": VIDEO_BRAND_PROMPT})
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1200,
        messages=[{"role": "user", "content": parts}],
    )
    return _parse_video_content(resp.content[0].text.strip())


def regenerate_video_caption(frames: list[bytes], original_raw: str, edit_request: str) -> dict:
    client = _ANTHROPIC_CLIENT
    parts = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
              "data": base64.b64encode(f).decode()}} for f in frames]
    parts.append({"type": "text", "text": VIDEO_BRAND_PROMPT})
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1200,
        messages=[
            {"role": "user", "content": parts},
            {"role": "assistant", "content": original_raw},
            {"role": "user", "content": (
                f"수정 요청: {edit_request}\n\n위 내용을 수정해주세요. 출력 형식(JSON 구조)은 그대로 유지해주세요."
            )},
        ],
    )
    return _parse_video_content(resp.content[0].text.strip())


def _parse_content(raw: str) -> dict:
    sections, current, lines = {}, None, []
    for line in raw.split("\n"):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            if current:
                sections[current] = "\n".join(lines).strip()
            current, lines = s[1:-1], []
        else:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return {
        "analysis":    sections.get("사진 분석", ""),
        "main_copy":   sections.get("카드 메인 카피", ""),
        "sub_copy":    sections.get("카드 서브 카피", ""),
        "caption":     sections.get("캡션 전문", ""),
        "slide_order": sections.get("슬라이드 순서", ""),
        "raw": raw,
    }


def generate_content(image_bytes: bytes) -> dict:
    client = _ANTHROPIC_CLIENT
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=2200,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": BRAND_PROMPT},
        ]}],
    )
    return _parse_single_content(resp.content[0].text.strip())


def generate_content_multi(images: list[bytes]) -> dict:
    client = _ANTHROPIC_CLIENT
    parts = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
              "data": base64.b64encode(img).decode()}} for img in images[:10]]
    parts.append({"type": "text", "text": f"총 {len(images)}장입니다.\n\n{MULTI_BRAND_PROMPT}"})
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1000,
        messages=[{"role": "user", "content": parts}],
    )
    return _parse_content(resp.content[0].text.strip())


def regenerate_with_edit(image_bytes: bytes, original_raw: str, edit_request: str, multi: bool = False) -> dict:
    """multi=True면 멀티 사진 카루셀(MULTI_BRAND_PROMPT, 구 bracket 포맷)용 수정."""
    client = _ANTHROPIC_CLIENT
    b64 = base64.b64encode(image_bytes).decode()
    prompt = MULTI_BRAND_PROMPT if multi else BRAND_PROMPT
    keep_note = "출력 형식은 그대로 유지해주세요." if multi else "출력 형식(JSON 구조)은 그대로 유지해주세요."
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=2200,
        messages=[
            {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": prompt},
            ]},
            {"role": "assistant", "content": original_raw},
            {"role": "user", "content": (
                f"수정 요청: {edit_request}\n\n"
                f"위 내용을 수정해주세요. 요청에 카피 문구뿐 아니라 유형(content_type), "
                f"포맷(format), 텍스트 위치(text_position) 변경이 포함되어 있다면 해당 필드도 "
                f"요청에 맞게 함께 갱신해주세요. {keep_note}"
            )},
        ],
    )
    raw = resp.content[0].text.strip()
    return _parse_content(raw) if multi else _parse_single_content(raw)


# ─── Scheduled Posting (평일 12:00 KST=03:00 UTC / 주말 21:00 KST=12:00 UTC) ──

async def scheduled_post_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(KST).date().isoformat()
    queue = load_queue()
    for item in queue:
        if item["scheduled_date"] != today:
            continue
        try:
            if item["post_type"] == "photo":
                pk = post_photo(Path(item["media_path"]).read_bytes(), item["caption"], item["id"])
            elif item["post_type"] == "carousel":
                paths = [item["media_path"]] + item.get("extra_media", [])
                pk = post_carousel([Path(p).read_bytes() for p in paths], item["caption"], item["id"])
            elif item["post_type"] == "video":
                pk = post_video(item["id"], item["caption"])
            else:
                continue
            # Make에 ZZL_OK 콜백이 없으므로 (콜백 모듈 추가 시 웹훅 연결이 깨지는 문제로 보류)
            # 웹훅 전송 성공 = 포스팅 성공으로 간주하고 즉시 큐에서 제거
            day_ko = ["월","화","수","목","금","토","일"][datetime.strptime(today, "%Y-%m-%d").weekday()]
            post_time = get_post_time(today)
            await context.bot.send_message(
                chat_id=APPROVAL_CHAT_ID,
                text=f"✅ 예약 포스팅 완료!\n📅 {today[:7].replace('-','/')}/{today[8:]} ({day_ko}) {post_time}\n📌 {item['main_copy']}\nPost ID: {pk}",
            )
            save_queue([i for i in load_queue() if i["id"] != item["id"]])
        except Exception as e:
            await context.bot.send_message(chat_id=APPROVAL_CHAT_ID, text=f"❌ 예약 포스팅 실패 ({today})\n{e}")
        break


# ─── Approval Keyboard ────────────────────────────────────────────────────────

def _approval_keyboard(post_key: str, is_multi: bool, is_video: bool = False) -> InlineKeyboardMarkup:
    if is_video:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ 승인 → 큐 추가", callback_data=f"approve_video_{post_key}")],
            [
                InlineKeyboardButton("✏️ 수정", callback_data=f"edit_{post_key}"),
                InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}"),
            ],
        ])
    label = "✅ 카루셀 승인" if is_multi else "✅ 승인 → 큐 추가"
    action = f"approve_carousel_{post_key}" if is_multi else f"approve_photo_{post_key}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=action)],
        [
            InlineKeyboardButton("✏️ 수정", callback_data=f"edit_{post_key}"),
            InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}"),
        ],
    ])


# ─── Single Photo Processing ──────────────────────────────────────────────────

async def _process_single(msg, image_bytes: bytes, context: ContextTypes.DEFAULT_TYPE, status_msg):
    try:
        content = generate_content(image_bytes)
    except Exception as e:
        await status_msg.edit_text(f"콘텐츠 생성 실패: {e}")
        return

    slides = content["slides"]
    is_carousel = content["format"] == "캐러셀" and len(slides) > 1
    n_cards = 2 if is_carousel else 1
    await status_msg.edit_text(f"카드 이미지 제작 중... 🎨 ({content['content_type']} · {'캐러셀 2장' if is_carousel else '단일'})")

    card_images = []
    for i in range(n_cards):
        slide = slides[i] if i < len(slides) else slides[0]
        try:
            card_images.append(await render_card_image(
                image_bytes, slide.get("main", ""), slide.get("sub", ""),
                content["content_type"], content["text_position"], content.get("card_style", "bar"),
            ))
        except Exception as e:
            print(f"카드 렌더링 실패 ({i}): {e}")
            card_images.append(image_bytes)

    await status_msg.delete()

    post_key = f"{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "type": "carousel" if is_carousel else "single",
        "card_image": card_images[0],
        "card_images": card_images,
        "original_image": image_bytes,
        "caption": content["caption"],
        "main_copy": content["main_copy"],
        "sub_copy": content["sub_copy"],
        "content_type": content["content_type"],
        "raw_output": content["raw"],
        "submitter": (msg.from_user.full_name if msg.from_user else '채널'),
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _approval_keyboard(post_key, is_carousel)
    submitter = msg.from_user.full_name if msg.from_user else '채널'
    header = (
        f"📸 *콘텐츠 미리보기*\n"
        f"제출: {submitter} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"🏷 유형: *{content['content_type']}* ({'캐러셀 2장' if is_carousel else '단일'})\n"
        f"   → {content['type_reason']}\n\n"
    )
    if is_carousel:
        preview = header + (
            f"1️⃣ *{slides[0].get('main','')}*\n   _{slides[0].get('sub','')}_\n\n"
            f"2️⃣ *{slides[1].get('main','')}*\n   _{slides[1].get('sub','')}_"
        )
    else:
        preview = header + f"📌 메인: *{content['main_copy']}*\n💬 서브: _{content['sub_copy']}_"

    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID, photo=card_images[0],
        caption=preview[:1024], parse_mode="Markdown", reply_markup=keyboard,
    )
    if is_carousel:
        await context.bot.send_photo(chat_id=APPROVAL_CHAT_ID, photo=card_images[1], caption="2️⃣ 두 번째 슬라이드")
    # 전체 캡션 별도 메시지로 전송
    await context.bot.send_message(
        chat_id=APPROVAL_CHAT_ID,
        text=f"📝 *캡션 전문*\n\n{content['caption']}",
        parse_mode="Markdown",
    )
    if msg.chat_id != APPROVAL_CHAT_ID:
        await msg.reply_text("담당자에게 승인 요청을 보냈습니다. ✉️")


# ─── Video Processing (카드 오버레이 없이 원본 영상 + 캡션) ──────────────────────

async def _process_video(msg, video_bytes: bytes, context: ContextTypes.DEFAULT_TYPE, status_msg):
    try:
        frames = _extract_video_frames(video_bytes)
    except Exception as e:
        await status_msg.edit_text(f"프레임 추출 실패: {e}")
        return
    try:
        content = generate_video_caption(frames)
    except Exception as e:
        await status_msg.edit_text(f"콘텐츠 생성 실패: {e}")
        return

    await status_msg.delete()

    post_key = f"vid_{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "type": "video",
        "video_bytes": video_bytes,
        "frames": frames,
        "caption": content["caption"],
        "title": content["title"],
        "raw_output": content["raw"],
        "submitter": (msg.from_user.full_name if msg.from_user else '채널'),
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _approval_keyboard(post_key, False, is_video=True)
    submitter = msg.from_user.full_name if msg.from_user else '채널'
    preview = (
        f"🎬 *영상 콘텐츠 미리보기*\n"
        f"제출: {submitter} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"📌 {content['title']}"
    )
    await context.bot.send_video(
        chat_id=APPROVAL_CHAT_ID, video=video_bytes,
        caption=preview[:1024], parse_mode="Markdown", reply_markup=keyboard,
    )
    await context.bot.send_message(
        chat_id=APPROVAL_CHAT_ID,
        text=f"📝 *캡션 전문*\n\n{content['caption']}",
        parse_mode="Markdown",
    )
    if msg.chat_id != APPROVAL_CHAT_ID:
        await msg.reply_text("담당자에게 승인 요청을 보냈습니다. ✉️")


# ─── Multi Photo Processing ───────────────────────────────────────────────────

async def _process_group(gid: str, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(3)
    group = _pending_groups.pop(gid, None)
    if not group:
        return

    photos, msg, status_msg = group["photos"], group["msg"], group["status_msg"]
    n = len(photos)
    await status_msg.edit_text(f"사진 {n}장 분석 중... ⏳")

    try:
        content = generate_content_multi(photos)
    except Exception as e:
        await status_msg.edit_text(f"콘텐츠 생성 실패: {e}")
        return

    await status_msg.edit_text(f"카드 이미지 제작 중... 🎨 ({n}장)")

    card_images = []
    for i, photo in enumerate(photos):
        try:
            if i == 0:
                card_images.append(await render_card_image(photo, content["main_copy"], content["sub_copy"]))
            else:
                card_images.append(photo)
        except Exception as e:
            print(f"카드 렌더링 실패 ({i}): {e}")
            card_images.append(photo)

    await status_msg.delete()

    post_key = f"grp_{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "type": "multi",
        "card_images": card_images,
        "original_images": photos,
        "caption": content["caption"],
        "main_copy": content["main_copy"],
        "sub_copy": content["sub_copy"],
        "slide_order": content["slide_order"],
        "raw_output": content["raw"],
        "submitter": (msg.from_user.full_name if msg.from_user else '채널'),
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _approval_keyboard(post_key, True)
    preview = (
        f"🖼 *카루셀 미리보기* ({n}장)\n"
        f"제출: {(msg.from_user.full_name if msg.from_user else '채널')} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"📋 순서: {content['slide_order']}\n\n"
        f"📌 메인: *{content['main_copy']}*\n"
        f"💬 서브: _{content['sub_copy']}_"
    )
    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID, photo=card_images[0],
        caption=preview[:1024], parse_mode="Markdown", reply_markup=keyboard,
    )
    await context.bot.send_message(
        chat_id=APPROVAL_CHAT_ID,
        text=f"📝 *캡션 전문*\n\n{content['caption']}",
        parse_mode="Markdown",
    )
    if msg.chat_id != APPROVAL_CHAT_ID:
        await msg.reply_text(f"사진 {n}장 승인 요청을 보냈습니다. ✉️")


# ─── Telegram Handlers ─────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    # 일반 사진 또는 이미지 파일(document) 모두 처리
    if msg.photo:
        file = await context.bot.get_file(msg.photo[-1].file_id)
    elif msg.document and (msg.document.mime_type or "").startswith("image/"):
        file = await context.bot.get_file(msg.document.file_id)
    else:
        return

    photo_bytes = bytes(await file.download_as_bytearray())

    gid = msg.media_group_id
    if gid:
        if gid not in _pending_groups:
            status_msg = await msg.reply_text("사진 수집 중... 📥")
            _pending_groups[gid] = {"photos": [], "msg": msg, "status_msg": status_msg}
            asyncio.create_task(_process_group(gid, context))
        _pending_groups[gid]["photos"].append(photo_bytes)
    else:
        status_msg = await msg.reply_text("사진 분석 중... ⏳ (20~40초 소요)")
        await _process_single(msg, photo_bytes, context, status_msg)


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    if msg.video:
        file = await context.bot.get_file(msg.video.file_id)
    elif msg.document and (msg.document.mime_type or "").startswith("video/"):
        file = await context.bot.get_file(msg.document.file_id)
    else:
        return

    video_bytes = bytes(await file.download_as_bytearray())
    status_msg = await msg.reply_text("영상 분석 중... ⏳ (프레임 추출 + 캡션 생성, 20~40초 소요)")
    await _process_video(msg, video_bytes, context, status_msg)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("qconfirm_"):
        cancel_queue_item(data[9:])
        await query.edit_message_text("🗑 취소됐습니다. 이후 날짜가 앞당겨졌습니다.")
        return
    if data.startswith("qno_"):
        await query.edit_message_text("취소하지 않습니다.")
        return
    if data.startswith("qedit_"):
        item_id = data[6:]
        item = next((i for i in load_queue() if i["id"] == item_id), None)
        if not item:
            await query.edit_message_text("⚠️ 콘텐츠를 찾을 수 없습니다.")
            return
        qedit_data = {"queue_id": item_id, "raw": item["raw_output"]}
        context.bot_data[f"qedit_{query.from_user.id}"] = qedit_data
        context.bot_data[f"qedit_{query.message.chat_id}"] = qedit_data  # 채널 익명 포스팅 대응
        await query.message.reply_text(f"📝 현재 캡션:\n{item['caption']}\n\n어떤 부분을 수정할까요?")
        return
    if data.startswith("qcancel_"):
        item_id = data[8:]
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ 확인", callback_data=f"qconfirm_{item_id}"),
            InlineKeyboardButton("❌ 아니오", callback_data=f"qno_{item_id}"),
        ]])
        await query.message.reply_text("정말 취소할까요?", reply_markup=keyboard)
        return

    if data.startswith("approve_"):
        rest = data[8:]
        post_type, post_key = rest.split("_", 1)
        post = context.bot_data.get(post_key)
        if not post:
            await query.edit_message_caption("⚠️ 세션 만료.")
            return
        await query.edit_message_caption("큐에 추가 중... ⏳")
        try:
            item_id = str(uuid.uuid4())[:8]
            if post_type == "photo":
                media_path = save_media_to_queue(post["card_image"], item_id, "photo")
                scheduled = add_to_queue(item_id, "photo", media_path, post["caption"],
                                         post["main_copy"], post["sub_copy"], post["raw_output"])
            elif post_type == "carousel":
                paths = [save_media_to_queue(img, item_id, f"carousel_{i}")
                         for i, img in enumerate(post["card_images"])]
                scheduled = add_to_queue(item_id, "carousel", paths[0], post["caption"],
                                         post["main_copy"], post["sub_copy"], post["raw_output"],
                                         extra_media=paths[1:])
            elif post_type == "video":
                media_path = save_video_to_queue(post["video_bytes"], item_id)
                scheduled = add_to_queue(item_id, "video", media_path, post["caption"],
                                         post["title"], "", post["raw_output"])
            else:
                await query.edit_message_caption("❌ 지원하지 않는 타입입니다.")
                return
            day_ko = ["월","화","수","목","금","토","일"][datetime.strptime(scheduled, "%Y-%m-%d").weekday()]
            await query.edit_message_caption(
                f"✅ 큐에 추가됐습니다!\n\n"
                f"📅 {scheduled[:7].replace('-','/')}/{scheduled[8:]} ({day_ko}) {get_post_time(scheduled)}\n"
                f"📌 {post.get('main_copy') or post.get('title', '')}"
            )
        except Exception as e:
            await query.edit_message_caption(f"❌ 큐 추가 실패\n{e}")
        finally:
            context.bot_data.pop(post_key, None)
        return

    if data.startswith("edit_"):
        post_key = data[5:]
        post = context.bot_data.get(post_key)
        if not post:
            await query.edit_message_caption("⚠️ 세션 만료.")
            return
        if post.get("type") == "video":
            edit_data = {
                "post_key": post_key, "raw": post["raw_output"], "frames": post["frames"],
                "orig_msg_id": query.message.message_id, "orig_chat_id": query.message.chat_id,
            }
        else:
            img = post.get("original_image") or (post.get("original_images", [None])[0])
            edit_data = {
                "post_key": post_key, "raw": post["raw_output"], "image_bytes": img,
                "orig_msg_id": query.message.message_id, "orig_chat_id": query.message.chat_id,
            }
        context.bot_data[f"edit_{query.from_user.id}"] = edit_data
        context.bot_data[f"edit_{query.message.chat_id}"] = edit_data  # 채널 익명 포스팅 대응
        await query.message.reply_text("어떤 부분을 수정할까요?")
        return

    if data.startswith("reject_"):
        context.bot_data.pop(data[7:], None)
        await query.edit_message_caption("❌ 거절됐습니다.")
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return
    uid = msg.from_user.id if msg.from_user else msg.chat_id

    qedit = context.bot_data.get(f"qedit_{uid}")
    if qedit:
        context.bot_data.pop(f"qedit_{uid}")
        queue = load_queue()
        item = next((i for i in queue if i["id"] == qedit["queue_id"]), None)
        if not item:
            await msg.reply_text("⚠️ 콘텐츠를 찾을 수 없습니다.")
            return
        await msg.reply_text("수정 중... ⏳")
        try:
            if item["post_type"] == "video":
                frames = _extract_video_frames(Path(item["media_path"]).read_bytes())
                new = regenerate_video_caption(frames, qedit["raw"], msg.text)
                item.update({"caption": new["caption"], "main_copy": new["title"], "raw_output": new["raw"]})
                save_queue(queue)
                await msg.reply_text(
                    f"✅ 수정 완료. 예약일 {item['scheduled_date']} 유지.\n\n"
                    f"📌 {new['title']}\n\n{new['caption']}"
                )
            else:
                img_bytes = Path(item["media_path"]).read_bytes()
                new = regenerate_with_edit(img_bytes, qedit["raw"], msg.text)
                item.update({"caption": new["caption"], "main_copy": new["main_copy"],
                             "sub_copy": new["sub_copy"], "raw_output": new["raw"]})
                save_queue(queue)
                await msg.reply_text(
                    f"✅ 수정 완료. 예약일 {item['scheduled_date']} 유지.\n\n"
                    f"📌 {new['main_copy']}\n💬 {new['sub_copy']}\n\n{new['caption']}"
                )
        except Exception as e:
            await msg.reply_text(f"❌ 수정 실패: {e}")
        return

    edit_state = context.bot_data.get(f"edit_{uid}")
    if not edit_state:
        return
    context.bot_data.pop(f"edit_{uid}")
    post_key = edit_state["post_key"]
    post = context.bot_data.get(post_key)
    if not post:
        await msg.reply_text("⚠️ 세션 만료.")
        return
    await msg.reply_text("수정 중... ⏳")
    post_type = post.get("type")

    if post_type == "video":
        try:
            new = regenerate_video_caption(edit_state["frames"], edit_state["raw"], msg.text)
            post.update({"caption": new["caption"], "title": new["title"], "raw_output": new["raw"]})
            caption_preview = (
                f"🎬 *수정된 영상 미리보기*\n📌 {new['title']}\n\n📝 캡션:\n{new['caption'][:400]}..."
            )
            await context.bot.send_video(
                chat_id=APPROVAL_CHAT_ID, video=post["video_bytes"],
                caption=caption_preview[:1024], parse_mode="Markdown",
                reply_markup=_approval_keyboard(post_key, False, is_video=True),
            )
            orig_msg_id = edit_state.get("orig_msg_id")
            orig_chat_id = edit_state.get("orig_chat_id")
            if orig_msg_id and orig_chat_id:
                try:
                    await context.bot.edit_message_caption(
                        chat_id=orig_chat_id, message_id=orig_msg_id,
                        caption="✏️ *수정됨* — 아래 새 버전을 확인하세요.",
                        parse_mode="Markdown", reply_markup=None,
                    )
                except Exception:
                    pass
        except Exception as e:
            await msg.reply_text(f"❌ 수정 실패: {e}")
        return

    is_legacy_multi = post_type == "multi"   # 여러 장 업로드 카루셀 (구 방식, MULTI_BRAND_PROMPT)
    try:
        new = regenerate_with_edit(edit_state["image_bytes"], edit_state["raw"], msg.text, multi=is_legacy_multi)

        if is_legacy_multi:
            try:
                card_image = await render_card_image(edit_state["image_bytes"], new["main_copy"], new["sub_copy"])
            except Exception:
                card_image = edit_state["image_bytes"]
            post["card_images"][0] = card_image
            post.update({"card_image": card_image, "caption": new["caption"],
                         "main_copy": new["main_copy"], "sub_copy": new["sub_copy"], "raw_output": new["raw"]})
            preview_imgs = post["card_images"]
            is_carousel = True
            new["content_type"] = "멀티 카루셀"
        else:
            slides = new["slides"]
            is_carousel = new["format"] == "캐러셀" and len(slides) > 1
            n_cards = 2 if is_carousel else 1
            card_images = []
            for i in range(n_cards):
                slide = slides[i] if i < len(slides) else slides[0]
                try:
                    card_images.append(await render_card_image(
                        edit_state["image_bytes"], slide.get("main", ""), slide.get("sub", ""),
                        new["content_type"], new["text_position"], new.get("card_style", "bar"),
                    ))
                except Exception:
                    card_images.append(edit_state["image_bytes"])
            post.update({
                "type": "carousel" if is_carousel else "single",
                "card_image": card_images[0], "card_images": card_images,
                "caption": new["caption"], "main_copy": new["main_copy"], "sub_copy": new["sub_copy"],
                "content_type": new["content_type"], "raw_output": new["raw"],
            })
            preview_imgs = card_images

        caption = (
            f"📸 *수정된 미리보기*\n"
            f"🏷 유형: *{new['content_type']}* ({'캐러셀 2장' if is_carousel else '단일'})\n\n"
            f"📌 메인: *{new['main_copy']}*\n"
            f"💬 서브: _{new['sub_copy']}_\n\n"
            f"📝 캡션:\n{new['caption'][:400]}..."
        )
        await context.bot.send_photo(
            chat_id=APPROVAL_CHAT_ID, photo=preview_imgs[0],
            caption=caption, parse_mode="Markdown",
            reply_markup=_approval_keyboard(post_key, is_carousel),
        )
        if is_carousel and len(preview_imgs) > 1:
            await context.bot.send_photo(chat_id=APPROVAL_CHAT_ID, photo=preview_imgs[1], caption="2️⃣ 두 번째 슬라이드")
        # 원본 승인 메시지 버튼 비활성화 + 수정됨 표시
        orig_msg_id = edit_state.get("orig_msg_id")
        orig_chat_id = edit_state.get("orig_chat_id")
        if orig_msg_id and orig_chat_id:
            try:
                await context.bot.edit_message_caption(
                    chat_id=orig_chat_id, message_id=orig_msg_id,
                    caption="✏️ *수정됨* — 아래 새 버전을 확인하세요.",
                    parse_mode="Markdown", reply_markup=None,
                )
            except Exception:
                pass  # 이미 삭제됐거나 수정 불가한 경우 무시
    except Exception as e:
        await msg.reply_text(f"❌ 수정 실패: {e}")


async def handle_queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message or update.channel_post
    if not msg:
        return
    queue = sorted(load_queue(), key=lambda x: x["scheduled_date"])
    if not queue:
        await msg.reply_text("📋 예약된 콘텐츠가 없습니다.")
        return
    DAYS = ["월","화","수","목","금","토","일"]
    lines = ["📋 *예약 현황*\n─────────────"]
    rows = []
    for i, item in enumerate(queue, 1):
        d = datetime.strptime(item["scheduled_date"], "%Y-%m-%d")
        main = item["main_copy"][:25] + ("..." if len(item["main_copy"]) > 25 else "")
        lines.append(f"{i}️⃣ {d.month}/{d.day} ({DAYS[d.weekday()]}) {get_post_time(item['scheduled_date'])}\n   \"{main}\"")
        rows.append([
            InlineKeyboardButton("수정", callback_data=f"qedit_{item['id']}"),
            InlineKeyboardButton("취소", callback_data=f"qcancel_{item['id']}"),
        ])
    lines.append(f"─────────────\n총 {len(queue)}개 예약됨")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("ZZL Instagram Bot 시작 (Make 웹훅 방식)")
    app = Application.builder().token(BOT_TOKEN).build()
    # PTB v20+ run_daily의 days는 0=일요일~6=토요일 (월=0 관례 아님, datetime.weekday()와 다름)
    # 평일(월~금) 12:00 KST = 03:00 UTC
    app.job_queue.run_daily(scheduled_post_job, time=dtime(3, 0, 0), days=(1,2,3,4,5), name="weekday_post")
    # 주말(토~일) 21:00 KST = 12:00 UTC
    app.job_queue.run_daily(scheduled_post_job, time=dtime(12, 0, 0), days=(6,0), name="weekend_post")
    app.add_handler(CommandHandler("queue", handle_queue_command))
    app.add_handler(MessageHandler(  # 채널에서 /queue 처리
        filters.UpdateType.CHANNEL_POST & filters.Regex(r"^/queue"),
        handle_queue_command,
    ))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot 시작 (Ctrl+C로 종료)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
