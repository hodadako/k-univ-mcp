# k-univ-mcp

한국 대학의 강의편람·시간표 데이터를 가져와서 CLI, 파일 export, MCP 서버 형태로 쓸 수 있게 만든 Python 프로젝트입니다. 지금은 연세대학교부터 붙여 두었고, 학기별 캠퍼스·대학(원)·학과·교과목 데이터를 순서대로 조회한 뒤 CSV, XLSX, JSON 같은 형식으로 저장할 수 있습니다.

## 지금 되는 것

- 첫 번째 제공자: **연세대학교**
- 라이브 조회: **캠퍼스, 대학(원), 학과, 교과목**
- 시드 데이터 fallback: **캠퍼스, 대학(원)**
- export 형식: **CSV, XLSX, JSON, JSONL, raw JSON archive**
- 실행 방식: **CLI**, **MCP tools**

## 디렉터리 구성

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

## 연세대 provider 메모

- 시작 페이지
  - `https://underwood1.yonsei.ac.kr/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko`
- 확인된 API 경로
  - 학과/조직 조회: `/sch/sles/SlescsCtr/findSchSlesHandbList.do`
  - 교과목 조회: `/sch/sles/SlessyCtr/findAtnlcHandbList.do`
- 학기(`syy`, `smtDivCd`)는 모든 조회에서 직접 넣어줘야 합니다.
- 캠퍼스 → 대학(원) → 학과 구조는 연세대 응답을 따라가며 동적으로 찾습니다.
- 시드 JSON은 테스트용이자, 라이브 조회가 어려울 때 쓰는 fallback 용도로만 둡니다.
- 세션은 `YONSEI_COOKIE`를 직접 넣어도 되고, 필요하면 브라우저 부트스트랩으로 다시 받아오게 할 수도 있습니다.

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

기본 실행만 놓고 보면 `.env`는 꼭 필요하지 않습니다. 테스트를 돌리거나, 기본 CLI를 실행하거나, 기본 MCP 서버를 띄우는 정도는 환경변수 없이도 됩니다.

다만 아래처럼 세션 쿠키를 고정해서 쓰거나 브라우저 부트스트랩 동작을 조절하고 싶으면 `.env` 파일이나 셸 환경변수를 쓰면 됩니다.

```bash
cp .env.example .env
```

브라우저 기반 세션 복구를 쓰려면 Playwright 브라우저도 한 번 설치해 두는 편이 좋습니다.

```bash
playwright install chromium
```

`playwright` 패키지는 설치되어 있는데 Chromium 바이너리가 없으면, 설정에 따라 첫 실행 시 자동 설치되도록 둘 수도 있습니다.

## `.env`가 언제 필요한가

| 상황 | `.env` 필요 여부 | 설명 |
| --- | --- | --- |
| `pytest` 실행 | 불필요 | 기본 설정으로 바로 돌아갑니다. |
| 기본 MCP 서버 실행 | 불필요 | transport 기본값이 `stdio`라서 별도 설정 없이 실행됩니다. |
| 기본 CLI 실행 | 불필요 | 학기, 캠퍼스 같은 값은 CLI 인자로 직접 넣습니다. |
| `YONSEI_COOKIE`로 live 세션 고정 | 선택 | `.env`에 넣어도 되고 실행할 때 환경변수로 바로 넘겨도 됩니다. |
| 브라우저 부트스트랩 활성화 | 선택 | `ENABLE_BROWSER_BOOTSTRAP=true` 같은 값을 줄 때 쓰면 편합니다. |
| output 디렉터리나 transport 변경 | 선택 | 기본값 대신 다른 값을 쓰고 싶을 때만 필요합니다. |

정리하면, 이 프로젝트에서 꼭 필요한 건 `.env` 파일이 아니라 **환경변수 값 자체**입니다. `.env`는 그 값을 로컬에서 편하게 관리하려고 두는 선택지에 가깝습니다.

예를 들어 쿠키를 파일 없이 바로 넘기려면 이렇게 실행할 수 있습니다.

```bash
YONSEI_COOKIE="JSESSIONID=...; NetFunnel_ID=..." python -m k_univ_mcp.mcp_server
```

브라우저 부트스트랩만 켜고 실행할 때는 이렇게 할 수 있습니다.

```bash
ENABLE_BROWSER_BOOTSTRAP=true BROWSER_BOOTSTRAP_ON_START=true python -m k_univ_mcp.mcp_server
```

## 환경 변수 목록

- `YONSEI_COOKIE`: 수동으로 넣는 세션 쿠키. 최소 `JSESSIONID`가 필요하고, 경우에 따라 `NetFunnel_ID`도 같이 필요할 수 있습니다.
- `YONSEI_REFERER`: 연세대 요청에 사용할 referer URL
- `ENABLE_BROWSER_BOOTSTRAP=true|false`: 브라우저를 써서 세션을 새로 받아올지 여부
- `BROWSER_BOOTSTRAP_ON_START=true|false`: 서버 시작 시점에 미리 세션을 한 번 확보할지 여부
- `BROWSER=headless|headed`: 브라우저 실행 모드
- `BROWSER_BOOTSTRAP_TIMEOUT_MS`: 쿠키 확보 대기 시간(ms)
- `BROWSER_READY_SELECTOR`: 쿠키 수집 전에 기다릴 selector override
- `BROWSER_CLICK_SELECTOR`: 쿠키 발급을 유도하려고 먼저 클릭할 selector override
- `AUTO_INSTALL_PLAYWRIGHT_BROWSER=true|false`: 필요할 때 Playwright 브라우저를 자동 설치할지 여부
- `YONSEI_SESSION_REFRESH_RETRIES`: 세션 만료로 판단됐을 때 재시도할 횟수
- `K_UNIV_MCP_OUTPUT_DIR`: 기본 출력 디렉터리
- `K_UNIV_MCP_TRANSPORT`: MCP 서버 transport (`stdio`, `sse`, `streamable-http`)

## CLI 예시

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

MCP로 쓸 때도 `year(syy)`와 `semester(smtDivCd)`는 항상 직접 넘겨줘야 합니다. 내부에서는 연세대 조직 계층을 따라가면서 전체 교과목을 수집하고 export 합니다.

## MCP 서버 실행

```bash
python -m k_univ_mcp.mcp_server
```

transport 기본값은 `stdio`입니다.

## 세션 만료 처리 방식

- 세션 만료 감지와 재시도 로직은 `providers/yonsei/client.py` 안에 모아 두었습니다.
- `YONSEI_COOKIE`가 있으면 브라우저 부트스트랩 설정보다 그 값을 먼저 씁니다.
- HTML 응답, JSON 파싱 실패, 인증 실패처럼 보이는 응답, 비정상적으로 빈 학과 응답 등을 세션 갱신 신호로 봅니다.
- 브라우저 부트스트랩이 켜져 있으면 이런 신호가 잡혔을 때만 세션을 새로 받고 원래 요청을 다시 시도합니다.
- `BROWSER_BOOTSTRAP_ON_START=true`이면 시작할 때 한 번 세션을 워밍업하고, 아니면 실제 요청이 들어온 뒤에 처리합니다.
- 단순히 교과목이 비어 있는 경우는 자동 갱신 조건으로 보지 않습니다.

## 테스트

```bash
pytest
```

## 제한 사항

- 브라우저 부트스트랩 인터페이스에는 Selenium 확장 지점을 열어뒀지만, 지금은 Playwright만 구현되어 있습니다.
- 강의 시간 파싱은 best-effort 방식이라 완벽하지 않을 수 있습니다. 대신 원본 문자열은 항상 같이 보존합니다.
