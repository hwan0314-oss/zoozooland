# 쥬쥬랜드 마케팅 분석 스택 구축 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** zoozoo.kr에 GA4, Google Search Console, 네이버 서치어드바이저, Microsoft Clarity 4종의 무료 추적 도구를 연결해 방문자 수·유입 경로·검색 키워드·사이트 내 행동을 확인할 수 있게 한다.

**Architecture:** 정적 사이트(`website-zzl/index.html`, `website-zzl/dogam.html`)의 `</head>` 직전에 각 도구의 표준 JS 스니펫을 삽입한다. Search Console과 네이버 서치어드바이저는 코드 변경 없이 계정 등록만으로 연동된다. GA4와 Clarity는 콘솔에서 발급받는 ID가 필요해, 사용자가 계정을 만들고 ID를 전달할 때까지 해당 작업은 대기 상태(Blocked)로 둔다.

**Tech Stack:** 순수 HTML — 빌드 도구나 패키지 매니저 불필요. `website-zzl/build.py`(SSG)는 `index.html`의 `<!-- ssg:name -->` 마커만 치환하므로 `</head>` 근처 코드는 그대로 통과된다.

## Global Constraints

- 스니펫 삽입 대상은 `website-zzl/index.html`, `website-zzl/dogam.html` 두 파일만. `website-zzl/map.html`은 즉시 리다이렉트 페이지라 제외 (설계 문서 참조).
- GA4 Measurement ID와 Clarity Project ID는 사용자가 각 콘솔에서 직접 생성해 전달해야 하며, Claude가 대신 발급할 수 없다.
- 실제 ID를 받기 전에는 플레이스홀더(`G-XXXXXXXXXX`, `XXXXXXXXXX`)가 들어간 코드를 **커밋하지 않는다** — 잘못된 ID로 배포되면 이후 실제 값으로 교체·재배포해야 하는 번거로움이 생기므로, ID 확보 전까지 Task 2·3은 대기.
- 커밋 시 `website-zzl/...` 파일만 개별 지정해서 add (레포 관례, [[project_website]] 참조).

---

### Task 1: 계정 생성 및 등록 가이드 문서 작성

**Files:**
- Create: `docs/marketing-analytics-setup-guide.md`

**Interfaces:**
- Produces: 사용자가 따라할 4단계 가입/등록 절차 문서. Task 2·3이 필요로 하는 `GA4_MEASUREMENT_ID`, `CLARITY_PROJECT_ID` 두 값을 사용자가 이 문서를 보고 발급받아 Claude에게 전달하게 된다.

- [ ] **Step 1: 가이드 문서 작성**

`docs/marketing-analytics-setup-guide.md` 파일을 아래 내용으로 생성한다.

```markdown
# zoozoo.kr 마케팅 분석 도구 설정 가이드

아래 4가지를 순서대로 진행해주세요. ①②는 완료 후 값을 Claude에게 전달해야 코드에 반영됩니다. ③④는 등록만 하면 끝입니다.

## ① Google Analytics 4 (GA4) — 방문자 수 · 유입 경로

1. https://analytics.google.com 접속 → Google 계정으로 로그인
2. 왼쪽 아래 "관리" → "계정 만들기" → 계정 이름: `쥬쥬랜드` 입력 후 다음
3. 속성 만들기 → 속성 이름: `zoozoo.kr`, 시간대: 대한민국, 통화: KRW
4. 업종 카테고리: "여가/레저" 선택, 비즈니스 규모 아무거나 선택 후 다음
5. 데이터 스트림 → "웹" 선택 → 웹사이트 URL: `https://zoozoo.kr`, 스트림 이름: `zoozoo.kr` 입력 후 "스트림 만들기"
6. 생성된 화면에 "측정 ID"가 `G-`로 시작하는 문자열로 표시됩니다 (예: `G-ABC1234XYZ`)
7. **이 측정 ID를 복사해서 Claude에게 전달해주세요.**

## ② Microsoft Clarity — 방문자 클릭·스크롤 히트맵/녹화

1. https://clarity.microsoft.com 접속 → Microsoft 계정(또는 Google 계정)으로 로그인
2. "New project" 클릭
3. Name: `zoozoo.kr`, Website URL: `https://zoozoo.kr`, Category: `Entertainment & Culture` 선택 후 "Add new project"
4. 프로젝트 생성 후 나오는 설치 코드 안에서 10자리 영숫자 Project ID를 확인합니다 (설치 코드 중 `"clarity", "script", "여기부분"` 위치의 문자열)
5. **이 Project ID를 복사해서 Claude에게 전달해주세요.**

