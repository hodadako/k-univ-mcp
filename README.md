# k-univ-mcp

국내 대학의 강의편람·시간표 데이터를 수집하고, 이를 CLI·파일 내보내기·MCP 서버로 제공하기 위한 Python 프로젝트입니다. 현재는 연세대학교 제공자(provider)를 중심으로 구현되어 있으며, 학기별 캠퍼스·대학·학과·교과목 데이터를 단계적으로 조회하고 CSV/XLSX/JSON 계열 형식으로 내보낼 수 있습니다.

## 현재 지원 범위

- 첫 번째 제공자: **연세대학교**
- 라이브 조회 지원: **캠퍼스, 대학(원), 학과, 교과목**
- 시드 데이터 지원: **라이브 조회가 어려울 때 캠퍼스/대학 fallback 용도**
- 내보내기 형식: **CSV, XLSX, JSON, JSONL, raw JSON archive**
- 실행 인터페이스: **CLI**, **MCP tools**

## 프로젝트 구조

```text
src/k_univ_mcp/
  browser_bootstrap.py
  cli.py
  exporter.py
  mcp_server.py
  models.py
  settings.py
  providers/
    base.py
    yonsei/
      bootstrap.py
      client.py
      models.py
      parser.py
      service.py
      data/
        campuses.json
        universities_s1.json
tests/
```

## 연세대학교 제공자 개요

- 공개 진입 페이지
  - `https://underwood1.yonsei.ac.kr/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko`
- 확인된 주요 API 경로
  - 학과/조직 조회: `/sch/sles/SlescsCtr/findSchSlesHandbList.do`
  - 교과목 조회: `/sch/sles/SlessyCtr/findAtnlcHandbList.do`
- 학기(`syy`, `smtDivCd`)는 모든 조회 흐름에서 반드시 명시해야 하는 입력값입니다.
- 캠퍼스 → 대학(원) → 학과 계층은 연세대 서버 응답을 바탕으로 동적으로 탐색합니다.
- 시드 JSON은 테스트와 fallback 용도로만 유지합니다.
- 수동 쿠키(`YONSEI_COOKIE`) 방식과 브라우저 기반 세션 확보 방식을 모두 지원합니다.

## 설치 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

`.env` 파일은 기본 실행에 필수가 아닙니다. 테스트 실행, 기본 CLI 사용, 기본 MCP 서버 실행은 환경변수 없이도 동작합니다. 다만 연세대 live 세션 쿠키를 고정해서 쓰거나 브라우저 부트스트랩 동작을 세밀하게 제어하려면 `.env` 또는 셸 환경변수 설정이 필요합니다.

필요할 때만 예시 파일을 복사해서 사용할 수 있습니다.

```bash
cp .env.example .env
```

브라우저 기반 세션 복구를 사용할 경우 Playwright 브라우저를 한 번 설치해야 합니다.

```bash
playwright install chromium
```

Python `playwright` 패키지는 설치되어 있지만 Chromium 바이너리가 없을 때는, 설정에 따라 첫 실행 시 자동 설치할 수도 있습니다.

## 환경 변수

### `.env`가 필요한 경우와 필요하지 않은 경우

| 상황 | `.env` 필요 여부 | 설명 |
| --- | --- | --- |
| `pytest` 실행 | 불필요 | 기본 설정값만으로 테스트가 동작합니다. |
| 기본 MCP 서버 실행 | 불필요 | `K_UNIV_MCP_TRANSPORT=stdio` 기본값을 사용합니다. |
| 기본 CLI 실행 | 불필요 | 학기/캠퍼스 같은 필수 조회 인자는 CLI 인자로 직접 전달합니다. |
| `YONSEI_COOKIE`로 live 세션 고정 | 선택 | `.env`에 넣어도 되고, 실행 시 셸 환경변수로 주입해도 됩니다. |
| 브라우저 부트스트랩 활성화 | 선택 | `ENABLE_BROWSER_BOOTSTRAP=true` 같은 값을 주고 싶을 때 사용합니다. |
| 출력 디렉터리/transport 변경 | 선택 | 기본값(`out`, `stdio`) 대신 다른 값을 쓰고 싶을 때만 필요합니다. |

즉, 이 프로젝트에서 실제로 필요한 것은 **`.env` 파일 자체가 아니라 환경변수 값**입니다. `.env`는 그 값을 로컬 개발 환경에서 편하게 관리하기 위한 선택적 수단입니다.

예를 들어 live 쿠키를 파일 없이 직접 주입하려면 다음처럼 실행할 수 있습니다.

