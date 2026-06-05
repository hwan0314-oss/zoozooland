import requests

TOKEN = "EAGDt4rXqZAxEBRj5KTTIubWHNR8xNoRwMndrCNEVX5Dl4ZA8Isv0VbU0JJftUtBCIZA6MtuI1yZBReD7WQV8PS1kSHJU7w4nqwoBEXBLIrYtOSGyRKGVR63AVLUJ0oYGxPuevwWZCO7Oj1feYMUu2lSnZCnQ7ZAls7ibqiwqqbfrbQQ6VQGiKdGZBIpzutIfbQ9CsRPAUE9Qadfsen7Kx31Y2EaSraYTZCsNCOwZDZD"
IG_ID = "17841444570925602"

# 1. 토큰 확인
r0 = requests.get("https://graph.facebook.com/v21.0/me", params={"fields": "id,name", "access_token": TOKEN})
print("토큰 유저:", r0.json())

# 2. 직접 미디어 생성 시도
r1 = requests.post(
    f"https://graph.facebook.com/v21.0/{IG_ID}/media",
    data={"image_url": "https://i.ibb.co/cXgfvv0n/photo.jpg", "caption": "test", "access_token": TOKEN},
    timeout=30,
)
print("미디어 생성:", r1.json())

# 3. 페이지 토큰으로 시도
r2 = requests.get(f"https://graph.facebook.com/v21.0/1184428141413290", params={"fields": "access_token", "access_token": TOKEN})
page_data = r2.json()
print("페이지 토큰:", page_data)

if "access_token" in page_data:
    page_token = page_data["access_token"]
    r3 = requests.post(
        f"https://graph.facebook.com/v21.0/{IG_ID}/media",
        data={"image_url": "https://i.ibb.co/cXgfvv0n/photo.jpg", "caption": "test", "access_token": page_token},
        timeout=30,
    )
    print("페이지 토큰으로 미디어 생성:", r3.json())
