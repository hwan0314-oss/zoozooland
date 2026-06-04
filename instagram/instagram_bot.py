import asyncio
import base64
import io
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone, timedelta, time as dtime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import anthropic
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
from PIL import Image, ImageDraw, ImageFont
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

BOT_TOKEN         = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
IG_USERNAME       = os.environ["INSTAGRAM_USERNAME"]
IG_PASSWORD       = os.environ["INSTAGRAM_PASSWORD"]
APPROVAL_CHAT_ID  = int(os.environ.get("APPROVAL_CHAT_ID", "-1003990713280"))

SESSION_FILE    = Path(__file__).parent / "ig_session.json"
QUEUE_FILE      = Path(__file__).parent / "queue.json"
QUEUE_MEDIA_DIR = Path(__file__).parent / "queue_media"
QUEUE_MEDIA_DIR.mkdir(exist_ok=True)

KST = timezone(timedelta(hours=9))

# ─── Prompts ──────────────────────────────────────────────────────────────────

BRAND_PROMPT = """\
너는 ZZL(쥬쥬랜드) 인스타그램 카드뉴스 카피라이터야.

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

## 카드 구성 (사진 1장)

**메인 카피 (카드에 삽입)**
- 2줄 이내, 짧고 임팩트 있게
- 유머와 감성 사이 어딘가
- 예: "매일 싸움. 매일 이럼"

**서브 카피 (카드에 삽입)**
- 영문, 이탤릭 감성
- 메인을 받쳐주는 한 줄
- 예: "that's why they call it lovebird"

## 캡션 구성 (인스타 본문)
다음 구조로 작성:

1. [팩트] 해당 동물의 실제 습성/행동
   (출처 없는 인용, 수치, 연구결과 사용 금지 — 관찰 가능한 사실만)
2. [연결] 그 행동을 인간관계·감정·일상으로 자연스럽게 전환
3. [공감] 독자가 "이거 내 얘기잖아" 느끼는 구간
4. [명언] 대구 구조의 여운 있는 한 줄 (저장·공유 유발)
5. [행동 조언] 독자에게 건네는 따뜻한 한 줄 행동 유도
6. [ZZL 연결] 쥬쥬랜드 방문 유도 1~2줄
7. [해시태그] #ZZL #쥬쥬랜드 #ZZLstagram #동물이말하는우리얘기 + 동물명 + 관련 감성 태그

## 시점 & 금지사항
- 시점: ZZL이 동물을 관찰하다 발견한 인간 이야기 (브랜드 관찰자)
- 1인칭(나는, 내가) 사용 금지
- 출처 없는 전문가 인용 금지
- 동물 설명 나열식 금지
- 과한 이모지 금지 (1~2개 이내)

## 출력 형식
사진을 받으면 아래 순서로 반드시 이 형식 그대로 출력:

[사진 분석]
- 동물 종류, 행동, 분위기, 카피 연결 포인트

[카드 메인 카피]
(내용)

[카드 서브 카피]
(내용)

[캡션 전문]
(내용)\
"""

