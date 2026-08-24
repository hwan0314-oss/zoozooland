# 쥬쥬랜드 마케팅 분석 스택 구축 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** zoozoo.kr에 GA4, Google Search Console, 네이버 서치어드바이저, Microsoft Clarity 4종의 무료 추적 도구를 연결해 방문자 수·유입 경로·검색 키워드·사이트 내 행동을 확인할 수 있게 하고, 그중 API로 자동 수집 가능한 GA4·Search Console·Clarity 데이터를 관리자 패널의 통합 대시보드 한 화면에서 볼 수 있게 한다.

**Architecture:** 정적 사이트(`website-zzl/index.html`, `website-zzl/dogam.html`)의 `</head>` 직전에 각 도구의 표준 JS 스니펫을 삽입한다. Search Console과 네이버 서치어드바이저는 코드 변경 없이 계정 등록만으로 연동된다. GA4와 Clarity는 콘솔에서 발급받는 ID가 필요해, 사용자가 계정을 만들고 ID를 전달할 때까지 해당 작업은 대기 상태(Blocked)로 둔다. 대시보드는 상시 서버가 없는 GitHub Pages 구조에 맞춰, 매일 1회 실행되는 GitHub Actions 워크플로우(레포에 이미 있는 `daily_report.yml` 패턴 재사용)가 Python ETL 스크립트로 GA4 Data API·Search Console API·Clarity Data Export API를 호출해 `website/data/analytics.json`에 스냅샷을 기록하고, 기존 관리자 패널(`website/admin/`, PIN 게이트 재사용)에 추가한 읽기 전용 페이지가 이 JSON을 읽어 차트로 보여준다. 네이버 서치어드바이저는 공개 API가 없어 대시보드에는 링크만 연결한다.

**Tech Stack:** 순수 HTML/CSS/JS(빌드 도구·패키지 매니저 불필요, 차트는 외부 라이브러리 없이 인라인 SVG로 직접 렌더링) + Python 3.11(ETL, `requests`+`google-auth`만 사용) + GitHub Actions(스케줄 워크플로우). `website-zzl/build.py`(SSG)는 `index.html`의 `<!-- ssg:name -->` 마커만 치환하므로 `</head>` 근처 코드는 그대로 통과된다.

## Global Constraints

- 스니펫 삽입 대상은 `website-zzl/index.html`, `website-zzl/dogam.html` 두 파일만. `website-zzl/map.html`은 즉시 리다이렉트 페이지라 제외 (설계 문서 참조).
- GA4 Measurement ID와 Clarity Project ID는 사용자가 각 콘솔에서 직접 생성해 전달해야 하며, Claude가 대신 발급할 수 없다.
- 실제 ID를 받기 전에는 플레이스홀더(`G-XXXXXXXXXX`, `XXXXXXXXXX`)가 들어간 코드를 **커밋하지 않는다** — 잘못된 ID로 배포되면 이후 실제 값으로 교체·재배포해야 하는 번거로움이 생기므로, ID 확보 전까지 Task 2·3은 대기.
- 대시보드용 서비스 계정 키(JSON)와 Clarity API 토큰 등 시크릿은 GitHub 저장소 Secrets에만 저장하고, 코드나 커밋에 평문으로 남기지 않는다 (Task 8).
- 대시보드용 GitHub Actions 워크플로우와 시크릿은 레포에 이미 있는 무관한 `daily_report.yml`(주식·날씨 개인 리포트, 별도 프로젝트)과 이름·시크릿이 겹치지 않게 완전히 분리한다 — 같은 `requirements.txt`를 공유하지 않고 워크플로우 안에서 자체적으로 `pip install`한다.
- 커밋 시 `website-zzl/...`, `website/...` 등 파일만 개별 지정해서 add (레포 관례, [[project_website]] 참조).

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

---

### Task 5: 마케팅 분석 ETL 스크립트 (GA4 + Search Console + Clarity)

