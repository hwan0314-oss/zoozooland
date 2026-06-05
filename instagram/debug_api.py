import requests

TOKEN = "EAGDt4rXqZAxEBRoMNBiZBGFdGiLy4rArOofh3nYZCuz3cbZB5HBdp5bZCfj3aA1IO8v15GFSwJnF043gyViKmgvsPATYYcjr5bZApQE7z66XZA8oGrxJE2v4Cj6nOoamTQwBCwmHrvSLhTlR5OnyFG4ZAhVYjR3u1p6cv0nDrS4eM7NNGbrqEfBVZBIVvFouxkG7yksugyQ4lMhvS0PwNJRAqIJQekRSiYygswdLwye4gzHS3mzLkZBF4jidwTJdU0dnVDOfoYoGNRgbIZD"
IG_ID = "17841444570925602"
PAGE_ID = "1184428141413290"

# 1. 토큰 확인
r0 = requests.get("https://graph.facebook.com/v21.0/me", params={"fields": "id,name", "access_token": TOKEN})
print("유저:", r0.json())

# 2. 페이지 instagram_business_account 확인
r1 = requests.get(f"https://graph.facebook.com/v21.0/{PAGE_ID}", params={"fields": "instagram_business_account", "access_token": TOKEN})
print("instagram_business_account:", r1.json())

# 3. 직접 미디어 생성
r2 = requests.post(
    f"https://graph.facebook.com/v21.0/{IG_ID}/media",
    data={"image_url": "https://i.ibb.co/cXgfvv0n/photo.jpg", "caption": "test", "access_token": TOKEN},
    timeout=30,
)
print("미디어 생성:", r2.json())
