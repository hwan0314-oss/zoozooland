import asyncio
import base64
import json
import os
import uuid
from datetime import datetime, timezone, timedelta, time as dtime
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

_pending_groups: dict = {}

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
6. [해시태그] #ZZL #쥬쥬랜드 #ZZLstagram #동물이말하는우리얘기 + 동물명 + 관련 감성 태그

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


def get_next_available_date() -> str:
    now = datetime.now(KST)
    today = now.date()
    candidate = today if (now.hour < 7 or (now.hour == 7 and now.minute < 30)) else today + timedelta(days=1)
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
    return str(_ig_call(lambda: get_ig_client().photo_upload(image_path, caption)).pk)


def post_carousel(image_paths: list, caption: str) -> str:
    return str(_ig_call(lambda: get_ig_client().album_upload(image_paths, caption)).pk)


# ─── Card Image Rendering (Playwright) ────────────────────────────────────────

def _build_card_html(image_b64: str, main_copy: str, sub_copy: str) -> str:
    # HTML 특수문자 이스케이프
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    main_html = esc(main_copy).replace("\n", "<br>")
    sub_html  = esc(sub_copy)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@1,400;1,600&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; height: 1080px; overflow: hidden; background: #121212; }}
.card {{
  width: 1080px; height: 1080px;
  position: relative;
  background-image: url('data:image/jpeg;base64,{image_b64}');
  background-size: cover;
  background-position: center;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 60px;
}}
.scrim {{
  position: absolute;
  bottom: 0; left: 0;
  width: 100%; height: 52%;
  background: linear-gradient(to top, rgba(0,0,0,0.88) 0%, rgba(0,0,0,0.4) 60%, rgba(0,0,0,0) 100%);
  pointer-events: none;
}}
.zzl-mark {{
  position: absolute;
  top: 44px; left: 60px;
  font-family: 'Pretendard', sans-serif;
  font-size: 16px;
  font-weight: 300;
  letter-spacing: 0.18em;
  color: rgba(255,255,255,0.22);
  z-index: 10;
}}
.text-block {{
  position: relative;
  z-index: 10;
  border-left: 3px solid #44B134;
  padding-left: 22px;
}}
.main-copy {{
  font-family: 'Pretendard', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  font-size: 66px;
  font-weight: 700;
  color: #FFFFFF;
  line-height: 1.18;
  letter-spacing: -0.025em;
  margin-bottom: 16px;
}}
.sub-copy {{
  font-family: 'Cormorant Garamond', Georgia, serif;
  font-style: italic;
  font-weight: 400;
  font-size: 32px;
  color: #44B134;
  line-height: 1.3;
  letter-spacing: 0.01em;
}}
</style>
</head>
<body>
<div class="card">
  <div class="scrim"></div>
  <span class="zzl-mark">ZZL</span>
  <div class="text-block">
    <div class="main-copy">{main_html}</div>
    <div class="sub-copy">{sub_html}</div>
  </div>
