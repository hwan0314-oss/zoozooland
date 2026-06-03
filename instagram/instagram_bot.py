import base64
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import anthropic
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
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

BRAND_PROMPT = """\
당신은 쥬쥬랜드(ZooZoo Land) 인스타그램 SNS 담당자입니다.

브랜드 가이드:
- 어린이·가족 동물원 테마파크, 활기차고 따뜻한 톤
- 카피: 짧고 임팩트 있게, 이모지 적극 활용
- 필수 해시태그: #ZZL #쥬쥬랜드

사진을 보고 아래 형식으로 인스타그램 캡션을 작성하세요.

[형식]
(임팩트 한 줄 카피, 15자 이내) 🌿

(따뜻한 본문 설명 2~3줄)

#ZZL #쥬쥬랜드 (관련 해시태그 5~7개)

한국어로 작성하세요. 형식 외 다른 텍스트는 출력하지 마세요.\
"""


# ─── Instagram Client ──────────────────────────────────────────────────────────

_ig_client: Client | None = None


def challenge_code_handler(username, choice):
    print(f"\n⚠️  Instagram 인증 필요! 계정: {username}")
    print(f"인증 방법: {'SMS' if choice == 1 else '이메일'}")
    print("Instagram 앱 또는 이메일에서 받은 6자리 코드를 입력하세요:")
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


def post_to_instagram(image_bytes: bytes, caption: str) -> str:
    fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    try:
        os.write(fd, image_bytes)
        os.close(fd)

        try:
            cl = get_ig_client()
            media = cl.photo_upload(tmp_path, caption)
        except (LoginRequired, ChallengeRequired):
            global _ig_client
            _ig_client = None
            cl = get_ig_client()
            media = cl.photo_upload(tmp_path, caption)

        return str(media.pk)
    finally:
        os.unlink(tmp_path)


# ─── Claude Vision ─────────────────────────────────────────────────────────────

def generate_caption(image_bytes: bytes) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    b64 = base64.b64encode(image_bytes).decode()
    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                },
                {"type": "text", "text": BRAND_PROMPT},
            ],
        }],
    )
    return resp.content[0].text.strip()


# ─── Telegram Handlers ─────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    status_msg = await msg.reply_text("사진 분석 중... ⏳")

    photo_file = await (await context.bot.get_file(msg.photo[-1].file_id)).download_as_bytearray()
    image_bytes = bytes(photo_file)

    try:
        caption = generate_caption(image_bytes)
    except Exception as e:
        await status_msg.edit_text(f"캡션 생성 실패: {e}")
        return

    await status_msg.delete()

    post_key = f"{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "image_bytes": image_bytes,
        "caption": caption,
        "submitter": msg.from_user.full_name,
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 승인 · 포스팅", callback_data=f"approve_{post_key}"),
            InlineKeyboardButton("✏️ 캡션 수정",     callback_data=f"edit_{post_key}"),
        ],
        [InlineKeyboardButton("❌ 거절", callback_data=f"reject_{post_key}")],
    ])

    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID,
        photo=image_bytes,
        caption=(
            f"📸 *인스타그램 게시물 미리보기*\n"
            f"제출: {msg.from_user.full_name} | {datetime.now(KST).strftime('%H:%M')}\n\n"
            f"{caption}"
        ),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    if msg.chat_id != APPROVAL_CHAT_ID:
        await msg.reply_text("담당자에게 승인 요청을 보냈습니다. ✉️")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, post_key = query.data.split("_", 1)
    post = context.bot_data.get(post_key)

    if not post:
        await query.edit_message_caption("⚠️ 세션 만료. 사진을 다시 전송해주세요.")
        return

    if action == "approve":
        await query.edit_message_caption("Instagram 포스팅 중... ⏳")
        try:
            pk = post_to_instagram(post["image_bytes"], post["caption"])
            await query.edit_message_caption(
                f"✅ 포스팅 완료!\n"
                f"Post ID: {pk}\n"
                f"{datetime.now(KST).strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception as e:
            await query.edit_message_caption(f"❌ 포스팅 실패\n{e}")
        finally:
            context.bot_data.pop(post_key, None)

    elif action == "reject":
        await query.edit_message_caption(
            f"❌ 거절됨\n제출: {post['submitter']} ({post['ts']})"
        )
        context.bot_data.pop(post_key, None)

    elif action == "edit":
        context.user_data["editing"] = post_key
        await query.message.reply_text(
            f"수정할 캡션을 입력해주세요.\n\n현재 캡션:\n{post['caption']}"
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 승인 · 포스팅", callback_data=f"approve_{editing_key}"),
            InlineKeyboardButton("✏️ 다시 수정",     callback_data=f"edit_{editing_key}"),
        ],
        [InlineKeyboardButton("❌ 거절", callback_data=f"reject_{editing_key}")],
    ])

    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID,
        photo=post["image_bytes"],
        caption=f"📸 *수정된 미리보기*\n\n{post['caption']}",
        parse_mode="Markdown",
        reply_markup=keyboard,
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
