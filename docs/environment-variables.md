# Environment Variables

이 문서는 `k-univ-mcp`에서 사용할 수 있는 환경 변수를 정리합니다.

## 공통

- `K_UNIV_MCP_OUTPUT_DIR`: 기본 출력 디렉터리
- `K_UNIV_MCP_TRANSPORT`: MCP 서버 transport (`stdio`, `sse`, `streamable-http`)
- `BROWSER`: 브라우저 실행 모드 (`headless`, `headed`)
- `BROWSER_BOOTSTRAP_TIMEOUT_MS`: 브라우저 세션 확보 대기 시간(ms). 기본값은 `120000`입니다.
- MCP tool 요청의 전체 timeout은 이 서버 설정이 아니라 호출하는 MCP client/runtime에서 관리될 수 있습니다.
- `BROWSER_READY_SELECTOR`: 브라우저 준비 대기 selector override
- `BROWSER_CLICK_SELECTOR`: 브라우저 진입 후 클릭 selector override
- `AUTO_INSTALL_PLAYWRIGHT_BROWSER`: 필요 시 Playwright Chromium 자동 설치 여부

## 연세대학교

- `YONSEI_COOKIE`: 수동 세션 쿠키
- `YONSEI_REFERER`: 연세대 요청 referer
- `ENABLE_BROWSER_BOOTSTRAP`: 연세대 browser bootstrap 사용 여부
- `BROWSER_BOOTSTRAP_ON_START`: 서버 시작 시점에 연세대 세션을 미리 워밍업할지 여부
- `YONSEI_SESSION_REFRESH_RETRIES`: 세션 만료로 판단됐을 때 재시도 횟수
- `YONSEI_TIMEOUT`: 요청 timeout(초). 기본값은 `120`입니다.
- `YONSEI_RETRY_TOTAL`: HTTP 재시도 횟수
- `YONSEI_RETRY_BACKOFF`: HTTP 재시도 backoff
- `YONSEI_SLEEP_SECONDS`: 요청 사이 대기 시간
- `YONSEI_SEED_ROOT`: 시드 데이터 루트 디렉터리 override

## 동국대학교

- `DONGGUK_COOKIE`: 공통 수동 세션 쿠키
- `DONGGUK_SEOUL_COOKIE`: 서울 캠퍼스 전용 수동 세션 쿠키
- `DONGGUK_WISE_COOKIE`: WISE 캠퍼스 전용 수동 세션 쿠키
- `DONGGUK_ENABLE_BROWSER_BOOTSTRAP`: 동국대 browser bootstrap 사용 여부. 기본값은 `true`
- `DONGGUK_REFERER`: 동국대 요청 referer
- `DONGGUK_SESSION_REFRESH_RETRIES`: 세션 만료로 판단됐을 때 재시도 횟수
- `DONGGUK_TIMEOUT`: 요청 timeout(초)
- `DONGGUK_RETRY_TOTAL`: HTTP 재시도 횟수
- `DONGGUK_RETRY_BACKOFF`: HTTP 재시도 backoff
- `DONGGUK_SLEEP_SECONDS`: 요청 사이 대기 시간
- `DONGGUK_USER_AGENT`: 동국대 요청에 사용할 User-Agent

## 가천대학교

- `GACHON_COOKIE`: 수동 세션 쿠키
- `GACHON_TIMEOUT`: 요청 timeout(초)
- `GACHON_RETRY_TOTAL`: HTTP 재시도 횟수
- `GACHON_RETRY_BACKOFF`: HTTP 재시도 backoff
- `GACHON_SLEEP_SECONDS`: 요청 사이 대기 시간
- `GACHON_USER_AGENT`: 가천대 요청에 사용할 User-Agent

## 인하대학교

- `INHA_TIMEOUT`: 요청 timeout(초)
- `INHA_SLEEP_SECONDS`: 요청 사이 대기 시간

## 성신여자대학교

- `SUNGSHIN_TIMEOUT`: 요청 timeout(초)
- `SUNGSHIN_SLEEP_SECONDS`: 요청 사이 대기 시간

## 한양대학교

- `HANYANG_COOKIE`: 수동 세션 쿠키
- `HANYANG_TIMEOUT`: 요청 timeout(초)
- `HANYANG_SLEEP_SECONDS`: 요청 사이 대기 시간
- `HANYANG_PGM_ID`: 프로그램 ID
- `HANYANG_MENU_ID`: 메뉴 ID
- `HANYANG_TK`: 세션 기반 토큰

## 참고

- 대부분의 값은 기본값이 코드에 들어 있으므로 항상 설정할 필요는 없습니다.
- 로컬 개발에서는 `.env.example`을 복사해서 필요한 값만 채우는 방식으로 사용할 수 있습니다.