**선행 조건:** 실제 실행에는 사용자가 전달한 서비스 계정 JSON, GA4 속성 ID, Clarity API 토큰이 필요하지만, 스크립트 코드 자체는 지금 작성할 수 있다 (레포 관례상 `report.py`, `validate_data.py` 등 자동화 스크립트가 레포 루트에 있으므로 같은 위치를 따른다). GitHub Secrets 미설정 상태에서 워크플로우가 실행되면 이 태스크의 방어 코드가 각 플랫폼 실패를 개별적으로 처리해 조용히 건너뛴다.

**Files:**
- Create: `marketing_analytics_etl.py`
- Modify: 없음 (기존 `requirements.txt`는 daily_report.yml 등 무관한 워크플로우와 공유되므로 건드리지 않고, 이 태스크 전용 워크플로우 안에서 `pip install`로 필요한 패키지를 직접 설치한다 — Task 6 참조)

**Interfaces:**
- Consumes: 환경변수 `GA4_SERVICE_ACCOUNT_JSON`(서비스 계정 키 JSON 원문), `GA4_PROPERTY_ID`(숫자), `GSC_SITE_URL`(예: `https://zoozoo.kr/`), `CLARITY_PROJECT_ID`, `CLARITY_API_TOKEN`
- Produces: `website/data/analytics.json` — 아래 스키마로 파일 생성/갱신

```json
{
  "updated_at": "2026-09-01T00:10:00+09:00",
  "ga4": {
    "daily": [{"date": "2026-08-25", "activeUsers": 12}],
    "sources": [{"source": "naver / organic", "sessions": 8}]
  },
  "gsc": {
    "top_queries": [{"query": "고양 동물원", "clicks": 5, "impressions": 120, "position": 8.2}]
  },
  "clarity": {
    "history": [{"date": "2026-08-25", "sessions": 10, "scrollDepth": 42.1, "engagementTime": 38.4}]
  },
  "errors": {}
}
```

- [ ] **Step 1: 스크립트 작성**

`marketing_analytics_etl.py`를 아래 내용으로 생성한다.

