# zoozoo.kr 마케팅 분석 도구 설정 가이드

아래를 순서대로 진행해주세요. ①②는 완료 후 값을 Claude에게 전달해야 추적 코드에 반영됩니다. ③④는 등록만 하면 끝입니다. ⑤~⑦은 관리자 패널 통합 대시보드를 만들기 위한 단계입니다 (①③이 먼저 완료되어 있어야 합니다).

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

## ⑤ Google Cloud 서비스 계정 발급 — 대시보드가 GA4·Search Console 데이터를 읽어오기 위한 열쇠

1. https://console.cloud.google.com 접속 → ①과 같은 Google 계정으로 로그인
2. 상단 프로젝트 선택 → "새 프로젝트" → 이름: `zoozoo-dashboard` → 만들기
3. "API 및 서비스" → "라이브러리"에서 `Google Analytics Data API` 검색 → "사용 설정" 클릭
4. 같은 방법으로 `Google Search Console API`도 검색해서 "사용 설정"
5. "API 및 서비스" → "사용자 인증 정보" → "+ 사용자 인증 정보 만들기" → "서비스 계정" 선택
6. 서비스 계정 이름: `zoozoo-dashboard-reader` 입력 → "만들기 및 계속하기" → 역할 선택은 건너뛰고 "완료"
7. 생성된 서비스 계정을 클릭 → "키" 탭 → "키 추가" → "새 키 만들기" → 키 유형 "JSON" 선택 → 다운로드
8. 다운로드된 JSON 파일을 텍스트 편집기로 열어 `"client_email"` 값을 확인합니다 (예: `zoozoo-dashboard-reader@zoozoo-dashboard.iam.gserviceaccount.com`) — 이 이메일 주소는 ⑥에서 사용합니다.
9. GA4 속성 ID도 함께 필요합니다: analytics.google.com → 관리 → 속성 세부정보에서 숫자로 된 "속성 ID"를 확인하세요 (예: `123456789`, `G-`가 아닌 숫자만 있는 값입니다).
10. **다운로드된 JSON 파일 전체 내용과 GA4 속성 ID(숫자)를 Claude에게 전달해주세요.** GitHub 저장소의 비공개 Secrets로만 저장되고 코드나 화면에는 노출되지 않습니다.

## ⑥ 서비스 계정에게 GA4·Search Console 조회 권한 주기

⑤-8에서 확인한 서비스 계정 이메일을 아래 두 곳에 "읽기 전용"으로 등록합니다.

1. **GA4:** analytics.google.com → 관리 → (속성 열의) "속성 액세스 관리" → "+" → "사용자 추가" → 이메일에 서비스 계정 이메일 입력 → 역할 "뷰어" 선택 → 추가
2. **Search Console:** search.google.com/search-console → 설정 → "사용자 및 권한" → "사용자 추가" → 같은 서비스 계정 이메일 입력 → 권한 "전체" 선택 → 추가

## ⑦ Microsoft Clarity API 토큰 발급

1. clarity.microsoft.com → zoozoo.kr 프로젝트 열기 → 우측 상단 "Settings" → "Data Export" 탭
2. "Add API token" 클릭 → 토큰 이름: `zoozoo-dashboard` 입력 → 생성
3. 화면에 표시된 토큰 값을 복사합니다 (이 화면을 벗어나면 다시 볼 수 없으니 바로 복사)
4. **이 토큰 값을 Claude에게 전달해주세요.**

---

①②를 완료하시면 측정 ID 두 개(GA4 `G-...`, Clarity 10자리)를 Claude에게 전달해주세요. 코드에 반영해서 배포하겠습니다.

⑤~⑦까지 완료하시면(서비스 계정 JSON, GA4 속성 ID, Clarity API 토큰) 관리자 패널에 통합 대시보드를 만들어 드립니다.