MULTI_BRAND_PROMPT = """\
너는 ZZL(쥬쥬랜드) 인스타그램 카드뉴스 카피라이터야.
위 사진들은 카루셀/슬라이드쇼로 게시될 여러 장의 사진이야.

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

# 미디어 그룹 수집용 임시 저장소
_pending_groups: dict = {}


# ─── Queue Management ─────────────────────────────────────────────────────────

def load_queue() -> list:
    if not QUEUE_FILE.exists():
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue(queue: list):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def get_next_available_date() -> str:
    now = datetime.now(KST)
    today = now.date()
    if now.hour < 7 or (now.hour == 7 and now.minute < 30):
        candidate = today
    else:
        candidate = today + timedelta(days=1)
    scheduled = {item["scheduled_date"] for item in load_queue()}
    while candidate.isoformat() in scheduled:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def add_to_queue(post_type: str, media_path: str, caption: str,
                 main_copy: str, sub_copy: str, raw_output: str,
                 extra_media: list = None) -> tuple[str, str]:
    item_id = str(uuid.uuid4())[:8]
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
    return item_id, scheduled_date


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
    for path in [item.get("media_path")] + (item.get("extra_media") or []):
        if path and os.path.exists(path):
            os.unlink(path)


def save_media_to_queue(image_bytes: bytes, item_id: str, suffix: str = "photo") -> str:
    path = QUEUE_MEDIA_DIR / f"{item_id}_{suffix}.jpg"
    path.write_bytes(image_bytes)
    return str(path)


def save_video_to_queue(video_path: str, item_id: str) -> str:
    dest = QUEUE_MEDIA_DIR / f"{item_id}_video.mp4"
    import shutil
    shutil.move(video_path, dest)
    return str(dest)


# ─── Instagram Client ──────────────────────────────────────────────────────────

_ig_client: Client | None = None


def challenge_code_handler(username, choice):
    method = "SMS" if choice == 1 else "이메일"
    print(f"\n⚠️  Instagram 인증 필요! 계정: {username}, 방법: {method}")
    return input("인증 코드: ").strip()


def get_ig_client() -> Client:
    global _ig_client
    if _ig_client is not None:
        return _ig_client
    cl = Client()
    cl.delay_range = [2, 5]
    cl.challenge_code_handler = challenge_code_handler
    if SESSION_FILE.exists():
        cl.load_settings(str(SESSION_FILE))
    cl.login(IG_USERNAME, IG_PASSWORD)
    cl.dump_settings(str(SESSION_FILE))
    _ig_client = cl
    return cl


def _ig_call(func):
    try:
        return func()
    except (LoginRequired, ChallengeRequired):
        global _ig_client
        _ig_client = None
        return func()


def post_photo(image_path: str, caption: str) -> str:
    media = _ig_call(lambda: get_ig_client().photo_upload(image_path, caption))
    return str(media.pk)


def post_carousel(image_paths: list, caption: str) -> str:
    media = _ig_call(lambda: get_ig_client().album_upload(image_paths, caption))
    return str(media.pk)


def post_reel(video_path: str, caption: str) -> str:
    media = _ig_call(lambda: get_ig_client().clip_upload(video_path, caption))
    return str(media.pk)


# ─── Image & Video Processing ─────────────────────────────────────────────────

def add_watermark(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    text = "🌿 ZZL"
    font_size = max(img.width // 22, 20)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = img.width - tw - 24, img.height - th - 24
    draw.rectangle([x-8, y-6, x+tw+8, y+th+6], fill=(0, 0, 0, 130))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 230))
    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def create_ken_burns_video(image_bytes: bytes, duration: int = 6) -> str:
    fd_in, in_path = tempfile.mkstemp(suffix=".jpg")
    fd_out, out_path = tempfile.mkstemp(suffix=".mp4")
    os.write(fd_in, image_bytes); os.close(fd_in); os.close(fd_out)
    frames = duration * 25
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", in_path,
        "-vf", (
            "scale=1080:1080:force_original_aspect_ratio=decrease,"
            "pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"zoompan=z='min(zoom+0.0008,1.25)':d={frames}:"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1080,fps=25"
        ),
        "-c:v", "libx264", "-preset", "fast",
        "-t", str(duration), "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    os.unlink(in_path)
    if r.returncode != 0:
        os.unlink(out_path)
        raise RuntimeError(r.stderr.decode()[-300:])
    return out_path


def create_slideshow_video(images: list[bytes], per_slide: int = 4) -> str:
    clip_paths = []
    fd_out, out_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd_out)
    try:
        for img in images:
            clip_paths.append(create_ken_burns_video(img, duration=per_slide))
        fd_list, list_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd_list, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path,
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        os.unlink(list_path)
        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode()[-300:])
        return out_path
    except Exception:
        if os.path.exists(out_path): os.unlink(out_path)
        raise
    finally:
        for p in clip_paths:
            if os.path.exists(p): os.unlink(p)


# ─── Claude API ────────────────────────────────────────────────────────────────

def _parse_content(raw: str) -> dict:
    sections = {}
    current = None
    lines = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current:
                sections[current] = "\n".join(lines).strip()
            current = stripped[1:-1]
            lines = []
        else:
            lines.append(line)
    if current:
        sections[current] = "\n".join(lines).strip()
    return {
        "analysis":   sections.get("사진 분석", ""),
        "main_copy":  sections.get("카드 메인 카피", ""),
        "sub_copy":   sections.get("카드 서브 카피", ""),
        "caption":    sections.get("캡션 전문", ""),
        "slide_order": sections.get("슬라이드 순서", ""),
        "raw": raw,
    }


def generate_content(image_bytes: bytes) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1000,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": BRAND_PROMPT},
        ]}],
    )
    return _parse_content(resp.content[0].text.strip())


def generate_content_multi(images: list[bytes]) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    parts = []
    for img in images[:10]:
        b64 = base64.b64encode(img).decode()
        parts.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    parts.append({"type": "text", "text": f"총 {len(images)}장입니다.\n\n{MULTI_BRAND_PROMPT}"})
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1000,
        messages=[{"role": "user", "content": parts}],
    )
    return _parse_content(resp.content[0].text.strip())


def regenerate_with_edit(image_bytes: bytes, original_raw: str, edit_request: str) -> dict:
    """수정 요청 반영해서 콘텐츠 재생성."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1000,
        messages=[
            {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": BRAND_PROMPT},
            ]},
            {"role": "assistant", "content": original_raw},
            {"role": "user", "content": f"수정 요청: {edit_request}\n\n위 내용을 수정해주세요. 출력 형식은 그대로 유지해주세요."},
        ],
    )
    return _parse_content(resp.content[0].text.strip())