```python
#!/usr/bin/env python3
"""
zoozoo.kr 마케팅 분석 ETL — GA4 Data API, Search Console API, Clarity Data
Export API에서 데이터를 모아 website/data/analytics.json에 기록한다.
GitHub Actions에서 매일 1회 실행된다. 세 플랫폼 중 하나가 실패해도
나머지는 정상적으로 기록되도록 각각 독립적으로 처리한다.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

ROOT = Path(__file__).parent
OUT = ROOT / 'website' / 'data' / 'analytics.json'

KST = timezone(timedelta(hours=9))

GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly',
]


def load_existing():
    if OUT.exists():
        return json.loads(OUT.read_text('utf-8'))
    return {'ga4': {'daily': [], 'sources': []}, 'gsc': {'top_queries': []}, 'clarity': {'history': []}, 'errors': {}}


def google_credentials():
    info = json.loads(os.environ['GA4_SERVICE_ACCOUNT_JSON'])
    creds = service_account.Credentials.from_service_account_info(info, scopes=GOOGLE_SCOPES)
    creds.refresh(GoogleAuthRequest())
    return creds


def fetch_ga4(creds, property_id):
    headers = {'Authorization': f'Bearer {creds.token}', 'Content-Type': 'application/json'}
    base = f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport'

    daily_body = {
        'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
        'dimensions': [{'name': 'date'}],
        'metrics': [{'name': 'activeUsers'}],
        'orderBys': [{'dimension': {'dimensionName': 'date'}}],
    }
    daily_res = requests.post(base, headers=headers, json=daily_body, timeout=30)
    daily_res.raise_for_status()
    daily_rows = daily_res.json().get('rows', [])
    daily = [
        {
            'date': f"{r['dimensionValues'][0]['value'][0:4]}-{r['dimensionValues'][0]['value'][4:6]}-{r['dimensionValues'][0]['value'][6:8]}",
            'activeUsers': int(r['metricValues'][0]['value']),
        }
        for r in daily_rows
    ]

    sources_body = {
        'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
        'dimensions': [{'name': 'sessionSource'}],
        'metrics': [{'name': 'sessions'}],
        'orderBys': [{'metric': {'metricName': 'sessions'}, 'desc': True}],
        'limit': 5,
    }
    sources_res = requests.post(base, headers=headers, json=sources_body, timeout=30)
    sources_res.raise_for_status()
    sources_rows = sources_res.json().get('rows', [])
    sources = [
        {'source': r['dimensionValues'][0]['value'], 'sessions': int(r['metricValues'][0]['value'])}
        for r in sources_rows
    ]

    return {'daily': daily, 'sources': sources}


def fetch_gsc(creds, site_url):
    headers = {'Authorization': f'Bearer {creds.token}', 'Content-Type': 'application/json'}
    from urllib.parse import quote
    end = datetime.now(KST).date() - timedelta(days=3)  # GSC 데이터는 최근 2~3일 지연됨
    start = end - timedelta(days=28)
    url = f'https://www.googleapis.com/webmasters/v3/sites/{quote(site_url, safe="")}/searchAnalytics/query'
    body = {
        'startDate': start.isoformat(),
        'endDate': end.isoformat(),
        'dimensions': ['query'],
        'rowLimit': 10,
    }
    res = requests.post(url, headers=headers, json=body, timeout=30)
    res.raise_for_status()
    rows = res.json().get('rows', [])
    top_queries = [
        {
            'query': r['keys'][0],
            'clicks': int(r['clicks']),
            'impressions': int(r['impressions']),
            'position': round(r['position'], 1),
        }
        for r in rows
    ]
    return {'top_queries': top_queries}


def fetch_clarity(project_id, token):
    headers = {'Authorization': f'Bearer {token}'}
    url = 'https://www.clarity.ms/export-data/api/v1/project-live-insights'
    res = requests.get(url, headers=headers, params={'numOfDays': 1}, timeout=30)
    res.raise_for_status()
    metrics = res.json()

    def find_metric(name):
        for m in metrics:
            if m.get('metricName') == name:
                return m.get('information', [{}])[0]
        return {}

    traffic = find_metric('Traffic')
    scroll = find_metric('ScrollDepth')
    engagement = find_metric('EngagementTime')

    return {
        'date': datetime.now(KST).date().isoformat(),
        'sessions': int(traffic.get('totalSessionCount', 0) or 0),
        'scrollDepth': float(scroll.get('averageScrollDepth', 0) or 0),
        'engagementTime': float(engagement.get('averageEngagementTime', 0) or 0),
    }


def merge_clarity_history(existing_history, today_snapshot):
    history = [h for h in existing_history if h['date'] != today_snapshot['date']]
    history.append(today_snapshot)
    history.sort(key=lambda h: h['date'])
    return history[-30:]


def main():
    data = load_existing()
    errors = {}

    try:
        creds = google_credentials()
    except Exception as e:
        errors['google_auth'] = str(e)
        creds = None

    if creds:
        try:
            data['ga4'] = fetch_ga4(creds, os.environ['GA4_PROPERTY_ID'])
        except Exception as e:
            errors['ga4'] = str(e)

        try:
            data['gsc'] = fetch_gsc(creds, os.environ['GSC_SITE_URL'])
        except Exception as e:
            errors['gsc'] = str(e)

    try:
        snapshot = fetch_clarity(os.environ['CLARITY_PROJECT_ID'], os.environ['CLARITY_API_TOKEN'])
        data.setdefault('clarity', {'history': []})
        data['clarity']['history'] = merge_clarity_history(data['clarity'].get('history', []), snapshot)
    except Exception as e:
        errors['clarity'] = str(e)

    data['errors'] = errors
    data['updated_at'] = datetime.now(KST).isoformat()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
    print(f'analytics.json 갱신 완료 → {OUT} (오류: {errors or "없음"})')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 구문 검증**

Run: `python3 -m py_compile marketing_analytics_etl.py`
Expected: 오류 없이 종료 (exit code 0)

- [ ] **Step 3: 필수 환경변수 누락 시 정상적으로 오류를 기록하는지 확인**

Run: `python3 marketing_analytics_etl.py`
Expected: `website/data/analytics.json`이 생성되고, `errors` 키에 `google_auth`(또는 `clarity`) 관련 메시지가 담김 — 환경변수가 없어도 스크립트 자체는 크래시하지 않고 종료되어야 한다. 확인 후 `git checkout -- website/data/analytics.json`으로 테스트 산출물은 되돌린다 (실제 데이터가 아니므로 커밋하지 않음).

- [ ] **Step 4: Commit**

```bash
git add marketing_analytics_etl.py
git commit -m "feat: GA4/Search Console/Clarity 마케팅 분석 ETL 스크립트 추가"
```

---

### Task 6: ETL GitHub Actions 스케줄 워크플로우

**선행 조건:** Task 5 완료.

**Files:**
- Create: `.github/workflows/marketing-analytics-etl.yml`

**Interfaces:**
- Consumes: `marketing_analytics_etl.py` (Task 5), GitHub Secrets `GA4_SERVICE_ACCOUNT_JSON`, `GA4_PROPERTY_ID`, `GSC_SITE_URL`, `CLARITY_PROJECT_ID`, `CLARITY_API_TOKEN` (사용자가 ⑤~⑦ 완료 후 값을 전달하면 Claude 또는 사용자가 등록)
- Produces: 매일 커밋되는 `website/data/analytics.json` → 기존 `deploy-website.yml`이 `website/data`를 통째로 복사하므로 자동 배포됨

- [ ] **Step 1: 워크플로우 파일 작성**

`.github/workflows/marketing-analytics-etl.yml`을 아래 내용으로 생성한다. `daily_report.yml`과 이름·시크릿이 겹치지 않도록 별도 워크플로우로 분리한다.

```yaml
name: 📊 Marketing Analytics ETL (zoozoo.kr)

