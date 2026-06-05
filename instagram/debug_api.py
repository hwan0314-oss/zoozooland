import os, requests
from pathlib import Path

# .env 직접 읽기 (BOM 없이)
with open(Path(__file__).parent / ".env", encoding="utf-8-sig") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "MISSING")
ig_id = os.environ.get("INSTAGRAM_ACCOUNT_ID", "MISSING")
print(f"Token prefix: {token[:40]}")
print(f"IG ID: {ig_id}")

# Instagram 계정 확인
r0 = requests.get(
    f"https://graph.facebook.com/v21.0/{ig_id}",
    params={"fields": "id,username", "access_token": token}
)
print(f"Instagram 계정: {r0.json()}")

# 미디어 생성 테스트
r = requests.post(
    f"https://graph.facebook.com/v21.0/{ig_id}/media",
    data={"image_url": "https://i.ibb.co/cXgfvv0n/photo.jpg", "caption": "test", "access_token": token},
    timeout=30,
)
print(f"미디어 생성: {r.status_code} {r.json()}")