## ③ Google Search Console — 구글 검색어별 유입 데이터

1. ①에서 GA4 설정을 먼저 완료해야 합니다 (Search Console이 GA4 계정으로 소유확인을 대신하기 때문)
2. https://search.google.com/search-console 접속 → 같은 Google 계정으로 로그인
3. "속성 추가" → URL 접두어 방식으로 `https://zoozoo.kr` 입력
4. 소유권 확인 화면에서 "Google Analytics" 방식을 선택 (①에서 만든 GA4 속성이 같은 계정에 있으면 자동으로 확인됩니다)
5. 확인 완료되면 별도로 전달할 값 없음. 며칠 후 "실적" 메뉴에서 검색어별 데이터가 쌓이기 시작합니다.

## ④ 네이버 서치어드바이저 — 네이버 검색어별 유입 데이터

1. https://searchadvisor.naver.com 접속 → 네이버 계정으로 로그인
2. "웹마스터 도구" → "사이트 등록" → `https://zoozoo.kr` 입력
3. 소유확인 방식 중 "HTML 태그" 선택 — zoozoo.kr에는 이미 소유확인 메타태그가 심어져 있어서 (`naver-site-verification`) 바로 확인이 완료될 가능성이 높습니다. 만약 실패하면 확인창에 뜨는 메타태그 값을 Claude에게 전달해주세요.
4. 등록 완료 후 "요약정보" → "검색 유입 분석"에서 며칠 뒤부터 검색어별 유입 데이터를 볼 수 있습니다.

---

①②를 완료하시면 측정 ID 두 개(GA4 `G-...`, Clarity 10자리)를 Claude에게 전달해주세요. 코드에 반영해서 배포하겠습니다.
```

- [ ] **Step 2: 문서가 올바르게 생성됐는지 확인**

Run: `cat "docs/marketing-analytics-setup-guide.md" | grep -c "^## "`
Expected: `4` (①~④ 4개 섹션이 모두 존재)

- [ ] **Step 3: Commit**

```bash
git add docs/marketing-analytics-setup-guide.md
git commit -m "docs: 마케팅 분석 도구 4종 계정 생성 가이드 추가"
```

---

### Task 2: GA4 추적 스니펫 삽입 (Blocked — GA4_MEASUREMENT_ID 필요)

**선행 조건:** 사용자가 Task 1의 ①을 완료하고 `G-`로 시작하는 Measurement ID를 채팅으로 전달했어야 한다. 전달받기 전에는 이 태스크를 시작하지 않는다.

**Files:**
- Modify: `website-zzl/index.html:55` (`</head>` 직전)
- Modify: `website-zzl/dogam.html:257` (`</head>` 직전)

**Interfaces:**
- Consumes: 사용자로부터 전달받은 실제 GA4 Measurement ID (예: `G-ABC1234XYZ`)

- [ ] **Step 1: index.html에 GA4 스니펫 삽입**

`website-zzl/index.html`의 55번째 줄(`</head>`) 바로 앞에 아래 블록을 삽입한다. `G-XXXXXXXXXX`는 사용자가 전달한 실제 Measurement ID로 정확히 치환한다.

```html
  <!-- Google Analytics (GA4) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
  </script>