on:
  schedule:
    - cron: '10 15 * * *'  # 매일 00:10 KST (UTC 15:10)
  workflow_dispatch:

jobs:
  etl:
    runs-on: ubuntu-22.04
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests google-auth

      - name: Run ETL
        env:
          GA4_SERVICE_ACCOUNT_JSON: ${{ secrets.GA4_SERVICE_ACCOUNT_JSON }}
          GA4_PROPERTY_ID: ${{ secrets.GA4_PROPERTY_ID }}
          GSC_SITE_URL: ${{ secrets.GSC_SITE_URL }}
          CLARITY_PROJECT_ID: ${{ secrets.CLARITY_PROJECT_ID }}
          CLARITY_API_TOKEN: ${{ secrets.CLARITY_API_TOKEN }}
        run: python marketing_analytics_etl.py

      - name: Commit analytics data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add website/data/analytics.json
          git diff --cached --quiet || git commit -m "chore: zoozoo.kr 마케팅 분석 데이터 갱신 $(date -u -d '+9 hours' +'%Y-%m-%d %H:%M KST')"
          git push
```

- [ ] **Step 2: YAML 문법 검증**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/marketing-analytics-etl.yml', encoding='utf-8'))"`
Expected: 오류 없이 종료 (`PyYAML`이 없으면 `pip install pyyaml` 먼저 실행)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/marketing-analytics-etl.yml
git commit -m "ci: 마케팅 분석 ETL 매일 자동 실행 워크플로우 추가"
```

---

### Task 7: 관리자 대시보드 페이지

**선행 조건:** Task 5, 6 완료. 실데이터는 없어도 되지만(빈 상태 UI로 대체), 스키마는 Task 5의 `analytics.json` 구조를 그대로 따라야 한다.

**Files:**
- Create: `website/admin/dashboard.html`
- Create: `website/js/dashboard.js`

**Interfaces:**
- Consumes: `../data/analytics.json` (Task 5 스키마), 기존 `ADMIN_PIN = 'zoozoo4500'` 상수 (website/js/admin.js:157와 동일한 값 — 로그인 화면 재사용 없이 같은 PIN만 재사용하는 경량 게이트)
- Produces: 없음 (읽기 전용 페이지)

- [ ] **Step 1: dashboard.html 작성**

`website/admin/dashboard.html`을 아래 내용으로 생성한다. 기존 `website/admin/index.html`의 라이트 테마 톤(녹색 `--g700` 계열, Noto Sans KR)을 그대로 따르고, 차트 색상만 dataviz 스킬의 검증된 팔레트(`references/palette.md`)를 사용한다.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>쥬쥬랜드 마케팅 대시보드</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --g700: #145a2e; --g600: #1d7a40; --g100: #e8f5ed; --g50: #f0f9f3;
      --n900: #111827; --n700: #374151; --n500: #6b7280; --n300: #d1d5db;
      --n200: #e5e7eb; --n100: #f3f4f6; --n50: #f9fafb; --white: #ffffff;
      --ff: 'Noto Sans KR', sans-serif; --r: 12px; --sh: 0 4px 16px rgba(0,0,0,.08);
      --surface-1: #fcfcfb; --text-secondary: #52514e; --text-muted: #898781;
      --series-1: #2a78d6; --grid: #e1e0d9; --baseline: #c3c2b7;
    }
    html, body { height: 100%; }
    body { font-family: var(--ff); background: var(--n50); color: var(--n900); line-height: 1.6; }
    #pinScreen { position: fixed; inset: 0; background: linear-gradient(145deg, #062318 0%, #1d7a40 100%);
      display: flex; align-items: center; justify-content: center; z-index: 999; }
    #pinScreen.hidden { display: none; }
    .pin-box { background: var(--white); border-radius: 24px; padding: 48px 40px; width: 100%; max-width: 380px; box-shadow: 0 24px 64px rgba(0,0,0,.25); }
    .pin-box h1 { font-size: 22px; color: var(--g700); margin-bottom: 24px; }
    .pin-input { width: 100%; border: 1.5px solid var(--n300); border-radius: var(--r); padding: 13px 16px;
      font-family: var(--ff); font-size: 14px; margin-bottom: 16px; outline: none; }
    .pin-input:focus { border-color: var(--g600); }
    .pin-btn { width: 100%; background: var(--g700); color: var(--white); border: none; border-radius: var(--r);
      padding: 13px; font-family: var(--ff); font-weight: 700; font-size: 14px; cursor: pointer; }
    .pin-error { color: #ef4444; font-size: 13px; margin-top: 10px; display: none; }
    .pin-error.show { display: block; }

    #dash { display: none; max-width: 1080px; margin: 0 auto; padding: 32px 20px 80px; }
    #dash.show { display: block; }
    .dash-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 24px; }
    .dash-head h1 { font-size: 24px; color: var(--g700); }
    .dash-updated { font-size: 12px; color: var(--n500); }

    .stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-tile { background: var(--white); border-radius: var(--r); box-shadow: var(--sh); padding: 20px; }
    .stat-label { font-size: 12px; color: var(--n500); margin-bottom: 8px; }
    .stat-value { font-size: 28px; font-weight: 700; color: var(--n900); }

    .card { background: var(--white); border-radius: var(--r); box-shadow: var(--sh); padding: 24px; margin-bottom: 20px; }
    .card h2 { font-size: 16px; color: var(--n700); margin-bottom: 16px; }

    #lineChart, #barChart { width: 100%; height: auto; }
    .tooltip { position: absolute; background: var(--n900); color: var(--white); font-size: 12px;
      padding: 6px 10px; border-radius: 6px; pointer-events: none; opacity: 0; transition: opacity .1s; white-space: nowrap; }

    table.qtable { width: 100%; border-collapse: collapse; font-size: 13px; }
    table.qtable th { text-align: left; color: var(--n500); font-weight: 500; font-size: 12px;
      padding: 8px 10px; border-bottom: 1px solid var(--n200); }
    table.qtable td { padding: 8px 10px; border-bottom: 1px solid var(--n100); }
    table.qtable td.num { text-align: right; font-variant-numeric: tabular-nums; }

    .naver-card { display: flex; justify-content: space-between; align-items: center; }
    .naver-link { color: var(--g700); font-weight: 700; text-decoration: none; }

    .empty-state { text-align: center; color: var(--n500); padding: 40px 0; font-size: 14px; }
  </style>
</head>
<body>
  <div id="pinScreen">
    <div class="pin-box">
      <h1>마케팅 대시보드</h1>
      <input type="password" class="pin-input" id="pinInput" placeholder="비밀번호">
      <button class="pin-btn" id="pinBtn">입장</button>
      <div class="pin-error" id="pinError">비밀번호가 올바르지 않습니다.</div>
    </div>
  </div>

  <div id="dash">
    <div class="dash-head">
      <h1>zoozoo.kr 마케팅 대시보드</h1>
      <div class="dash-updated" id="updatedAt"></div>
    </div>

    <div class="stat-row" id="statRow"></div>

    <div class="card">
      <h2>최근 30일 방문자 수 (GA4)</h2>
      <svg id="lineChart" viewBox="0 0 640 220"></svg>
    </div>

    <div class="card">
      <h2>유입 경로 Top 5 (최근 30일, GA4)</h2>
      <svg id="barChart" viewBox="0 0 640 200"></svg>
    </div>

    <div class="card">
      <h2>검색어 Top 10 (Google Search Console)</h2>
      <div id="queryTableWrap"></div>
    </div>

    <div class="card naver-card">
      <div>
        <h2 style="margin-bottom:4px">네이버 검색 유입</h2>
        <div style="font-size:13px;color:var(--n500)">네이버 서치어드바이저는 공개 API가 없어 자동 수집이 불가능합니다. 콘솔에서 직접 확인해주세요.</div>
      </div>
      <a class="naver-link" href="https://searchadvisor.naver.com" target="_blank" rel="noopener">서치어드바이저 열기 →</a>
    </div>
  </div>

  <div class="tooltip" id="tooltip"></div>

  <script src="../js/dashboard.js"></script>
</body>
</html>
```

