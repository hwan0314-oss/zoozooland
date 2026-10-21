# CLAUDE.md — zoozooland 저장소 작업 규칙

이 파일은 Claude가 세션을 시작할 때 가장 먼저 읽는 문서입니다.
작업 전 반드시 `WORKLOG.md`의 "다음 할 일"과 `docs/ROADMAP.md`의 현재 단계를 확인하세요.

## 1. 이 저장소는 무엇인가

쥬쥬랜드(ZZL, 경기 고양시 덕양구 원당로458번길 7-42) 공식 홈페이지 **zoozoo.kr**과
쥬쥬랜드 운영 자동화가 한 저장소에 함께 들어 있습니다.

| 폴더/파일 | 역할 | 홈페이지 배포 영향 |
|---|---|---|
| `website-zzl/` | **실제 운영 중인 홈페이지** (index.html, dogam.html, css, js) | 배포됨 (사이트 루트) |
| `website/data/` | 홈페이지가 읽는 데이터 JSON (운영정보·상품·프로그램·공지·인스타 피드·GA 분석) | 배포됨 (`/data`) |
| `website/images/` | 홈페이지 이미지 | 배포됨 (`/images`) |
| `website/admin/`, `website/js/dashboard.js` | 관리자 대시보드 (GA 분석 표시) | 배포됨 (`/admin`) |
| `website/index.html`, `website/css`, `website/js/main.js` | **구버전 사이트 — 배포되지 않음.** 수정하지 말 것 | 없음 |
| `guidemap/` | 안내지도 편집용 로컬 Node 서버 (배포 안 됨) | 없음 |
| `instagram/`, `reels/` | 인스타그램 피드 수집·게시, 릴스 자동화 | 없음 |
| `report.py`, `validate_data.py`, `dashboard/` | 실적 텔레그램 리포트 (하루 2회) | 없음 |
| `marketing_analytics_etl.py` | GA4 등 분석 데이터 → `website/data/analytics.json` | 데이터만 |

**홈페이지 작업 범위는 `website-zzl/`, `website/data/`, `website/images/`, `website/admin/`, `.github/workflows/deploy-website.yml` 입니다.**
리포트·인스타·릴스 자동화 파일은 사용자가 명시적으로 요청하지 않는 한 건드리지 않습니다.

## 2. 배포 구조

- `main` 브랜치에 `website/**`, `website-zzl/**` 변경이 push되면 GitHub Actions(`deploy-website.yml`)가 GitHub Pages로 자동 배포 → **main에 올리는 순간 실서비스 반영**.
- 배포 과정: `website-zzl/` → `deploy/` 복사, `website/data`·`images`·`admin` 복사, `website-zzl/build.py`가 JSON 내용을 `index.html`의 `<!-- ssg:이름 -->` 마커 사이에 정적으로 주입(SEO용), CNAME `zoozoo.kr`.
- 자동화 봇이 `website/data/instagram_feed.json`, `analytics.json`을 수시로 커밋하므로, 작업 전 항상 `git pull` 할 것.

## 3. 작업 방식 (반드시 지킬 것)

1. **main에 직접 push 금지.** 브랜치(`design/winter-2026` 같은 이름)에서 작업 → PR → 사용자 확인 후 병합.
2. 수정 후 로컬 확인: 아래 "로컬 미리보기"로 데스크톱(1440px)·모바일(390px) 두 폭에서 화면을 확인하고, 가로 스크롤이 생기지 않는지(`document.documentElement.scrollWidth`가 화면 폭과 같은지) 확인.
3. `build.py`의 ssg 마커(`<!-- ssg:product -->` 등)는 지우거나 이름을 바꾸지 말 것. 바꿔야 하면 `build.py`도 같이 수정.
4. 운영 정보(요금·운영시간·프로그램·공지)는 HTML에 직접 쓰지 말고 `website/data/*.json`에서 관리.
5. 디자인 규칙은 `docs/DESIGN.md`를 따른다. 색상은 CSS 변수로만 쓰고 HTML에 hex 값을 직접 쓰지 않는다.
6. 세션을 끝낼 때 `WORKLOG.md`에 "한 일 / 다음 할 일"을 3~5줄로 추가한다.
7. 큰 이미지(1MB 이상)·PDF는 그대로 넣지 말고 웹용으로 줄여서 넣는다.
8. API 키·토큰·비밀번호는 저장소에 커밋하지 않는다 (이 저장소는 public).

## 4. 로컬 미리보기

```bash
rm -rf deploy && mkdir -p deploy/js
cp -r website-zzl/. deploy/ && cp -r website/data deploy/data && cp -r website/images deploy/images
cp -r website/admin deploy/admin && cp website/js/dashboard.js deploy/js/
python3 website-zzl/build.py
cd deploy && python3 -m http.server 8765   # http://localhost:8765
```
`deploy/`는 빌드 결과물이므로 커밋하지 않는다.

## 5. 사이트 정보 (변경 시 여기도 갱신)

- 운영: 매일 10:00–18:00, 월요일 휴무(공휴일인 월요일은 정상 운영)
- 대표전화 031-962-4500 / 단체 star0666@zoozoo.kr / 제휴 hwan9740@zoozoo.kr
- 예약: 네이버 예약 (URL은 `website/data/products.json`)
- 분석: GA4 `G-HF2XRXQE6X`, Microsoft Clarity
- 브랜드 언어: ZZL = "즐", 동물은 "쥬민". 카피는 "ZZL겨볼까?"처럼 ZZL 말장난을 살린다.
- 주 방문객: 아이 동반 가족 → 한국어 우선, 영어 장식 문구는 보조로만.

## 6. 담당자

홈페이지 관리는 최석환 이사가 단독 결정·처리한다. 변경 사항은 배포 후 직원에게 공지.
