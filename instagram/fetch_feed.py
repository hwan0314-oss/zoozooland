"""Instagram Graph API에서 최신 게시물을 가져와 website/data/instagram_feed.json으로 저장.

LightWidget(서드파티 iframe) 의존성을 없애기 위해 사이트에서 직접 렌더링하는 용도.
"""
import json
import os
from pathlib import Path

import requests

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ACCOUNT_ID = os.environ["INSTAGRAM_ACCOUNT_ID"]
API = "https://graph.instagram.com/v21.0"
LIMIT = 9
OUT_FILE = Path(__file__).parent.parent / "website" / "data" / "instagram_feed.json"


def get_image_url(post: dict) -> str | None:
    if post.get("media_type") == "VIDEO":
        return post.get("thumbnail_url") or post.get("media_url")
    if post.get("media_type") == "CAROUSEL_ALBUM":
        r = requests.get(
            f"{API}/{post['id']}/children",
            params={"fields": "media_url,media_type", "access_token": ACCESS_TOKEN},
            timeout=15,
        )
        r.raise_for_status()
        children = r.json().get("data", [])
        if children:
            return children[0].get("media_url")
        return None
    return post.get("media_url")


def main() -> None:
    r = requests.get(
        f"{API}/{ACCOUNT_ID}/media",
        params={
            "fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp",
            "limit": LIMIT,
            "access_token": ACCESS_TOKEN,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json().get("data", [])

    posts = []
    for post in data:
        image = get_image_url(post)
        if not image:
            continue
        caption = (post.get("caption") or "").strip().splitlines()[0] if post.get("caption") else ""
        if len(caption) > 60:
            caption = caption[:60].rsplit(" ", 1)[0] + "…"
        posts.append({
            "id": post["id"],
            "image": image,
            "caption": caption,
            "permalink": post.get("permalink"),
            "timestamp": post.get("timestamp"),
        })

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps({"posts": posts}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(posts)} posts to {OUT_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[WARN] Instagram feed update skipped: {e}")
        print("Token may be expired. Update INSTAGRAM_ACCESS_TOKEN secret to fix.")
        raise SystemExit(0)
