# 쥬쥬랜드 마케팅 분석 스택 구축 — 설계

## 배경

zoozoo.kr(website-zzl/, GitHub Pages 정적 배포)에는 방문 추적 코드가 전혀 없다. 네이버 소유확인 메타태그(`naver-site-verification`)만 존재하고, GA4·Search Console 연동 흔적은 없다. 즉 현재는 방문자 수, 유입 경로, 검색 키워드를 확인할 방법이 없는 상태다.

사용자는 계정을 하나도 만들어두지 않았고(로그인이 필요한 계정 생성·소유확인 단계는 Claude가 대신할 수 없음), "코드는 Claude가, 계정은 사장님이" 방식으로 진행하기로 합의했다.

## 목표

zoozoo.kr의 (1) 방문자 수, (2) 유입 경로, (3) 검색 키워드를 추적할 수 있는 무료 도구를 사이트에 연결하고, (4) 그중 프로그램으로 수집 가능한 지표(GA4·Search Console·Clarity)를 관리자 패널의 통합 대시보드 한 화면에서 볼 수 있게 한다.

## 구성 도구 및 역할 분담

| 도구 | 얻는 데이터 | 코드 변경 | 사용자가 할 일 |
|---|---|---|---|
| GA4 (Google Analytics 4) | 방문자 수, 유입 경로(직접/네이버/구글/인스타그램 등), 인기 페이지, 체류시간 | `index.html`, `dogam.html`에 gtag.js 스니펫 삽입 | GA4 계정 생성 → Measurement ID(`G-XXXXXXX`)를 Claude에게 전달 |
| Google Search Console | 구글 검색어별 노출수·클릭수·평균순위 | 없음 (GA4 계정 연동으로 소유확인 대체) | Search Console에서 "기존 Google Analytics 계정 사용"으로 zoozoo.kr 등록 |
| 네이버 서치어드바이저 | 네이버 검색어별 유입 데이터 | 없음 (기존 메타태그로 이미 소유확인 가능한 상태) | https://searchadvisor.naver.com 로그인 → zoozoo.kr 사이트 등록 확인 |
| Microsoft Clarity | 방문자가 사이트 내에서 클릭·스크롤하는 위치 (히트맵, 세션 녹화) | `index.html`, `dogam.html`에 Clarity 스니펫 삽입 | clarity.microsoft.com에서 프로젝트 생성 → Project ID를 Claude에게 전달 |

## 적용 범위

- **포함:** `website-zzl/index.html`, `website-zzl/dogam.html` — 실제 방문자가 머무는 페이지.
- **제외:** `website-zzl/map.html` — `<meta http-equiv="refresh" content="0">` + 즉시 JS 리다이렉트로 dogam.html로 넘어가는 페이지라, 추적 스크립트가 네트워크 요청을 완료할 시간이 부족함.

## 작업 흐름

1. Claude가 단계별 계정 생성 가이드 문서를 작성해 전달한다 (GA4, Search Console, 네이버 서치어드바이저, MS Clarity 가입/등록 + 대시보드용 서비스 계정·API 토큰 발급 절차).
2. 사용자가 각 플랫폼에서 계정을 만들고 Measurement ID(GA4), Project ID(Clarity)를 Claude에게 전달한다. Search Console과 네이버 서치어드바이저는 ID 전달 없이 등록만 하면 된다.
3. Claude가 받은 ID를 `index.html`, `dogam.html`의 `</head>` 직전에 실제 추적 스니펫으로 반영하고 커밋한다.
4. GitHub Actions가 자동 배포하면 데이터 수집이 시작된다.
5. 사용자가 GCP 서비스 계정 키(JSON)와 Clarity API 토큰을 발급해 Claude에게 전달하면, Claude가 GitHub 저장소 Secrets에 등록 방법을 안내하고 ETL 워크플로우·대시보드 페이지 코드를 커밋한다.
6. 매일 1회 ETL 워크플로우가 자동 실행되며 며칠 뒤부터 대시보드에 추이 데이터가 쌓이기 시작한다.

## 데이터 확인 방법

두 가지 경로를 병행한다.

1. **각 플랫폼 자체 대시보드** — 상세 분석이 필요할 때 (GA4 실시간/보고서, Search Console 실적 보고서, 네이버 서치어드바이저 웹마스터도구, Clarity 히트맵·세션 녹화).
2. **커스텀 통합 대시보드** — 기존 관리자 패널(`website/admin/`) 안에 새 페이지를 추가해, GA4·Search Console·Clarity 세 곳의 핵심 지표를 한 화면에서 한눈에 본다. 매일 자동 수집된 스냅샷을 보여준다 (아래 "커스텀 통합 대시보드" 절 참조).

