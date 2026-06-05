import os, requests
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

# 새 토큰으로 테스트
token = "EAGDt4rXqZAxEBRoAs3WiHNhCXr5vdNvSsgyZBkzBcSEqRo7hXP4XR4uxYQyOgYu2QjTeoghheys8QHtIinQVoxEjl7AYoJPrTFTNLevc2ZBaqByIftNEUKlY4uVu7dLvQhyYkWQ2KK6R77qi0MUGlI6kVrIMaNixjGHFB11vzoaaAB4BbaQ7hZAGwcj4MB79KMR8ly1hVzIXl6NYTSRrDda5cfjvSxKk3pw8BflUW7ulVn6mTZAkHo1qvtPC6stYvhvg37V3AvAB9"

PAGE_ID = "1184428141413290"  # zoozooland-instagram 페이지 ID

# 1. me/accounts 확인
print("=== me/accounts ===")
r = requests.get("https://graph.facebook.com/v21.0/me/accounts", params={"access_token": token, "fields": "id,name,access_token"})
print(r.json())

# 2. 페이지 직접 조회
print("\n=== 페이지 직접 조회 ===")
r2 = requests.get(f"https://graph.facebook.com/v21.0/{PAGE_ID}", params={"fields": "id,name,access_token", "access_token": token})
print(r2.json())

# 3. Business 조회
print("\n=== me/businesses ===")
r3 = requests.get("https://graph.facebook.com/v21.0/me/businesses", params={"access_token": token})
print(r3.json())

# 4. 토큰 권한 확인
print("\n=== 토큰 권한 ===")
r4 = requests.get("https://graph.facebook.com/v21.0/me/permissions", params={"access_token": token})
print(r4.json())
