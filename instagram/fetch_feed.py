"""Instagram Graph API에서 최신 게시물을 가져와 website/data/instagram_feed.json으로 저장.

LightWidget(서드파티 iframe) 의존성을 없애기 위해 사이트에서 직접 렌더링하는 용도.

이미지는 website/images/instagram/ 에 내려받아 저장한다.
인스타그램 CDN 이미지 주소(scontent-*.cdninstagram.com)는 며칠 뒤 만료되므로,
주소를 그대로 쓰면 피드 갱신이 한 번만 멈춰도 홈페이지 사진이 전부 깨진다.

토큰 만료 등으로 실패하면 기존 피드를 건드리지 않고 종료 코드 1로 끝낸다.
(예전에는 실패해도 성공으로 끝나서, 피드가 멈춘 걸 알 수 없었다.)
"""
import json
import os
import sys
from pathlib import Path

import requests

ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
ACCOUNT_ID = os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
API = "https://graph.instagram.com/v21.0"
LIMIT = 9
ROOT = Path(__file__).parent.parent
OUT_FILE = ROOT / "website" / "data" / "instagram_feed.json"
IMG_DIR = ROOT / "website" / "images" / "instagram"
IMG_WEB_PATH = "images/instagram"  # 사이트 기준 상대 경로


def get_image_url(post: dict) -> str | None:
    if post.get("media_type") == "VIDEO":
        return post.get("thumbnail_url") or post.get("media_url")
    if post.get("media_type") == "CAROUSEL_ALBUM":
        r = requests.get(
            f"{API}/{post['id']}/children",
            params={"fields": "media_url,media_type,thumbnail_url", "access_token": ACCESS_TOKEN},
            timeout=15,
        )
        r.raise_for_status()
        for child in r.json().get("data", []):
            url = child.get("thumbnail_url") if child.get("media_type") == "VIDEO" else child.get("media_url")
            if url:
                return url
        return None
    return post.get("media_url")


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True  # 이미 받은 게시물은 다시 받지 않음
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        return False
    dest.write_bytes(r.content)
    return True


def main() -> int:
    if not ACCESS_TOKEN or not ACCOUNT_ID:
        print("[ERROR] INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_ACCOUNT_ID secret이 비어 있습니다.")
        return 1

    r = requests.get(
        f"{API}/{ACCOUNT_ID}/media",
        params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
            "limit": LIMIT,
            "access_token": ACCESS_TOKEN,
        },
        timeout=30,
    )
    if r.status_code != 200:
        try:
            err = r.json().get("error", {})
        except ValueError:
            err = {}
        print(f"[ERROR] Instagram API {r.status_code}: {err.get('message', r.text[:200])}")
        if err.get("code") == 190 or r.status_code in (400, 401):
            print("토큰이 만료됐거나 잘못됐습니다. 새 장기 토큰을 발급해 GitHub secret INSTAGRAM_ACCESS_TOKEN을 바꿔주세요.")
        return 1
    data = r.json().get("data", [])

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    posts, keep = [], set()
    for post in data:
        try:
            url = get_image_url(post)
            if not url:
                continue
            name = f"{post['id']}.jpg"
            if not download(url, IMG_DIR / name):
                continue
        except requests.RequestException as e:
            print(f"[WARN] 게시물 {post.get('id')} 이미지 건너뜀: {e}")
            continue
        keep.add(name)
        caption = (post.get("caption") or "").strip().splitlines()[0] if post.get("caption") else ""
        if len(caption) > 60:
            caption = caption[:60].rsplit(" ", 1)[0] + "…"
        posts.append({
            "id": post["id"],
            "image": f"{IMG_WEB_PATH}/{name}",
            "caption": caption,
            "permalink": post.get("permalink"),
            "timestamp": post.get("timestamp"),
        })

    if not posts:
        print("[ERROR] 가져온 게시물이 없습니다. 기존 피드를 그대로 둡니다.")
        return 1

    # 피드에서 빠진 예전 이미지 정리
    for f in IMG_DIR.glob("*.jpg"):
        if f.name not in keep:
            f.unlink()

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({"posts": posts}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(posts)} posts to {OUT_FILE}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.RequestException as e:
        print(f"[ERROR] Instagram 요청 실패: {e}")
        sys.exit(1)
