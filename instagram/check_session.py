"""세션 상태 확인 및 업로드 테스트."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from instagrapi import Client

SESSION = Path(__file__).parent / "ig_session.json"

cl = Client()
cl.delay_range = [2, 5]

if SESSION.exists():
    cl.load_settings(str(SESSION))
    print(f"세션 로드됨. user_id: {cl.user_id}")
else:
    print("세션 파일 없음")

# 세션만으로 API 호출 테스트 (login 없이)
try:
    info = cl.account_info()
    print(f"계정 확인: @{info.username}")
    print("✅ 세션 유효")
except Exception as e:
    print(f"❌ 세션 오류: {e}")
    print("→ username/password로 재로그인 시도...")
    try:
        cl2 = Client()
        cl2.delay_range = [2, 5]
        cl2.login(os.environ["INSTAGRAM_USERNAME"], os.environ["INSTAGRAM_PASSWORD"])
        cl2.dump_settings(str(SESSION))
        info = cl2.account_info()
        print(f"✅ 재로그인 성공: @{info.username}")
    except Exception as e2:
        print(f"❌ 재로그인도 실패: {e2}")