# ─── Scheduled Posting (07:30 KST = 22:30 UTC) ────────────────────────────────

async def scheduled_post_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(KST).date().isoformat()
    queue = load_queue()
    for item in queue:
        if item["scheduled_date"] != today:
            continue
        try:
            pk = None
            if item["post_type"] == "photo":
                pk = post_photo(item["media_path"], item["caption"])
            elif item["post_type"] == "reel":
                pk = post_reel(item["media_path"], item["caption"])
            elif item["post_type"] == "carousel":
                paths = [item["media_path"]] + item.get("extra_media", [])
                pk = post_carousel(paths, item["caption"])

            await context.bot.send_message(
                chat_id=APPROVAL_CHAT_ID,
                text=(
                    f"✅ 예약 포스팅 완료!\n"
                    f"📅 {today} 07:30\n"
                    f"📝 {item['main_copy']}\n"
                    f"Post ID: {pk}"
                ),
            )
            new_queue = [i for i in load_queue() if i["id"] != item["id"]]
            save_queue(new_queue)
        except Exception as e:
            await context.bot.send_message(
                chat_id=APPROVAL_CHAT_ID,
                text=f"❌ 예약 포스팅 실패 ({today})\n{e}",
            )
        break


# ─── Approval Keyboard ────────────────────────────────────────────────────────

def _approval_keyboard(post_key: str, has_video: bool, is_multi: bool) -> InlineKeyboardMarkup:
    if is_multi:
        rows = [
            [
                InlineKeyboardButton("✅ 카루셀 승인",    callback_data=f"approve_carousel_{post_key}"),
                InlineKeyboardButton("✅ 슬라이드쇼 승인", callback_data=f"approve_reel_{post_key}"),
            ],
            [
                InlineKeyboardButton("✏️ 수정", callback_data=f"edit_{post_key}"),
                InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}"),
            ],
        ]
    elif has_video:
        rows = [
            [
                InlineKeyboardButton("✅ 사진 승인", callback_data=f"approve_photo_{post_key}"),
                InlineKeyboardButton("✅ 릴스 승인", callback_data=f"approve_reel_{post_key}"),
            ],
            [
                InlineKeyboardButton("✏️ 수정", callback_data=f"edit_{post_key}"),
                InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}"),
            ],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("✅ 승인", callback_data=f"approve_photo_{post_key}"),
                InlineKeyboardButton("✏️ 수정", callback_data=f"edit_{post_key}"),
                InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}"),
            ],
        ]
    return InlineKeyboardMarkup(rows)


def _cleanup_temp(post: dict):
    if post.get("video_path") and os.path.exists(post.get("video_path", "")):
        os.unlink(post["video_path"])


# ─── Single Photo Processing ──────────────────────────────────────────────────