- [ ] **Step 2: dashboard.js 작성**

`website/js/dashboard.js`를 아래 내용으로 생성한다.

```javascript
/* ================================================
   쥬쥬랜드 — 마케팅 대시보드 (읽기 전용)
   ================================================ */
(() => {
  'use strict';

  const ADMIN_PIN = 'zoozoo4500'; // website/js/admin.js의 ADMIN_PIN과 동일하게 유지

  const pinScreen = document.getElementById('pinScreen');
  const pinInput  = document.getElementById('pinInput');
  const pinBtn    = document.getElementById('pinBtn');
  const pinError  = document.getElementById('pinError');
  const dash      = document.getElementById('dash');
  const tooltip   = document.getElementById('tooltip');

  function enter() {
    if (pinInput.value.trim() !== ADMIN_PIN) {
      pinError.classList.add('show');
      return;
    }
    pinScreen.classList.add('hidden');
    dash.classList.add('show');
    loadData();
  }
  pinBtn.addEventListener('click', enter);
  pinInput.addEventListener('keydown', e => { if (e.key === 'Enter') enter(); });

  async function loadData() {
    let data;
    try {
      const res = await fetch('../data/analytics.json?t=' + Date.now(), { cache: 'no-cache' });
      if (!res.ok) throw new Error('not found');
      data = await res.json();
    } catch {
      document.getElementById('statRow').innerHTML =
        '<div class="empty-state">아직 수집된 데이터가 없습니다. ETL 워크플로우가 처음 실행되면 표시됩니다.</div>';
      return;
    }
    renderUpdatedAt(data.updated_at);
    renderStats(data);
    renderLineChart(data.ga4?.daily || []);
    renderBarChart(data.ga4?.sources || []);
    renderQueryTable(data.gsc?.top_queries || []);
  }

  function renderUpdatedAt(iso) {
    if (!iso) return;
    const d = new Date(iso);
    document.getElementById('updatedAt').textContent =
      '마지막 갱신: ' + d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' });
  }

  function renderStats(data) {
    const daily = data.ga4?.daily || [];
    const today = daily[daily.length - 1];
    const total30 = daily.reduce((sum, d) => sum + d.activeUsers, 0);
    const clarityLatest = (data.clarity?.history || []).slice(-1)[0];

    const tiles = [
      { label: '오늘 방문자 (GA4)', value: today ? today.activeUsers.toLocaleString('ko-KR') : '–' },
      { label: '최근 30일 방문자 합계', value: total30.toLocaleString('ko-KR') },
      { label: '평균 스크롤 깊이 (Clarity)', value: clarityLatest ? `${clarityLatest.scrollDepth.toFixed(0)}%` : '–' },
      { label: '평균 참여 시간 (Clarity)', value: clarityLatest ? `${clarityLatest.engagementTime.toFixed(0)}초` : '–' },
    ];

    document.getElementById('statRow').innerHTML = tiles.map(t => `
      <div class="stat-tile">
        <div class="stat-label">${t.label}</div>
        <div class="stat-value">${t.value}</div>
      </div>
    `).join('');
  }

  function renderLineChart(daily) {
    const svg = document.getElementById('lineChart');
    if (!daily.length) { svg.parentElement.innerHTML += '<div class="empty-state">데이터 없음</div>'; return; }

    const W = 640, H = 220, padL = 36, padB = 24, padT = 12, padR = 12;
    const plotW = W - padL - padR, plotH = H - padT - padB;
    const max = Math.max(...daily.map(d => d.activeUsers), 1);
    const stepX = plotW / Math.max(daily.length - 1, 1);

    const points = daily.map((d, i) => {
      const x = padL + i * stepX;
      const y = padT + plotH - (d.activeUsers / max) * plotH;
      return { x, y, d };
    });

    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const areaPath = `${linePath} L${points[points.length - 1].x.toFixed(1)},${padT + plotH} L${points[0].x.toFixed(1)},${padT + plotH} Z`;

    const gridLines = [0, 0.5, 1].map(f => {
      const y = padT + plotH * (1 - f);
      return `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" stroke="var(--grid)" stroke-width="1"/>`;
    }).join('');

    const lastPoint = points[points.length - 1];

    svg.innerHTML = `
      ${gridLines}
      <path d="${areaPath}" fill="var(--series-1)" opacity="0.1"/>
      <path d="${linePath}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${lastPoint.x}" cy="${lastPoint.y}" r="4" fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2"/>
      <text x="${lastPoint.x - 4}" y="${lastPoint.y - 10}" font-size="11" fill="var(--n700)" text-anchor="end">${lastPoint.d.activeUsers}</text>
      ${points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="8" fill="transparent" data-date="${p.d.date}" data-value="${p.d.activeUsers}" class="hover-dot"/>`).join('')}
    `;

    svg.querySelectorAll('.hover-dot').forEach(dot => {
      dot.addEventListener('mousemove', e => showTooltip(e, `${dot.dataset.date}: 방문자 ${dot.dataset.value}명`));
      dot.addEventListener('mouseleave', hideTooltip);
    });
  }

  function renderBarChart(sources) {
    const svg = document.getElementById('barChart');
    if (!sources.length) { svg.parentElement.innerHTML += '<div class="empty-state">데이터 없음</div>'; return; }

    const W = 640, H = 200, padL = 140, padR = 50, rowH = 36, gap = 8;
    const max = Math.max(...sources.map(s => s.sessions), 1);
    const plotW = W - padL - padR;

    const bars = sources.map((s, i) => {
      const y = i * (rowH + gap);
      const w = (s.sessions / max) * plotW;
      return `
        <text x="${padL - 10}" y="${y + rowH / 2 + 4}" font-size="12" fill="var(--n700)" text-anchor="end">${s.source}</text>
        <rect x="${padL}" y="${y}" width="${w}" height="${rowH - 4}" rx="4" fill="var(--series-1)"/>
        <text x="${padL + w + 8}" y="${y + rowH / 2 + 4}" font-size="12" fill="var(--n700)">${s.sessions}</text>
      `;
    }).join('');

    svg.setAttribute('viewBox', `0 0 ${W} ${sources.length * (rowH + gap)}`);
    svg.innerHTML = bars;
  }

  function renderQueryTable(queries) {
    const wrap = document.getElementById('queryTableWrap');
    if (!queries.length) { wrap.innerHTML = '<div class="empty-state">데이터 없음</div>'; return; }
    wrap.innerHTML = `
      <table class="qtable">
        <thead><tr><th>검색어</th><th class="num">클릭</th><th class="num">노출</th><th class="num">평균 순위</th></tr></thead>
        <tbody>
          ${queries.map(q => `
            <tr>
              <td>${q.query}</td>
              <td class="num">${q.clicks}</td>
              <td class="num">${q.impressions}</td>
              <td class="num">${q.position}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  function showTooltip(e, text) {
    tooltip.textContent = text;
    tooltip.style.left = e.pageX + 12 + 'px';
    tooltip.style.top = e.pageY - 28 + 'px';
    tooltip.style.opacity = '1';
  }
  function hideTooltip() { tooltip.style.opacity = '0'; }
})();
```

- [ ] **Step 3: 빈 상태(데이터 없음) 렌더링 확인**

`website/data/analytics.json`이 아직 없는 상태에서 로컬로 페이지를 연다.

Run: `python3 -m http.server 8000 --directory website`
그 다음 브라우저로 `http://localhost:8000/admin/dashboard.html` 접속 → PIN(`zoozoo4500`) 입력 → "아직 수집된 데이터가 없습니다" 메시지가 뜨는지 확인. 확인 후 서버 종료.

- [ ] **Step 4: 샘플 데이터로 차트 렌더링 확인**

임시로 `website/data/analytics.json`을 아래 샘플로 만들고 같은 방법으로 열어 라인차트·바차트·표가 정상적으로 그려지는지 확인한다.

```json
{
  "updated_at": "2026-08-25T00:10:00+09:00",
  "ga4": {
    "daily": [{"date":"2026-08-24","activeUsers":8},{"date":"2026-08-25","activeUsers":15}],
    "sources": [{"source":"naver / organic","sessions":9},{"source":"(direct)","sessions":6},{"source":"instagram","sessions":3}]
  },
  "gsc": { "top_queries": [{"query":"고양 동물원","clicks":4,"impressions":88,"position":7.3}] },
  "clarity": { "history": [{"date":"2026-08-25","sessions":10,"scrollDepth":42.1,"engagementTime":38.4}] },
  "errors": {}
}
```

확인 후 이 샘플 파일은 실제 데이터가 아니므로 삭제한다: `rm website/data/analytics.json`

- [ ] **Step 5: Commit**

```bash
git add website/admin/dashboard.html website/js/dashboard.js
git commit -m "feat: 마케팅 통합 대시보드 페이지 추가"
```

---

### Task 8: Secrets 등록 및 첫 실행 검증 (Blocked — 사용자 입력 필요)

**선행 조건:** 사용자가 가이드 ⑤~⑦을 완료하고 서비스 계정 JSON, GA4 속성 ID, Clarity API 토큰을 전달했어야 한다.

**Files:** 없음 (GitHub 저장소 설정 작업)

- [ ] **Step 1: GitHub Secrets 등록**

`gh` CLI가 인증되어 있으면 아래처럼 등록한다 (또는 사용자가 직접 저장소 Settings → Secrets and variables → Actions에서 등록해도 된다):

```bash
gh secret set GA4_SERVICE_ACCOUNT_JSON < service-account.json
gh secret set GA4_PROPERTY_ID --body "123456789"
gh secret set GSC_SITE_URL --body "https://zoozoo.kr/"
gh secret set CLARITY_PROJECT_ID --body "abc123defg"
gh secret set CLARITY_API_TOKEN --body "<전달받은 토큰>"
```

- [ ] **Step 2: 워크플로우 수동 실행**

```bash
gh workflow run marketing-analytics-etl.yml
```

- [ ] **Step 3: 실행 결과 확인**

```bash
gh run list --workflow=marketing-analytics-etl.yml --limit 1
```

Expected: 최근 실행이 `success` 상태. 실패하면 `gh run view --log`로 로그를 확인해 어떤 플랫폼(GA4/GSC/Clarity) 호출이 실패했는지 확인하고 디버깅한다 (서비스 계정 권한 부여 누락, 속성 ID 오타 등이 흔한 원인).

- [ ] **Step 4: 대시보드에서 실데이터 확인**

`https://zoozoo.kr/admin/dashboard.html`을 브라우저로 열어 PIN 입력 후 방문자 수·유입 경로·검색어가 표시되는지 확인한다 (Search Console 데이터는 등록 후 며칠~2주가 지나야 채워질 수 있음 — 그 전까지는 GA4/Clarity 카드만 채워져도 정상).
