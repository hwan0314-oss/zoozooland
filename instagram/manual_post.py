"""큐에서 오늘 항목 수동 포스팅 후 삭제."""
import json, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from instagrapi import Client

QUEUE_FILE  = Path(__file__).parent / "queue.json"
SESSION_FILE = Path(__file__).parent / "ig_session.json"
TODAY = "2026-06-05"

with open(QUEUE_FILE) as f:
    queue = json.load(f)

item = next((i for i in queue if i["scheduled_date"] == TODAY), None)
if not item:
    print(f"오늘({TODAY}) 큐 항목 없음")
else:
    print(f"포스팅 시도: {item['main_copy']}")
    cl = Client()
    cl.delay_range = [2, 5]
    cl.load_settings(str(SESSION_FILE))

    # 세션 유효성 확인 (재로그인 없이)
    try:
        cl.get_timeline_feed()
        print("세션 유효 확인")
    except Exception as e:
        print(f"세션 오류: {e}")
        exit(1)

    try:
        media = cl.photo_upload(item["media_path"], item["caption"])
        print(f"✅ 성공! Post ID: {media.pk}")
        queue = [i for i in queue if i["id"] != item["id"]]
        with open(QUEUE_FILE, "w") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        print("큐에서 제거 완료")
    except Exception as e:
        print(f"❌ 업로드 실패: {e}")
