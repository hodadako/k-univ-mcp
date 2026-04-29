# k-univ-mcp

한국 대학의 강의편람·시간표 데이터를 CLI, 파일 export, MCP 서버 형태로 사용할 수 있게 만든 Python 프로젝트입니다.

## 지원 대학

학교별로 상류 시스템이 제공하는 학기 코드와 실제 조회 가능한 학기는 다를 수 있습니다. 같은 학교라도 특정 연도나 계절학기에서 조회 범위가 달라질 수 있으니, 항상 해당 학교 시스템이 내려주는 값을 기준으로 확인하는 것이 안전합니다.

| 대학교 | Provider | 조회 계층 | Export | 학기 입력 형식 | 비고 |
| --- | --- | --- | --- | --- | --- |
| 연세대학교 | `yonsei` | 캠퍼스 → 대학(원) → 학과 → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2026`, `semester=10` 같은 코드 | 시드 fallback 일부 지원 |
| 동국대학교 | `dongguk` | 캠퍼스 → 대학 → 학과 → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2026`, `semester=1` 또는 `semester=CM160.10` | 서울/WISE 지원, browser bootstrap 기반 live 세션 사용 |

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
playwright install chromium
```

## CLI 예시

```bash
python -m k_univ_mcp.cli yonsei campuses --year 2026 --semester 10
python -m k_univ_mcp.cli yonsei universities --campus s1 --year 2026 --semester 10
python -m k_univ_mcp.cli yonsei faculties --campus s1 --univ s1103 --year 2026 --semester 10
python -m k_univ_mcp.cli yonsei courses --year 2026 --semester 10 --campus s1 --univ s1103 --faculty 0301
python -m k_univ_mcp.cli yonsei export --year 2026 --semester 10 --campus s1 --outdir out

python -m k_univ_mcp.cli dongguk campuses --year 2026 --semester CM160.10
python -m k_univ_mcp.cli dongguk universities --campus CM030.10 --year 2026 --semester CM160.10
python -m k_univ_mcp.cli dongguk faculties --campus CM030.10 --univ DS0312 --year 2026 --semester CM160.10
python -m k_univ_mcp.cli dongguk courses --year 2026 --semester CM160.10 --campus CM030.10 --univ DS0312 --faculty DS031201
python -m k_univ_mcp.cli dongguk universities --campus CM030.21 --year 2026 --semester 1
python -m k_univ_mcp.cli dongguk export --year 2026 --semester 1 --batch-size 20 --outdir out
```

## MCP 도구

- `yonsei_get_campuses`
- `yonsei_get_universities`
- `yonsei_get_faculties`
- `yonsei_get_courses`
- `yonsei_export_courses`
- `dongguk_get_campuses`
- `dongguk_get_universities`
- `dongguk_get_faculties`
- `dongguk_get_courses`
- `dongguk_export_courses`

## MCP 서버 실행

```bash
python -m k_univ_mcp.mcp_server
```

기본 transport는 `stdio`입니다.

## 학교별 상세

<details>
<summary>연세대학교 (`yonsei`)</summary>

- 시작 페이지: `https://underwood1.yonsei.ac.kr/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko`
- 확인된 API 경로
  - 학과/조직 조회: `/sch/sles/SlescsCtr/findSchSlesHandbList.do`
  - 교과목 조회: `/sch/sles/SlessyCtr/findAtnlcHandbList.do`
- 학기 값은 모든 조회에서 직접 넘겨야 합니다.
- 캠퍼스 → 대학(원) → 학과 구조는 응답을 따라 동적으로 찾습니다.
- 브라우저 부트스트랩 관련 환경 변수
  - `ENABLE_BROWSER_BOOTSTRAP`
  - `BROWSER_BOOTSTRAP_ON_START`
  - `BROWSER`
  - `BROWSER_BOOTSTRAP_TIMEOUT_MS`
  - `BROWSER_READY_SELECTOR`
  - `BROWSER_CLICK_SELECTOR`

</details>

<details>
<summary>동국대학교 (`dongguk`)</summary>

- 지원 캠퍼스
  - 서울: `CM030.10`, `https://support.dongguk.edu`
  - WISE: `CM030.21`, `https://support.dongguk.ac.kr`
- 시작 페이지
  - 서울: `https://support.dongguk.edu/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039`
  - WISE: `https://support.dongguk.ac.kr/unis/index.do?t=654867724D6E564B57577777554374315558647861564273646A524251543039`
- 확인된 API 경로
  - 화면 초기화: `/ed/edc/lesn/EdcLesn010/doLoad.do`
  - 학기 코드 조회: `/ed/sys/doListSemCd.do`
  - 교과목 조회: `/ed/edc/lesn/EdcLesn010/doList.do`
- `doLoad.do`는 코드/조직 목록과 화면 초기화 payload를 주고, 학기 코드는 `doListSemCd.do`, 실제 강의 목록은 `doList.do`에서 조회합니다.
- 학기 입력은 `1`, `2`, `1학기`, `2학기`, `CM160.10` 같은 코드 모두 허용하고 내부에서 학교 코드로 맞춥니다.
- `dongguk export`는 `batch_size`가 필수이며, `batch_index`를 생략하면 내부적으로 전체 배치를 순차 실행한 뒤 마지막에 merged 산출물을 자동 생성합니다.
- 동국대는 브라우저가 만든 런타임 세션 값(`_runningNana`, `_runningMainOpenKey`, `_runningLoginIdenNo`)이 필요합니다.
- 브라우저 부트스트랩 관련 환경 변수
  - `DONGGUK_ENABLE_BROWSER_BOOTSTRAP`
  - `BROWSER`
  - `BROWSER_BOOTSTRAP_TIMEOUT_MS`
  - `BROWSER_READY_SELECTOR`
  - `BROWSER_CLICK_SELECTOR`

</details>

## 문서

- [환경 변수 문서](docs/environment-variables.md)
- [세션 처리 문서](docs/session-handling.md)

## 테스트

```bash
pytest
```

## 제한 사항

- 브라우저 부트스트랩 인터페이스에는 Selenium 확장 지점을 열어뒀지만, 지금은 Playwright만 구현되어 있습니다.
- 강의 시간 파싱은 best-effort 방식이라 완벽하지 않을 수 있습니다. 대신 원본 문자열은 항상 같이 보존합니다.
