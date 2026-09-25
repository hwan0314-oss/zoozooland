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
    except Exception as e:
        # 텔레그램 전송(외부 서비스 경계)에서 무엇이 실패하든 영상은 이미 저장되어 있으니
        # 에러를 보고하고 안전하게 끝낸다 (조용히 삼키지 않는다).
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
