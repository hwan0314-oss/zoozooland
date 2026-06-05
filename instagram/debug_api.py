import requests

TOKEN = "IGAAiMvRTUimBBZAGFNSzh5RDhtNS13d2NwU01sRDBnRHhWQUwyZAEphdFJYd0tKUHB4MjZA2VnBJQmh6WEl6bmhpTElHRTR2bnB4Q2h1a3ptWXR2dG5ncnhVVjViM0pSYUdLdWZAOdzFYelF2bGZAkNktPUjNYbTBnY2t5anY3UEltMAZDZD"

# Instagram 토큰으로 me 조회
r1 = requests.get("https://graph.facebook.com/v21.0/me", params={"fields": "id,name", "access_token": TOKEN})
print("me:", r1.json())

# Instagram 계정 ID 가져오기
if "id" in r1.json():
    ig_id = r1.json()["id"]
    print(f"Instagram ID: {ig_id}")

    # 미디어 생성 시도
    r2 = requests.post(
        f"https://graph.facebook.com/v21.0/{ig_id}/media",
        data={"image_url": "https://i.ibb.co/cXgfvv0n/photo.jpg", "caption": "test", "access_token": TOKEN},
        timeout=30,
    )
    print("미디어 생성:", r2.json())