## 커스텀 통합 대시보드

### API 조사 결과 (2026-08-25 확인)

| 플랫폼 | 데이터 API 존재 여부 | 인증 방식 | 비고 |
|---|---|---|---|
| GA4 | 있음 — Google Analytics Data API (`analyticsdata.googleapis.com`, `runReport`) | 서비스 계정 (GA4 속성에 "뷰어"로 등록) | 기간 지정 조회 가능, 제한 넉넉함 |
| Google Search Console | 있음 — Search Console API (`searchanalytics.query`) | 서비스 계정 (속성에 사용자로 등록) | 기간 지정 조회 가능 |
| Microsoft Clarity | 있음 — Clarity Data Export API (`clarity.ms/export-data/api/v1/project-live-insights`) | 프로젝트 API 토큰 | **하루 최대 10회 호출, 최근 1~3일치 데이터만 제공** (과거 데이터 누적 불가 — 매일 스냅샷을 직접 저장해야 이력이 쌓임) |
| 네이버 서치어드바이저 | **없음** — 공개 API 미제공, 웹 콘솔 전용 | — | 자동 연동 불가. 대시보드에는 "네이버 서치어드바이저 바로가기" 링크 카드만 넣고, 실제 검색어 데이터는 사장님이 콘솔에서 직접 확인 |

**Why:** 대시보드를 만들기 전에 각 플랫폼이 실제로 프로그램으로 데이터를 꺼낼 수 있는지 확인이 필요했다. 네이버는 API가 없다는 게 확인된 하드 제약이라, "4개 도구 통합 대시보드"가 아니라 "3개 자동 + 네이버는 링크 연결"이 현실적인 목표다.

### 아키텍처

zoozoo.kr은 GitHub Pages 정적 배포라 상시 서버가 없다. 기존에도 이 프로젝트는 GitHub Actions를 서버 대신 쓰고 있으므로(배포 워크플로우), 같은 패턴을 재사용한다.

1. **수집(ETL):** 매일 1회 실행되는 새 GitHub Actions 스케줄 워크플로우가 Python 스크립트를 실행해 GA4 Data API, Search Console API, Clarity Data Export API를 호출하고 결과를 `website/data/analytics.json`(최신 스냅샷 + 최근 30일 이력 배열)에 기록 후 커밋한다.
2. **인증 정보:** GA4/Search Console용 서비스 계정 키(JSON)와 Clarity API 토큰은 GitHub 저장소 Secrets에 저장한다 (`GA4_SERVICE_ACCOUNT_JSON`, `GA4_PROPERTY_ID`, `GSC_SERVICE_ACCOUNT_JSON`, `CLARITY_API_TOKEN`). 코드나 저장소에 평문으로 남기지 않는다.
3. **표시:** 기존 관리자 패널(`website/admin/`, PIN 로그인 방식 재사용)에 새 페이지 `website/admin/dashboard.html`을 추가해 `website/data/analytics.json`을 읽어 지표 카드 + 추이 차트로 보여준다. 공개 사이트가 아니라 관리자만 접근하는 페이지이므로 `robots: noindex,nofollow` 유지.
4. **배포:** 기존 배포 워크플로우가 이미 `website/data/`와 `website/admin/`을 통째로 `deploy/`에 복사하므로, 추가 배포 설정 변경은 필요 없다.

### 적용 제외

- 네이버 서치어드바이저 데이터 자동 수집 (API 없음 — 위 표 참조)
- 실시간 갱신 (스냅샷은 하루 1회. 실시간이 필요하면 각 플랫폼 자체 대시보드의 "실시간" 메뉴를 이용)

## 비범위 (지금 하지 않는 것)

- Google Tag Manager 도입 (관리 편의성은 있지만 지금 규모에 비해 계정·개념이 하나 더 늘어나는 오버헤드)
- 네이버 프리미엄로그분석 (서치어드바이저 등록 이후 필요성이 확인되면 추가 검토)
- Meta Pixel 등 광고 전용 픽셀 (광고 집행 계획이 생기면 별도 논의)
- 네이버 검색어 데이터의 프로그램적 수집 (공개 API 없음이 확인됨 — 콘솔에서 수동 확인)
