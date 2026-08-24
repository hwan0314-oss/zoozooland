# 쥬쥬랜드 마케팅 분석 스택 구축 — 설계

## 배경

zoozoo.kr(website-zzl/, GitHub Pages 정적 배포)에는 방문 추적 코드가 전혀 없다. 네이버 소유확인 메타태그(`naver-site-verification`)만 존재하고, GA4·Search Console 연동 흔적은 없다. 즉 현재는 방문자 수, 유입 경로, 검색 키워드를 확인할 방법이 없는 상태다.

사용자는 계정을 하나도 만들어두지 않았고(로그인이 필요한 계정 생성·소유확인 단계는 Claude가 대신할 수 없음), "코드는 Claude가, 계정은 사장님이" 방식으로 진행하기로 합의했다.

## 목표

zoozoo.kr의 (1) 방문자 수, (2) 유입 경로, (3) 검색 키워드를 추적할 수 있는 무료 도구를 사이트에 연결한다.

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

1. Claude가 단계별 계정 생성 가이드 문서를 작성해 전달한다 (GA4, Search Console, 네이버 서치어드바이저, MS Clarity 각각의 가입/등록 절차).
2. 사용자가 각 플랫폼에서 계정을 만들고 Measurement ID(GA4), Project ID(Clarity)를 Claude에게 전달한다. Search Console과 네이버 서치어드바이저는 ID 전달 없이 등록만 하면 된다.
3. Claude가 받은 ID를 `index.html`, `dogam.html`의 `</head>` 직전에 실제 추적 스니펫으로 반영하고 커밋한다.
4. GitHub Actions가 자동 배포하면 데이터 수집이 시작된다.

## 데이터 확인 방법

통합 대시보드는 만들지 않는다. 각 플랫폼 자체 대시보드에서 확인한다:
- GA4: 실시간/보고서 메뉴에서 방문자 수·유입 경로
- Search Console: 검색 결과 실적 보고서에서 검색어별 노출·클릭
- 네이버 서치어드바이저: 웹마스터도구에서 유입 검색어
- Clarity: 히트맵·세션 녹화

**Why:** 지금은 데이터가 전혀 없는 상태라, 이 시점에 커스텀 통합 대시보드(API 연동 포함)를 만들면 빈 껍데기가 된다. 데이터가 쌓이고 통합 뷰의 필요성이 명확해지면 별도로 설계하는 것이 낫다.

## 비범위 (지금 하지 않는 것)

- Google Tag Manager 도입 (관리 편의성은 있지만 지금 규모에 비해 계정·개념이 하나 더 늘어나는 오버헤드)
- 네이버 프리미엄로그분석 (서치어드바이저 등록 이후 필요성이 확인되면 추가 검토)
- API 연동 커스텀 대시보드 (데이터 축적 후 별도 프로젝트로 재논의)
- Meta Pixel 등 광고 전용 픽셀 (광고 집행 계획이 생기면 별도 논의)
