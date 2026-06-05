import os, requests
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

token = os.environ["INSTAGRAM_ACCESS_TOKEN"]

# 1. 접근 가능한 Facebook 페이지 목록
print("=== Facebook 페이지 목록 ===")
r = requests.get(
    "https://graph.facebook.com/v21.0/me/accounts",
    params={"access_token": token}
)
data = r.json()
print(data)

# 2. 각 페이지의 Instagram 계정 확인
print("\n=== 페이지별 Instagram 계정 ===")
for page in data.get("data", []):
    page_id = page["id"]
    page_token = page["access_token"]
    r2 = requests.get(
        f"https://graph.facebook.com/v21.0/{page_id}",
        params={"fields": "instagram_business_account", "access_token": page_token}
    )
    ig_info = r2.json()
    print(f"페이지 {page['name']} ({page_id}): {ig_info}")

    if ig_info.get("instagram_business_account"):
        ig_id = ig_info["instagram_business_account"]["id"]
        print(f"\n✅ Instagram 계정 ID: {ig_id}")
        print(f"✅ Page Access Token: {page_token[:50]}...")

        # 이 Page Token으로 미디어 생성 테스트
        print("\n=== 미디어 생성 테스트 (Page Token) ===")
        r3 = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_id}/media",
            data={"image_url": "https://i.ibb.co/Sw7ySqPx/photo.jpg", "caption": "test", "access_token": page_token},
            timeout=30,
        )
        print(r3.status_code, r3.json())