</div>
</body>
</html>"""


async def render_card_image(image_bytes: bytes, main_copy: str, sub_copy: str) -> bytes:
    """Playwright로 HTML 카드를 렌더링해서 JPEG bytes 반환."""
    from playwright.async_api import async_playwright

    b64 = base64.b64encode(image_bytes).decode()
    html = _build_card_html(b64, main_copy, sub_copy)

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
    parts = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
              "data": base64.b64encode(img).decode()}} for img in images[:10]]
    parts.append({"type": "text", "text": f"총 {len(images)}장입니다.\n\n{MULTI_BRAND_PROMPT}"})
    resp = client.messages.create(
        model="claude-opus-4-8", max_tokens=1000,
        messages=[{"role": "user", "content": parts}],
    )
    return _parse_content(resp.content[0].text.strip())


def regenerate_with_edit(image_bytes: bytes, original_raw: str, edit_request: str) -> dict:
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
            if item["post_type"] == "photo":
                pk = post_photo(item["media_path"], item["caption"])
            elif item["post_type"] == "carousel":
                paths = [item["media_path"]] + item.get("extra_media", [])
                pk = post_carousel(paths, item["caption"])
            else:
                continue
            day_ko = ["월","화","수","목","금","토","일"][datetime.strptime(today, "%Y-%m-%d").weekday()]
            await context.bot.send_message(
                chat_id=APPROVAL_CHAT_ID,
                text=f"✅ 예약 포스팅 완료!\n📅 {today[:7].replace('-','/')}/{today[8:]} ({day_ko}) 07:30\n📌 {item['main_copy']}\nPost ID: {pk}",
            )
            save_queue([i for i in load_queue() if i["id"] != item["id"]])
        except Exception as e:
            await context.bot.send_message(chat_id=APPROVAL_CHAT_ID, text=f"❌ 예약 포스팅 실패 ({today})\n{e}")
        break


# ─── Approval Keyboard ────────────────────────────────────────────────────────

def _approval_keyboard(post_key: str, is_multi: bool) -> InlineKeyboardMarkup:
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

    await status_msg.edit_text("카드 이미지 제작 중... 🎨")

    try:
        card_image = await render_card_image(image_bytes, content["main_copy"], content["sub_copy"])
    except Exception as e:
        print(f"카드 렌더링 실패: {e}")
        card_image = image_bytes

    await status_msg.delete()

    post_key = f"{abs(msg.chat_id) % 10000}_{msg.message_id}"
    context.bot_data[post_key] = {
        "type": "single",
        "card_image": card_image,
        "original_image": image_bytes,
        "caption": content["caption"],
        "main_copy": content["main_copy"],
        "sub_copy": content["sub_copy"],
        "raw_output": content["raw"],
        "submitter": (msg.from_user.full_name if msg.from_user else '채널'),
        "ts": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }

    keyboard = _approval_keyboard(post_key, False)
    preview = (
        f"📸 *콘텐츠 미리보기*\n"
        f"제출: {(msg.from_user.full_name if msg.from_user else '채널')} | {datetime.now(KST).strftime('%H:%M')}\n\n"
        f"📌 메인: *{content['main_copy']}*\n"
        f"💬 서브: _{content['sub_copy']}_"
    )
    await context.bot.send_photo(
        chat_id=APPROVAL_CHAT_ID, photo=card_image,
        caption=preview[:1024], parse_mode="Markdown", reply_markup=keyboard,
    )
    # 전체 캡션 별도 메시지로 전송
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
            else:
                await query.edit_message_caption("❌ 지원하지 않는 타입입니다.")
                return
            day_ko = ["월","화","수","목","금","토","일"][datetime.strptime(scheduled, "%Y-%m-%d").weekday()]
            await query.edit_message_caption(
                f"✅ 큐에 추가됐습니다!\n\n"
                f"📅 {scheduled[:7].replace('-','/')}/{scheduled[8:]} ({day_ko}) 07:30\n"
                f"📌 {post['main_copy']}"
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
        img = post.get("original_image") or (post.get("original_images", [None])[0])
        edit_data = {"post_key": post_key, "raw": post["raw_output"], "image_bytes": img}
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
    try:
        new = regenerate_with_edit(edit_state["image_bytes"], edit_state["raw"], msg.text)
        try:
            card_image = await render_card_image(edit_state["image_bytes"], new["main_copy"], new["sub_copy"])
        except Exception:
            card_image = edit_state["image_bytes"]
        post.update({"card_image": card_image, "caption": new["caption"],
                     "main_copy": new["main_copy"], "sub_copy": new["sub_copy"], "raw_output": new["raw"]})
        if "card_images" in post:
            post["card_images"][0] = card_image
        is_multi = post.get("type") == "multi"
        first_img = post["card_images"][0] if is_multi else post["card_image"]
        await context.bot.send_photo(
            chat_id=APPROVAL_CHAT_ID, photo=first_img,
            caption=(
                f"📸 *수정된 미리보기*\n\n"
                f"📌 메인: *{new['main_copy']}*\n"
                f"💬 서브: _{new['sub_copy']}_\n\n"
                f"📝 캡션:\n{new['caption'][:400]}..."
            ),
            parse_mode="Markdown",
            reply_markup=_approval_keyboard(post_key, is_multi),
        )
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
        lines.append(f"{i}️⃣ {d.month}/{d.day} ({DAYS[d.weekday()]}) 07:30\n   \"{main}\"")
        rows.append([
            InlineKeyboardButton("수정", callback_data=f"qedit_{item['id']}"),
            InlineKeyboardButton("취소", callback_data=f"qcancel_{item['id']}"),
        ])
    lines.append(f"─────────────\n총 {len(queue)}개 예약됨")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))


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
    app.job_queue.run_daily(scheduled_post_job, time=dtime(22, 30, 0), name="daily_post")
    app.add_handler(CommandHandler("queue", handle_queue_command))
    app.add_handler(MessageHandler(  # 채널에서 /queue 처리
        filters.UpdateType.CHANNEL_POST & filters.Regex(r"^/queue"),
        handle_queue_command,
    ))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot 시작 (Ctrl+C로 종료)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
