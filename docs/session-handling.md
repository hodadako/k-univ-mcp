# Session Handling

이 문서는 학교별 세션 확보 방식과 만료 대응 방식을 설명합니다.

## 연세대학교

- 세션 만료 감지와 재시도 로직은 `providers/yonsei/client.py`에 있습니다.
- `YONSEI_COOKIE`가 있으면 그 값을 먼저 사용합니다.
- HTML 응답, JSON 파싱 실패, 인증 실패처럼 보이는 응답, 비정상적으로 빈 학과 응답 등을 세션 갱신 신호로 봅니다.
- browser bootstrap이 켜져 있으면 이런 신호가 잡혔을 때 세션을 새로 받고 원래 요청을 다시 시도합니다.
- `BROWSER_BOOTSTRAP_ON_START=true`이면 시작 시 한 번 세션을 워밍업합니다.

## 동국대학교

- 세션 처리 로직은 `providers/dongguk/client.py`와 `providers/dongguk/bootstrap.py`에 있습니다.
- 동국대는 단순 쿠키만으로는 부족하고, browser bootstrap으로 런타임 세션 값까지 같이 확보해야 합니다.
- 필요한 런타임 값은 `_runningNana`, `_runningMainOpenKey`, `_runningLoginIdenNo`입니다.
- `doLoad.do`는 화면 초기화와 코드/조직 payload를 주고, 실제 강의 목록은 `doList.do`에서 가져옵니다.
- `DONGGUK_ENABLE_BROWSER_BOOTSTRAP=true`가 기본값이라 기본 CLI/MCP 경로에서도 browser bootstrap을 사용합니다.
- 인증 실패처럼 보이는 JSON payload, HTML 응답, 비정상 응답을 세션 갱신 신호로 보고 재시도합니다.

## 공통 참고

- Playwright가 설치되어 있어도 Chromium 바이너리가 없으면 browser bootstrap이 실패할 수 있습니다.
- 필요하면 `python -m playwright install chromium`로 브라우저를 먼저 설치하세요.