async def _process_single(msg, image_bytes: bytes, context: ContextTypes.DEFAULT_TYPE, status_msg):
    try:
        content = generate_content(image_bytes)
    except Exception as e:
        await status_msg.edit_text(f"콘텐츠 생성 실패: {e}")
        return

    await status_msg.edit_text("워터마크 추가 + 영상 생성 중... 🎬")

    try:
        watermarked = add_watermark(image_bytes)
    except Exception:
        watermarked = image_bytes

    video_path = None
    try:
        video_path = create_ken_burns_video(watermarked)
    except Exception as e:
        print(f"영상 생성 실패: {e}")

    await status_msg.delete()

    post_key = f"{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "type": "single",
        "image_bytes": watermarked,
        "original_image_bytes": image_bytes,
        "video_path": video_path,
        "caption": content["caption"],
        "main_copy": content["main_copy"],
        "sub_copy": content["sub_copy"],
        "raw_output": content["raw"],
        "submitter": msg.from_user.full_name,
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _approval_keyboard(post_key, bool(video_path), False)
    preview = (
        f"📸 *콘텐츠 미리보기*\n"
        f"제출: {msg.from_user.full_name} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"🔍 {content['analysis']}\n\n"
        f"📌 메인: *{content['main_copy']}*\n"
        f"💬 서브: _{content['sub_copy']}_\n\n"
        f"📝 캡션:\n{content['caption'][:300]}..."
    )
    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID, photo=watermarked,
        caption=preview[:1024], parse_mode="Markdown", reply_markup=keyboard,
    )
    if video_path:
        try:
            with open(video_path, "rb") as vf:
                await context.bot.send_video(
                    chat_id=APPROVAL_CHAT_ID, video=vf,
                    caption="🎬 릴스 미리보기 (Ken Burns)", width=1080, height=1080,
                )
        except Exception as e:
            print(f"영상 미리보기 전송 실패: {e}")

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

    await status_msg.edit_text(f"워터마크 + 슬라이드쇼 생성 중... 🎬")

    watermarked = []
    for p in photos:
        try:
            watermarked.append(add_watermark(p))
        except Exception:
            watermarked.append(p)

    video_path = None
    try:
        video_path = create_slideshow_video(watermarked)
    except Exception as e:
        print(f"슬라이드쇼 생성 실패: {e}")

    await status_msg.delete()

    post_key = f"grp_{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "type": "multi",
        "images": watermarked,
        "original_images": photos,
        "video_path": video_path,
        "caption": content["caption"],
        "main_copy": content["main_copy"],
        "sub_copy": content["sub_copy"],
        "raw_output": content["raw"],
        "submitter": msg.from_user.full_name,
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _approval_keyboard(post_key, bool(video_path), True)
    preview = (
        f"🖼 *카루셀 미리보기* ({n}장)\n"
        f"제출: {msg.from_user.full_name} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"📋 순서: {content['slide_order']}\n\n"
        f"📌 메인: *{content['main_copy']}*\n"
        f"💬 서브: _{content['sub_copy']}_\n\n"
        f"📝 캡션:\n{content['caption'][:300]}..."
    )
    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID, photo=watermarked[0],
        caption=preview[:1024], parse_mode="Markdown", reply_markup=keyboard,
    )
    if video_path:
        try:
            with open(video_path, "rb") as vf:
                await context.bot.send_video(
                    chat_id=APPROVAL_CHAT_ID, video=vf,
                    caption=f"🎬 슬라이드쇼 미리보기 ({n}장)", width=1080, height=1080,
                )
        except Exception as e:
            print(f"미리보기 전송 실패: {e}")

    if msg.chat_id != APPROVAL_CHAT_ID:
        await msg.reply_text(f"사진 {n}장 승인 요청을 보냈습니다. ✉️")