```bash
YONSEI_COOKIE="JSESSIONID=...; NetFunnel_ID=..." python -m k_univ_mcp.mcp_server
```

또는 브라우저 부트스트랩만 켜고 실행할 수도 있습니다.

```bash
ENABLE_BROWSER_BOOTSTRAP=true BROWSER_BOOTSTRAP_ON_START=true python -m k_univ_mcp.mcp_server
```

- `YONSEI_COOKIE`: 수동으로 넣는 세션 쿠키. 최소 `JSESSIONID`가 필요하며 상황에 따라 `NetFunnel_ID`도 포함될 수 있습니다.
- `YONSEI_REFERER`: 연세대 요청 시 사용할 referer URL
- `ENABLE_BROWSER_BOOTSTRAP=true|false`: 브라우저를 이용한 세션 부트스트랩/갱신 활성화 여부
- `BROWSER_BOOTSTRAP_ON_START=true|false`: 서버 시작 시점에 미리 세션을 한 번 확보할지 여부
- `BROWSER=headless|headed`: 브라우저 실행 모드
- `BROWSER_BOOTSTRAP_TIMEOUT_MS`: 쿠키 확보 대기 시간(ms)
- `BROWSER_READY_SELECTOR`: 쿠키 수집 전 대기할 selector override
- `BROWSER_CLICK_SELECTOR`: 쿠키 발급을 유도하기 위해 먼저 클릭할 selector override
- `AUTO_INSTALL_PLAYWRIGHT_BROWSER=true|false`: 필요 시 Playwright 브라우저 자동 설치 여부
- `YONSEI_SESSION_REFRESH_RETRIES`: 세션 만료로 판단될 때 재시도할 횟수
- `K_UNIV_MCP_OUTPUT_DIR`: 기본 출력 디렉터리
- `K_UNIV_MCP_TRANSPORT`: MCP 서버 transport (`stdio`, `sse`, `streamable-http`)

## CLI 사용 예시

```bash
python -m k_univ_mcp.cli yonsei campuses --year 2026 --semester 10
python -m k_univ_mcp.cli yonsei universities --campus s1 --year 2026 --semester 10
python -m k_univ_mcp.cli yonsei faculties --campus s1 --univ s1103 --year 2026 --semester 10
python -m k_univ_mcp.cli yonsei courses --year 2026 --semester 10 --campus s1 --univ s1103 --faculty 0301
python -m k_univ_mcp.cli yonsei export --year 2026 --semester 10 --campus s1 --outdir out
```

## MCP 도구

- `yonsei_get_campuses`
- `yonsei_get_universities`
- `yonsei_get_faculties`
- `yonsei_get_courses`
- `yonsei_export_courses`

MCP 경로에서도 `year(syy)`와 `semester(smtDivCd)`는 항상 명시적으로 전달해야 하며, 내부적으로는 연세대 서버의 계층형 조직 데이터를 탐색한 뒤 전체 교과목 수집과 export를 수행합니다.

## MCP 서버 실행

```bash
python -m k_univ_mcp.mcp_server
```

기본 transport는 `K_UNIV_MCP_TRANSPORT` 값으로 결정되며, 기본값은 `stdio`입니다.

## 세션 만료 대응 방식

- 세션 만료 감지와 재시도 로직은 `providers/yonsei/client.py` 내부에 캡슐화되어 있습니다.
- `YONSEI_COOKIE`가 주어지면 브라우저 부트스트랩 설정보다 우선합니다.
- HTML 응답, JSON 파싱 실패, 인증 실패로 보이는 응답, 비정상적인 빈 학과 응답 등을 세션 갱신 신호로 취급합니다.
- 브라우저 부트스트랩이 활성화되어 있으면 강한 만료 신호가 나타났을 때만 세션을 새로 확보한 뒤 원 요청을 재시도합니다.
- `BROWSER_BOOTSTRAP_ON_START=true`이면 시작 시점에 한 번 세션을 워밍업하고, 아니면 실제 요청 시점까지 지연합니다.
- 단순한 빈 교과목 목록은 자동 갱신 신호로 보지 않습니다.

## 테스트

```bash
pytest
```

## 알려진 제한 사항

- 브라우저 부트스트랩 인터페이스에는 Selenium 확장 지점이 있지만 현재 구현은 Playwright만 제공합니다.
- 강의 시간 파싱은 best-effort 방식이며, 파싱에 실패해도 원본 문자열은 항상 보존합니다.
