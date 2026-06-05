"""큐에서 오늘 항목 수동 포스팅 후 삭제."""
import json, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from instagrapi import Client

QUEUE_FILE = Path(__file__).parent / "queue.json"

with open(QUEUE_FILE) as f:
    queue = json.load(f)

item = next((i for i in queue if i["scheduled_date"] == "2026-06-05"), None)
if not item:
    print("오늘(2026-06-05) 큐 항목 없음")
else:
    print(f"포스팅 시도: {item['main_copy']}")
    cl = Client()
    cl.load_settings(str(Path(__file__).parent / "ig_session.json"))
    cl.login(os.environ["INSTAGRAM_USERNAME"], os.environ["INSTAGRAM_PASSWORD"])
    media = cl.photo_upload(item["media_path"], item["caption"])
    print(f"✅ 성공! Post ID: {media.pk}")
    queue = [i for i in queue if i["id"] != item["id"]]
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    print("큐에서 제거 완료")
