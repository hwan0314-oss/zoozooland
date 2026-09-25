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