</head>
```

(기존 `</head>` 한 줄을 이 블록으로 교체하는 형태 — 즉 스니펫 4줄을 추가하고 `</head>`는 그대로 마지막에 유지)

- [ ] **Step 2: dogam.html에 동일한 스니펫 삽입**

`website-zzl/dogam.html`의 257번째 줄(`</head>`) 바로 앞에 Step 1과 동일한 블록(같은 Measurement ID)을 삽입한다.

- [ ] **Step 3: 삽입 확인**

Run: `grep -c "gtag/js?id=G-" website-zzl/index.html website-zzl/dogam.html`
Expected: 두 파일 모두 `1` (플레이스홀더가 아닌 실제 ID가 두 파일에 정확히 1번씩 들어갔는지 확인)

Run: `grep "G-XXXXXXXXXX" website-zzl/index.html website-zzl/dogam.html`
Expected: 아무 결과도 없어야 함 (플레이스홀더가 실제 값으로 전부 치환됐는지 확인)

- [ ] **Step 4: Commit**

```bash
git add website-zzl/index.html website-zzl/dogam.html
git commit -m "feat: GA4 방문자 추적 스니펫 연결"
```

---

### Task 3: Microsoft Clarity 추적 스니펫 삽입 (Blocked — CLARITY_PROJECT_ID 필요)

**선행 조건:** 사용자가 Task 1의 ②를 완료하고 10자리 Clarity Project ID를 채팅으로 전달했어야 한다.

**Files:**
- Modify: `website-zzl/index.html` (Task 2 완료 후 위치한 `</head>` 직전)
- Modify: `website-zzl/dogam.html` (Task 2 완료 후 위치한 `</head>` 직전)

**Interfaces:**
- Consumes: 사용자로부터 전달받은 실제 Clarity Project ID (예: `abc123defg`)

- [ ] **Step 1: index.html에 Clarity 스니펫 삽입**

`website-zzl/index.html`의 `</head>` 직전(Task 2에서 넣은 GA4 스니펫 바로 다음)에 아래 블록을 삽입한다. `XXXXXXXXXX`는 실제 Project ID로 치환한다.

```html
  <!-- Microsoft Clarity -->
  <script type="text/javascript">
    (function(c,l,a,r,i,t,y){
        c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
        t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i+"?ref=bwt";
        y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
    })(window, document, "clarity", "script", "XXXXXXXXXX");
  </script>
</head>
```

- [ ] **Step 2: dogam.html에 동일한 스니펫 삽입**

`website-zzl/dogam.html`의 `</head>` 직전(Task 2의 GA4 스니펫 다음)에 Step 1과 동일한 블록(같은 Project ID)을 삽입한다.

- [ ] **Step 3: 삽입 확인**

Run: `grep -c 'clarity.ms/tag' website-zzl/index.html website-zzl/dogam.html`
Expected: 두 파일 모두 `1`

Run: `grep '"script", "XXXXXXXXXX"' website-zzl/index.html website-zzl/dogam.html`
Expected: 아무 결과도 없어야 함 (플레이스홀더 미치환 여부 확인)

- [ ] **Step 4: Commit**

```bash
git add website-zzl/index.html website-zzl/dogam.html
git commit -m "feat: Microsoft Clarity 세션 녹화/히트맵 스니펫 연결"
```

---

### Task 4: 배포 후 데이터 수신 검증

**선행 조건:** Task 2, 3 커밋이 push되어 GitHub Actions 배포가 완료되어 있어야 한다 (`.github/workflows/deploy-website.yml`, main 브랜치 push 시 자동 실행).

**Files:** 없음 (검증 전용 태스크, 코드 변경 없음)

**Interfaces:**
- Consumes: Task 2·3에서 배포된 실제 GA4/Clarity 스니펫

- [ ] **Step 1: 배포 완료 확인**

Run: `curl -s https://zoozoo.kr | grep -c "gtag/js"`
Expected: `1` (라이브 사이트에 GA4 스니펫이 실제로 반영됐는지 확인)

- [ ] **Step 2: GA4 실시간 리포트로 수신 확인**

zoozoo.kr을 브라우저로 직접 방문한 뒤, GA4 콘솔(analytics.google.com) → 보고서 → 실시간 메뉴에서 활성 사용자 1명이 잡히는지 확인한다. (사용자가 직접 확인 — Claude가 GA4 콘솔에 로그인할 수 없음)

- [ ] **Step 3: Clarity 대시보드로 세션 수신 확인**

같은 방문 후 clarity.microsoft.com 프로젝트 대시보드에서 세션이 기록되는지 확인한다 (수 분 정도 지연될 수 있음). (사용자가 직접 확인)

- [ ] **Step 4: Search Console / 네이버 서치어드바이저 등록 상태 확인**

Search Console과 네이버 서치어드바이저는 검색어 데이터가 실제로 쌓이기까지 수일~2주가 걸린다. 이 단계에서는 "등록 및 소유확인 완료" 상태인지만 사용자가 각 콘솔에서 확인한다.

- [ ] **Step 5: 결과를 Claude에게 알리고 마무리**

사용자가 위 확인 결과를 Claude에게 전달하면, 문제가 있을 경우(예: GA4에 데이터가 안 잡힘) 스니펫 위치나 ID 오타를 함께 디버깅한다.