# ─── Telegram Handlers ─────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    photo_file = await (await context.bot.get_file(msg.photo[-1].file_id)).download_as_bytearray()
    image_bytes = bytes(photo_file)

    gid = msg.media_group_id
    if gid:
        if gid not in _pending_groups:
            status_msg = await msg.reply_text("사진 수집 중... 📥")
            _pending_groups[gid] = {"photos": [], "msg": msg, "status_msg": status_msg}
            asyncio.create_task(_process_group(gid, context))
        _pending_groups[gid]["photos"].append(image_bytes)
    else:
        status_msg = await msg.reply_text("사진 분석 중... ⏳ (15~30초 소요)")
        await _process_single(msg, image_bytes, context, status_msg)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # ── 큐 취소 확인 ──
    if data.startswith("qconfirm_"):
        item_id = data[9:]
        cancel_queue_item(item_id)
        await query.edit_message_text("🗑 취소됐습니다. 이후 콘텐츠 날짜가 하루씩 앞당겨졌습니다.")
        return

    if data.startswith("qno_"):
        await query.edit_message_text("취소를 유지합니다.")
        return

    # ── 큐 수정 ──
    if data.startswith("qedit_"):
        item_id = data[6:]
        queue = load_queue()
        item = next((i for i in queue if i["id"] == item_id), None)
        if not item:
            await query.edit_message_text("⚠️ 해당 콘텐츠를 찾을 수 없습니다.")
            return
        uid = query.from_user.id
        context.bot_data[f"qedit_{uid}"] = {"queue_id": item_id, "raw": item["raw_output"]}
        await query.message.reply_text(
            f"📝 현재 캡션:\n{item['caption']}\n\n어떤 부분을 수정할까요?",
        )
        return

    # ── 큐 취소 클릭 ──
    if data.startswith("qcancel_"):
        item_id = data[8:]
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ 확인", callback_data=f"qconfirm_{item_id}"),
            InlineKeyboardButton("❌ 아니오", callback_data=f"qno_{item_id}"),
        ]])
        await query.message.reply_text("정말 취소할까요?", reply_markup=keyboard)
        return

    # ── 승인 ──
    if data.startswith("approve_"):
        rest = data[8:]  # "photo_KEY" or "reel_KEY" or "carousel_KEY"
        parts = rest.split("_", 1)
        post_type, post_key = parts[0], parts[1]
        post = context.bot_data.get(post_key)
        if not post:
            await query.edit_message_caption("⚠️ 세션 만료.")
            return

        await query.edit_message_caption("큐에 추가 중... ⏳")
        try:
            item_id = str(uuid.uuid4())[:8]

            if post_type == "photo":
                media_path = save_media_to_queue(post["image_bytes"], item_id, "photo")
                _, scheduled = add_to_queue("photo", media_path, post["caption"],
                                            post["main_copy"], post["sub_copy"], post["raw_output"])
            elif post_type == "reel" and post.get("video_path"):
                media_path = save_video_to_queue(post["video_path"], item_id)
                post["video_path"] = None  # 이동됐으므로 cleanup 스킵
                _, scheduled = add_to_queue("reel", media_path, post["caption"],
                                            post["main_copy"], post["sub_copy"], post["raw_output"])
            elif post_type == "carousel" and post.get("type") == "multi":
                paths = []
                for i, img in enumerate(post["images"]):
                    p = save_media_to_queue(img, item_id, f"carousel_{i}")
                    paths.append(p)
                _, scheduled = add_to_queue("carousel", paths[0], post["caption"],
                                            post["main_copy"], post["sub_copy"], post["raw_output"],
                                            extra_media=paths[1:])
            else:
                await query.edit_message_caption("❌ 지원하지 않는 포스팅 타입입니다.")
                return

            day_ko = ["월","화","수","목","금","토","일"][datetime.strptime(scheduled, "%Y-%m-%d").weekday()]
            await query.edit_message_caption(
                f"✅ 큐에 추가됐습니다!\n\n"
                f"📅 예약일: {scheduled[:7].replace('-','/')}/{scheduled[8:]} ({day_ko}) 07:30\n"
                f"📌 {post['main_copy']}"
            )
        except Exception as e:
            await query.edit_message_caption(f"❌ 큐 추가 실패\n{e}")
        finally:
            _cleanup_temp(post)
            context.bot_data.pop(post_key, None)
        return

    # ── 수정 ──
    if data.startswith("edit_"):
        post_key = data[5:]
        post = context.bot_data.get(post_key)
        if not post:
            await query.edit_message_caption("⚠️ 세션 만료.")
            return
        uid = query.from_user.id
        img = post.get("image_bytes") or (post.get("images", [None])[0])
        context.bot_data[f"edit_{uid}"] = {
            "post_key": post_key,
            "raw": post["raw_output"],
            "image_bytes": img,
        }
        await query.message.reply_text("어떤 부분을 수정할까요?")
        return

    # ── 거절 ──
    if data.startswith("reject_"):
        post_key = data[7:]
        post = context.bot_data.get(post_key)
        if post:
            _cleanup_temp(post)
            context.bot_data.pop(post_key, None)
        await query.edit_message_caption("❌ 거절됐습니다.")
        return


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    uid = msg.from_user.id if msg.from_user else None
    if not uid:
        return

    # ── 큐 수정 모드 ──
    qedit_state = context.bot_data.get(f"qedit_{uid}")
    if qedit_state:
        context.bot_data.pop(f"qedit_{uid}", None)
        queue = load_queue()
        item = next((i for i in queue if i["id"] == qedit_state["queue_id"]), None)
        if not item:
            await msg.reply_text("⚠️ 해당 콘텐츠를 찾을 수 없습니다.")
            return
        await msg.reply_text("수정 중... ⏳")
        try:
            img_bytes = Path(item["media_path"]).read_bytes()
            new_content = regenerate_with_edit(img_bytes, qedit_state["raw"], msg.text)
            item["caption"] = new_content["caption"]
            item["main_copy"] = new_content["main_copy"]
            item["sub_copy"] = new_content["sub_copy"]
            item["raw_output"] = new_content["raw"]
            save_queue(queue)
            await msg.reply_text(
                f"✅ 수정됐습니다. 예약 날짜({item['scheduled_date']}) 유지.\n\n"
                f"📌 메인: {new_content['main_copy']}\n"
                f"💬 서브: {new_content['sub_copy']}\n\n"
                f"📝 캡션:\n{new_content['caption']}"
            )
        except Exception as e:
            await msg.reply_text(f"❌ 수정 실패: {e}")
        return

    # ── 승인 전 수정 모드 ──
    edit_state = context.bot_data.get(f"edit_{uid}")
    if not edit_state:
        return

    context.bot_data.pop(f"edit_{uid}", None)
    post_key = edit_state["post_key"]
    post = context.bot_data.get(post_key)
    if not post:
        await msg.reply_text("⚠️ 세션 만료.")
        return

    await msg.reply_text("수정 중... ⏳")
    try:
        new_content = regenerate_with_edit(edit_state["image_bytes"], edit_state["raw"], msg.text)
        post["caption"] = new_content["caption"]
        post["main_copy"] = new_content["main_copy"]
        post["sub_copy"] = new_content["sub_copy"]
        post["raw_output"] = new_content["raw"]

        is_multi = post.get("type") == "multi"
        keyboard = _approval_keyboard(post_key, bool(post.get("video_path")), is_multi)
        first_img = post["images"][0] if is_multi else post["image_bytes"]

        await context.bot.send_photo(
            chat_id=APPROVAL_CHAT_ID, photo=first_img,
            caption=(
                f"📸 *수정된 미리보기*\n\n"
                f"📌 메인: *{new_content['main_copy']}*\n"
                f"💬 서브: _{new_content['sub_copy']}_\n\n"
                f"📝 캡션:\n{new_content['caption'][:400]}..."
            ),
            parse_mode="Markdown", reply_markup=keyboard,
        )
    except Exception as e:
        await msg.reply_text(f"❌ 수정 실패: {e}")


