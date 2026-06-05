import os, requests
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

token = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ig_id = os.environ["INSTAGRAM_ACCOUNT_ID"]

# 1. 토큰 권한 확인
print("=== 토큰 확인 ===")
r = requests.get(f"https://graph.facebook.com/v21.0/me?fields=id,name&access_token={token}")
print(r.json())

# 2. Instagram 계정 정보 확인
print("\n=== Instagram 계정 확인 ===")
r2 = requests.get(
    f"https://graph.facebook.com/v21.0/{ig_id}",
    params={"fields": "id,username,account_type", "access_token": token}
)
print(r2.json())

# 3. 미디어 생성 시도
print("\n=== 미디어 생성 시도 ===")
r3 = requests.post(
    f"https://graph.facebook.com/v21.0/{ig_id}/media",
    data={"image_url": "https://i.ibb.co/Sw7ySqPx/photo.jpg", "caption": "test", "access_token": token},
    timeout=30,
)
print(r3.status_code, r3.json())
