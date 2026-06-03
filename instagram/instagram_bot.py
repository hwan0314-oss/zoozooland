import asyncio
import base64
import io
import os
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
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

SESSION_FILE = Path(__file__).parent / "ig_session.json"
KST = timezone(timedelta(hours=9))

SINGLE_PROMPT = """\
당신은 쥬쥬랜드(ZooZoo Land) 인스타그램 SNS 전략가입니다.

브랜드:
- 어린이·가족 동물원 테마파크 (경기도 고양시)
- 타겟: 가족, 특히 영유아 자녀를 둔 부모
- 톤: 활기차고 따뜻하며 감성적

현재 인스타그램 트렌드 반영:
- 짧은 감성 카피 + 스토리텔링이 도달률 높음
- 동물 콘텐츠는 힐링/치유 감성으로 접근할 때 저장수 폭발
- 가족 나들이 콘텐츠: 주말 계획 자극
- 해시태그는 대형+틈새 태그 혼합이 효과적

사진을 보고 아래 형식으로 작성하세요:

[콘텐츠 전략]
이 사진을 어떤 각도로 접근할지 한 줄로.

[캡션]
(임팩트 첫 줄, 15자 이내) ✨

(스토리텔링 본문 2~3줄, 감성적으로)

#ZZL #쥬쥬랜드 (관련 해시태그 7~10개, 대형+틈새 혼합)

[포스팅 추천 시간]
최적 시간대 한 줄.

한국어로 작성하세요.\
"""

MULTI_PROMPT = """\
당신은 쥬쥬랜드(ZooZoo Land) 인스타그램 SNS 전략가입니다.

브랜드:
- 어린이·가족 동물원 테마파크 (경기도 고양시)
- 타겟: 가족, 특히 영유아 자녀를 둔 부모
- 톤: 활기차고 따뜻하며 감성적

위 사진들을 보고 스토리라인이 있는 카루셀/슬라이드쇼 콘텐츠를 기획하세요.
사진들의 연결성과 흐름을 파악해서 하나의 이야기로 만들어주세요.

[콘텐츠 전략]
이 사진들을 어떤 스토리로 연결할지 한 줄로.

[슬라이드 순서]
사진을 어떤 순서로 배치할지 (1번부터 번호로 설명)

[캡션]
(임팩트 첫 줄, 15자 이내) ✨

(스토리텔링 본문 3~4줄, 감성적으로, 카루셀 유도 문구 포함)

#ZZL #쥬쥬랜드 (관련 해시태그 7~10개)

[포스팅 추천 시간]
최적 시간대 한 줄.

한국어로 작성하세요.\
"""

# 미디어 그룹 수집용 임시 저장소
_pending_groups: dict = {}


# ─── Instagram Client ──────────────────────────────────────────────────────────

_ig_client: Client | None = None


def challenge_code_handler(username, choice):
    print(f"\n⚠️  Instagram 인증 필요! 계정: {username}")
    print(f"인증 방법: {'SMS' if choice == 1 else '이메일'}")
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


def _ig_upload(func, *args):
    """로그인 만료 시 재시도."""
    try:
        return func(*args)
    except (LoginRequired, ChallengeRequired):
        global _ig_client
        _ig_client = None
        return func(*args)


def post_photo_to_instagram(image_bytes: bytes, caption: str) -> str:
    fd, tmp = tempfile.mkstemp(suffix=".jpg")
    try:
        os.write(fd, image_bytes); os.close(fd)
        media = _ig_upload(lambda: get_ig_client().photo_upload(tmp, caption))
        return str(media.pk)
    finally:
        os.unlink(tmp)


def post_carousel_to_instagram(images: list[bytes], caption: str) -> str:
    paths = []
    try:
        for img in images:
            fd, p = tempfile.mkstemp(suffix=".jpg")
            os.write(fd, img); os.close(fd)
            paths.append(p)
        media = _ig_upload(lambda: get_ig_client().album_upload(paths, caption))
        return str(media.pk)
    finally:
        for p in paths:
            if os.path.exists(p): os.unlink(p)


def post_reel_to_instagram(video_path: str, caption: str) -> str:
    media = _ig_upload(lambda: get_ig_client().clip_upload(video_path, caption))
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
    """단일 사진 Ken Burns 릴스. 임시 파일 경로 반환."""
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
    """여러 사진 슬라이드쇼 릴스 (사진마다 Ken Burns + 페이드). 임시 파일 경로 반환."""
    clip_paths = []
    fd_out, out_path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd_out)

    try:
        # 각 사진을 개별 클립으로 생성
        for img in images:
            clip = create_ken_burns_video(img, duration=per_slide)
            clip_paths.append(clip)

        # concat 리스트 파일 생성
        fd_list, list_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd_list, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")

        # 클립들을 하나로 합치기
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path,
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", out_path,
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        os.unlink(list_path)

        if r.returncode != 0:
            raise RuntimeError(r.stderr.decode()[-300:])

        return out_path

    except Exception:
        if os.path.exists(out_path):
            os.unlink(out_path)
        raise
    finally:
        for p in clip_paths:
            if os.path.exists(p): os.unlink(p)


