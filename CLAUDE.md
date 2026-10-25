# CLAUDE.md — zoozooland 저장소 작업 규칙

이 파일은 Claude가 세션을 시작할 때 가장 먼저 읽는 문서입니다.
작업 전 반드시 `WORKLOG.md`의 "다음 할 일"과 `docs/ROADMAP.md`의 현재 단계를 확인하세요.

## 1. 이 저장소는 무엇인가

쥬쥬랜드(ZZL, 경기 고양시 덕양구 원당로458번길 7-42) 공식 홈페이지 **zoozoo.kr**과
쥬쥬랜드 운영 자동화가 한 저장소에 함께 들어 있습니다.

| 폴더/파일 | 역할 | 홈페이지 배포 영향 |
|---|---|---|
| `website-zzl/` | **실제 운영 중인 홈페이지** (index.html, dogam.html, map.html, css, js) | 배포됨 (사이트 루트) |
| `website-zzl/build.py` | 빌드 스크립트: JSON → 정적 HTML 주입(SSG), WebP 변환, 구조화 데이터·sitemap 생성 | 배포 결과물에서는 제외 |
| `website-zzl/tailwind.config.js`, `css/tailwind.src.css` | Tailwind 빌드 설정 (배포 시 `css/tailwind.css` 생성) | 배포 결과물에서는 제외 |
| `website/data/` | 홈페이지가 읽는 데이터 JSON (운영시간·상품·프로그램·공지·리뷰·FAQ·설정·인스타 피드) | 배포됨 (`/data`) |
| `website/images/` | 홈페이지 이미지 | 배포됨 (`/images`) |
| `guidemap/` | 안내지도 편집용 로컬 Node 서버 (배포 안 됨) | 없음 |
| `instagram/`, `reels/` | 인스타그램 피드 수집·게시, 릴스 자동화 | 피드 데이터만 |

구버전 사이트(`website/index.html`, `website/css/style.css`, `website/js/main.js`)는 2026-10-24에 삭제했습니다(PR #6).
관리자 대시보드(`website/admin/`, `dashboard.js`)와 실적·마케팅 수집 코드(`report.py`, `marketing_analytics_etl.py`, `dashboard/` 등)는 ZZL Work와 비공개 저장소 `zzl-collectors`로 옮기고 삭제했습니다(PR #12).
`website-zzl/css/style.css`, `website-zzl/js/main.js`는 현재 사이트 파일이니 혼동하지 마세요.

**홈페이지 작업 범위는 `website-zzl/`, `website/data/`, `website/images/`, `.github/workflows/deploy-website.yml` 입니다.**
리포트·인스타·릴스 자동화 파일은 사용자가 명시적으로 요청하지 않는 한 건드리지 않습니다.

## 2. 배포 구조

- `main` 브랜치에 `website/**`, `website-zzl/**` 변경이 push되면 GitHub Actions(`deploy-website.yml`)가 GitHub Pages로 자동 배포 → **main에 올리는 순간 실서비스 반영**.
- 배포 과정:
  1. `website-zzl/` → `deploy/` 복사, `website/data`·`images` 복사, CNAME `zoozoo.kr`
  2. `website-zzl/build.py`: JSON 내용을 `index.html`의 `<!-- ssg:이름 -->` 마커 사이에 정적으로 주입(SEO용), 이미지를 WebP `<picture>`로 변환, 구조화 데이터(JSON-LD)·`sitemap.xml` 생성
  3. Tailwind 빌드 → `deploy/css/tailwind.css` (개발용 CDN은 쓰지 않음)
- 인스타그램 피드 봇이 `website/data/instagram_feed.json`과 `website/images/instagram/`을 수시로 커밋하므로, 작업 전 항상 `git pull` 할 것.

## 3. 작업 방식 (반드시 지킬 것)

1. **main에 직접 push 금지.** 브랜치(`design/winter-2026` 같은 이름)에서 작업 → PR → 사용자 확인 후 병합.
2. 수정 후 로컬 확인: 아래 "로컬 미리보기"로 데스크톱(1440px)·모바일(390px) 두 폭에서 화면을 확인하고, 가로 스크롤이 생기지 않는지(`document.documentElement.scrollWidth`가 화면 폭과 같은지) 확인.
3. `build.py`의 ssg 마커(`<!-- ssg:product -->` 등)는 지우거나 이름을 바꾸지 말 것. 바꿔야 하면 `build.py`도 같이 수정.
4. 운영 정보는 HTML에 직접 쓰지 말고 `website/data/*.json`에서 관리.
   - 운영시간·휴무·공휴일·임시휴무: `hours.json` / 요금·예약 URL: `products.json` / 프로그램: `programs.json`
   - 공지: `notices.json` / 리뷰: `reviews.json` / FAQ: `faq.json` / 단체 예약·카카오 채널 주소: `settings.json`
   - 시즌 효과: `settings.json`의 `season_effect` (`"autumn_leaves"`면 가을 낙엽, `""`면 끔. 코드는 `js/season-leaves.js`)
5. 디자인 규칙은 `docs/DESIGN.md`를 따른다. 색상은 CSS 변수로만 쓰고 HTML에 hex 값을 직접 쓰지 않는다.
6. 세션을 끝낼 때 `WORKLOG.md`에 "한 일 / 다음 할 일"을 3~5줄로 추가한다.
7. 큰 이미지(1MB 이상)·PDF는 그대로 넣지 말고 웹용으로 줄여서 넣는다.
8. API 키·토큰·비밀번호는 저장소에 커밋하지 않는다 (이 저장소는 public).

## 4. 로컬 미리보기

배포 워크플로와 같은 순서입니다 (`pip install pillow` 필요).

```bash
rm -rf deploy && mkdir -p deploy/js
cp -r website-zzl/. deploy/ && cp -r website/data deploy/data && cp -r website/images deploy/images
python3 website-zzl/build.py
npx --yes tailwindcss@3.4.17 -c website-zzl/tailwind.config.js \
  -i website-zzl/css/tailwind.src.css -o deploy/css/tailwind.css --minify
cd deploy && python3 -m http.server 8765   # http://localhost:8765
```
`deploy/`는 빌드 결과물이므로 커밋하지 않는다.

## 5. 사이트 정보 (변경 시 여기도 갱신)

- 운영: 10:00–18:00, 월요일 휴무(공휴일인 월요일은 정상 운영) — 기준은 `website/data/hours.json`
- 대표전화 031-962-4500 / 제휴 hwan9740@zoozoo.kr
- 단체: 단체 예약 페이지 `https://booking.zoozoo.kr/group` (`settings.json`의 `group_booking_url`). 단체 이메일 문의는 받지 않음
- 단체 도시락: 쥬쥬레스토랑 010-9425-9495 (FAQ에 안내)
- 예약: 네이버 예약 (URL은 `website/data/products.json`)
- 분석: GA4 `G-HF2XRXQE6X`, Microsoft Clarity (`data-track` 속성으로 클릭 이벤트 전송)
- 브랜드 언어: ZZL = "즐", 동물은 "쥬민". 카피는 "ZZL겨볼까?"처럼 ZZL 말장난을 살린다.
- 주 방문객: 아이 동반 가족 → 한국어 우선, 영어 장식 문구는 보조로만.

## 6. 담당자

홈페이지 관리는 최석환 이사가 단독 결정·처리한다. 변경 사항은 배포 후 직원에게 공지.
