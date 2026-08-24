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