# ─── Claude Vision ─────────────────────────────────────────────────────────────

def _parse_content(raw: str) -> dict:
    caption = raw
    if "[캡션]" in raw:
        cap_raw = raw.split("[캡션]")[1]
        if "[포스팅 추천 시간]" in cap_raw:
            cap_raw = cap_raw.split("[포스팅 추천 시간]")[0]
        caption = cap_raw.strip()
    strategy = raw.split("[콘텐츠 전략]")[1].split("[캡션]")[0].strip() if "[콘텐츠 전략]" in raw else ""
    post_time = raw.split("[포스팅 추천 시간]")[1].strip() if "[포스팅 추천 시간]" in raw else ""
    slide_order = raw.split("[슬라이드 순서]")[1].split("[캡션]")[0].strip() if "[슬라이드 순서]" in raw else ""
    return {"caption": caption, "strategy": strategy, "post_time": post_time, "slide_order": slide_order}


def generate_content(image_bytes: bytes) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=800,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": SINGLE_PROMPT},
        ]}],
    )
    return _parse_content(resp.content[0].text.strip())


def generate_content_multi(images: list[bytes]) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    content_parts = []
    for img in images[:10]:
        b64 = base64.b64encode(img).decode()
        content_parts.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    content_parts.append({"type": "text", "text": f"총 {len(images)}장의 사진입니다.\n\n{MULTI_PROMPT}"})
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1000,
        messages=[{"role": "user", "content": content_parts}],
    )
    return _parse_content(resp.content[0].text.strip())


# ─── Post Data Helpers ────────────────────────────────────────────────────────

def _make_approval_keyboard(post_key: str, has_video: bool, is_multi: bool) -> InlineKeyboardMarkup:
    if is_multi:
        rows = [
            [
                InlineKeyboardButton("🖼 카루셀 포스팅",   callback_data=f"carousel_{post_key}"),
                InlineKeyboardButton("🎬 슬라이드쇼 릴스", callback_data=f"reel_{post_key}"),
            ],
            [
                InlineKeyboardButton("✏️ 캡션 수정", callback_data=f"edit_{post_key}"),
                InlineKeyboardButton("❌ 거절",      callback_data=f"reject_{post_key}"),
            ],
        ]
    elif has_video:
        rows = [
            [
                InlineKeyboardButton("🖼 사진 포스팅", callback_data=f"photo_{post_key}"),
                InlineKeyboardButton("🎬 릴스 포스팅", callback_data=f"reel_{post_key}"),
            ],
            [
                InlineKeyboardButton("✏️ 캡션 수정", callback_data=f"edit_{post_key}"),
                InlineKeyboardButton("❌ 거절",      callback_data=f"reject_{post_key}"),
            ],
        ]
    else:
        rows = [
            [
                InlineKeyboardButton("🖼 사진 포스팅", callback_data=f"photo_{post_key}"),
                InlineKeyboardButton("✏️ 캡션 수정",  callback_data=f"edit_{post_key}"),
            ],
            [InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}")],
        ]
    return InlineKeyboardMarkup(rows)


def _cleanup_post(post: dict):
    if post.get("video_path") and os.path.exists(post["video_path"]):
        os.unlink(post["video_path"])


# ─── Single Photo Processing ──────────────────────────────────────────────────

async def _process_single(msg, image_bytes: bytes, context: ContextTypes.DEFAULT_TYPE, status_msg=None):
    if status_msg is None:
        status_msg = await msg.reply_text("사진 분석 중... ⏳ (15~30초 소요)")

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
        "video_path": video_path,
        "caption": content["caption"],
        "strategy": content["strategy"],
        "submitter": msg.from_user.full_name,
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _make_approval_keyboard(post_key, bool(video_path), False)
    preview = (
        f"📸 *인스타그램 게시물 미리보기*\n"
        f"제출: {msg.from_user.full_name} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"💡 전략: {content['strategy']}\n\n"
        f"📝 캡션:\n{content['caption']}\n\n"
        f"⏰ {content['post_time']}"
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
                    caption="🎬 릴스 미리보기", width=1080, height=1080,
                )
        except Exception as e:
            print(f"영상 미리보기 전송 실패: {e}")

    if msg.chat_id != APPROVAL_CHAT_ID:
        await msg.reply_text("담당자에게 승인 요청을 보냈습니다. ✉️")


# ─── Multi Photo Processing ───────────────────────────────────────────────────