async def handle_queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    if not msg:
        return

    queue = sorted(load_queue(), key=lambda x: x["scheduled_date"])
    if not queue:
        await msg.reply_text("📋 예약된 콘텐츠가 없습니다.")
        return

    DAYS = ["월","화","수","목","금","토","일"]
    lines = ["📋 *예약 현황*\n─────────────"]
    keyboard_rows = []

    for i, item in enumerate(queue, 1):
        d = datetime.strptime(item["scheduled_date"], "%Y-%m-%d")
        day = DAYS[d.weekday()]
        main = item["main_copy"][:25] + ("..." if len(item["main_copy"]) > 25 else "")
        lines.append(f"{i}️⃣ {d.month}/{d.day} ({day}) 07:30\n   \"{main}\"")
        keyboard_rows.append([
            InlineKeyboardButton("수정", callback_data=f"qedit_{item['id']}"),
            InlineKeyboardButton("취소", callback_data=f"qcancel_{item['id']}"),
        ])

    lines.append(f"─────────────\n총 {len(queue)}개 예약됨")

    await msg.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
    )


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("Instagram 로그인 중...")
    try:
        get_ig_client()
        print(f"로그인 완료: @{IG_USERNAME}")
    except Exception as e:
        print(f"로그인 실패: {e}")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # 07:30 KST = 22:30 UTC 매일 자동 포스팅
    app.job_queue.run_daily(
        scheduled_post_job,
        time=dtime(22, 30, 0),
        name="daily_post",
    )

    app.add_handler(CommandHandler("queue", handle_queue_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot 시작 (Ctrl+C로 종료)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
