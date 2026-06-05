"""오늘 날짜 큐 항목 수동 포스팅."""
import json, os, time, requests
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

QUEUE_FILE       = Path(__file__).parent / "queue.json"
IG_ACCESS_TOKEN  = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_ACCOUNT_ID    = os.environ["INSTAGRAM_ACCOUNT_ID"]
IMGBB_API_KEY    = os.environ["IMGBB_API_KEY"]
IG_API           = "https://graph.facebook.com/v21.0"
TODAY            = "2026-06-05"

with open(QUEUE_FILE) as f:
    queue = json.load(f)

item = next((i for i in queue if i["scheduled_date"] == TODAY), None)
if not item:
    print(f"오늘({TODAY}) 큐 항목 없음")
    exit(0)

print(f"포스팅 시도: {item['main_copy']}")

# imgbb 업로드
img_bytes = Path(item["media_path"]).read_bytes()
r_img = requests.post(
    "https://api.imgbb.com/1/upload",
    data={"key": IMGBB_API_KEY, "expiration": 600},
    files={"image": ("photo.jpg", img_bytes, "image/jpeg")},
    timeout=30,
)
r_img.raise_for_status()
image_url = r_img.json()["data"]["url"]
print(f"이미지 업로드 완료: {image_url[:50]}...")

# 컨테이너 생성
r1 = requests.post(
    f"{IG_API}/{IG_ACCOUNT_ID}/media",
    data={"image_url": image_url, "caption": item["caption"], "access_token": IG_ACCESS_TOKEN},
    timeout=30,
)
r1.raise_for_status()
creation_id = r1.json()["id"]
print(f"컨테이너 생성: {creation_id}")

# 처리 대기
for _ in range(15):
    time.sleep(4)
    status_r = requests.get(
        f"{IG_API}/{creation_id}",
        params={"fields": "status_code", "access_token": IG_ACCESS_TOKEN},
        timeout=15,
    )
    status = status_r.json().get("status_code", "")
    print(f"상태: {status}")
    if status == "FINISHED":
        break
    if status == "ERROR":
        print(f"처리 실패: {status_r.json()}")
        exit(1)

# 게시
r2 = requests.post(
    f"{IG_API}/{IG_ACCOUNT_ID}/media_publish",
    data={"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN},
    timeout=30,
)
r2.raise_for_status()
post_id = r2.json()["id"]
print(f"✅ 포스팅 완료! Post ID: {post_id}")

# 큐에서 제거
queue = [i for i in queue if i["id"] != item["id"]]
with open(QUEUE_FILE, "w") as f:
    json.dump(queue, f, ensure_ascii=False, indent=2)
print("큐에서 제거 완료")