async def _process_group(gid: str, context: ContextTypes.DEFAULT_TYPE):
    """미디어 그룹 사진 모두 수집 후 처리."""
    await asyncio.sleep(3)  # 나머지 사진 도착 대기

    group = _pending_groups.pop(gid, None)
    if not group:
        return

    photos = group["photos"]
    msg = group["msg"]
    status_msg = group["status_msg"]

    n = len(photos)
    await status_msg.edit_text(f"사진 {n}장 분석 중... ⏳ (20~40초 소요)")

    try:
        content = generate_content_multi(photos)
    except Exception as e:
        await status_msg.edit_text(f"콘텐츠 생성 실패: {e}")
        return

    await status_msg.edit_text(f"워터마크 + 슬라이드쇼 영상 생성 중... 🎬 ({n}장)")

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
        "video_path": video_path,
        "caption": content["caption"],
        "strategy": content["strategy"],
        "slide_order": content["slide_order"],
        "submitter": msg.from_user.full_name,
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _make_approval_keyboard(post_key, bool(video_path), True)
    preview = (
        f"🖼 *카루셀/슬라이드쇼 미리보기* ({n}장)\n"
        f"제출: {msg.from_user.full_name} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"💡 전략: {content['strategy']}\n\n"
        f"📋 슬라이드 순서: {content['slide_order']}\n\n"
        f"📝 캡션:\n{content['caption']}\n\n"
        f"⏰ {content['post_time']}"
    )

    # 첫 번째 사진으로 미리보기
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
            print(f"슬라이드쇼 미리보기 전송 실패: {e}")

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
            _pending_groups[gid] = {
                "photos": [],
                "msg": msg,
                "status_msg": status_msg,
            }
            asyncio.create_task(_process_group(gid, context))
        _pending_groups[gid]["photos"].append(image_bytes)
    else:
        status_msg = await msg.reply_text("사진 분석 중... ⏳ (15~30초 소요)")
        await _process_single(msg, image_bytes, context, status_msg)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, post_key = query.data.split("_", 1)
    post = context.bot_data.get(post_key)

    if not post:
        await query.edit_message_caption("⚠️ 세션 만료. 사진을 다시 전송해주세요.")
        return

    if action == "photo":
        await query.edit_message_caption("📤 사진 포스팅 중... ⏳")
        try:
            pk = post_photo_to_instagram(post["image_bytes"], post["caption"])
            await query.edit_message_caption(f"✅ 사진 포스팅 완료!\nPost ID: {pk}\n{datetime.now(KST).strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            await query.edit_message_caption(f"❌ 포스팅 실패\n{e}")
        finally:
            _cleanup_post(post); context.bot_data.pop(post_key, None)

    elif action == "carousel":
        await query.edit_message_caption("📤 카루셀 포스팅 중... ⏳")
        try:
            pk = post_carousel_to_instagram(post["images"], post["caption"])
            await query.edit_message_caption(f"✅ 카루셀 포스팅 완료!\nPost ID: {pk}\n{datetime.now(KST).strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            await query.edit_message_caption(f"❌ 카루셀 포스팅 실패\n{e}")
        finally:
            _cleanup_post(post); context.bot_data.pop(post_key, None)

    elif action == "reel":
        if not post.get("video_path"):
            await query.edit_message_caption("❌ 영상이 없습니다.")
            return
        await query.edit_message_caption("📤 릴스 포스팅 중... ⏳")
        try:
            pk = post_reel_to_instagram(post["video_path"], post["caption"])
            await query.edit_message_caption(f"✅ 릴스 포스팅 완료!\nPost ID: {pk}\n{datetime.now(KST).strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            await query.edit_message_caption(f"❌ 릴스 포스팅 실패\n{e}")
        finally:
            _cleanup_post(post); context.bot_data.pop(post_key, None)

    elif action == "reject":
        await query.edit_message_caption(f"❌ 거절됨\n제출: {post['submitter']} ({post['ts']})")
        _cleanup_post(post); context.bot_data.pop(post_key, None)

    elif action == "edit":
        context.user_data["editing"] = post_key
        await query.message.reply_text(f"수정할 캡션을 입력해주세요.\n\n현재 캡션:\n{post['caption']}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not context.user_data:
        return
    editing_key = context.user_data.get("editing")
    if not editing_key:
        return

    post = context.bot_data.get(editing_key)
    if not post:
        await update.message.reply_text("⚠️ 세션 만료.")
        context.user_data.pop("editing", None)
        return

    post["caption"] = update.message.text
    context.user_data.pop("editing", None)

    is_multi = post.get("type") == "multi"
    keyboard = _make_approval_keyboard(editing_key, bool(post.get("video_path")), is_multi)
    first_img = post["images"][0] if is_multi else post["image_bytes"]

    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID, photo=first_img,
        caption=f"📸 *수정된 미리보기*\n\n{post['caption']}",
        parse_mode="Markdown", reply_markup=keyboard,
    )
    await update.message.reply_text("캡션이 수정되었습니다. ✏️")


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
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot 시작 (Ctrl+C로 종료)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
