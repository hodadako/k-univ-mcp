# k-univ-mcp

한국 대학의 강의편람·시간표 데이터를 CLI, 파일 export, MCP 서버 형태로 사용할 수 있게 만든 Python 프로젝트입니다.

## 지원 대학

학교별로 수강신청 시스템이 제공하는 학기 코드와 실제 조회 가능한 학기는 다를 수 있습니다. 같은 학교라도 특정 연도나 계절학기에서 조회 범위가 달라질 수 있으니, 항상 해당 학교 시스템이 내려주는 값을 기준으로 확인해야합니다.

| 대학교 | Provider | 조회 계층 | Export | 학기 입력 형식 | 비고                                        |
| --- | --- | --- | --- | --- |-------------------------------------------|
| 연세대학교 | `yonsei` | 캠퍼스 → 대학(원) → 학과 → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2026`, `semester=10` 같은 코드 | 신촌/미래 지원캠퍼스/대학(원) 목록은 시드 fallback 일부 지원   |
| 동국대학교 | `dongguk` | 캠퍼스 → 대학 → 학과 → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2026`, `semester=1` 또는 `semester=CM160.10` | 서울/WISE 지원, browser bootstrap 기반 live 세션 사용 |
| 가천대학교 | `gachon` | 캠퍼스 → 대학 → 학과 → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2026`, `semester=10` 같은 코드 | 글로벌/메디컬 지원, `WMONID` 기반 세션 필요             |
| 인하대학교 | `inha` | 캠퍼스 → 단과대학 → 학부(과) → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2026`, `semester=1` | 용현캠퍼스 지원, ASP.NET PostBack 기반 세션 사용 |
| 성신여자대학교 | `sungshin` | 캠퍼스 → 대학 → 학과 → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `year=2025`, `semester=10` | 수정/운정캠퍼스 지원, AJAX 기반 JSON API 사용 |

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

python -m k_univ_mcp.cli gachon campuses --year 2026 --semester 10
python -m k_univ_mcp.cli gachon universities --campus gachon-global --year 2026 --semester 10
python -m k_univ_mcp.cli gachon faculties --campus gachon-global --univ COL01 --year 2026 --semester 10
python -m k_univ_mcp.cli gachon courses --year 2026 --semester 10 --campus gachon-global --univ COL01 --faculty D001
python -m k_univ_mcp.cli gachon export --year 2026 --semester 10 --campus gachon-global --outdir out

python -m k_univ_mcp.cli inha campuses --year 2026 --semester 1
python -m k_univ_mcp.cli inha universities --campus yonghyeon --year 2026 --semester 1
python -m k_univ_mcp.cli inha faculties --campus yonghyeon --univ 공과대학 --year 2026 --semester 1
python -m k_univ_mcp.cli inha courses --year 2026 --semester 1 --campus yonghyeon --univ 공과대학 --faculty 0194002
python -m k_univ_mcp.cli inha export --year 2026 --semester 1 --campus yonghyeon --univ 공과대학 --faculty 0194002 --outdir out

python -m k_univ_mcp.cli sungshin campuses --year 2025 --semester 10
python -m k_univ_mcp.cli sungshin universities --campus COMM060.1 --year 2025 --semester 10
python -m k_univ_mcp.cli sungshin faculties --campus COMM060.1 --univ COMM075.101 --year 2025 --semester 10
python -m k_univ_mcp.cli sungshin courses --year 2025 --semester 10 --campus COMM060.1 --univ COMM075.101 --faculty 2170100
python -m k_univ_mcp.cli sungshin export --year 2025 --semester 10 --campus COMM060.1 --univ COMM075.101 --faculty 2170100 --outdir out
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
- `gachon_get_campuses`
- `gachon_get_universities`
- `gachon_get_faculties`
- `gachon_get_courses`
- `gachon_export_courses`
- `inha_get_campuses`
- `inha_get_universities`
- `inha_get_faculties`
- `inha_get_courses`
- `inha_export_courses`
- `sungshin_get_campuses`
- `sungshin_get_universities`
- `sungshin_get_faculties`
- `sungshin_get_courses`
- `sungshin_export_courses`

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

<details>
<summary>가천대학교 (`gachon`)</summary>

- 지원 캠퍼스
  - 글로벌: `gachon-global` (`groupType=20`)
  - 메디컬: `gachon-medical` (`groupType=21`)
- 시작 페이지: `https://info.gachon.ac.kr/ssu/showTimetable.do`
- 확인된 API 경로
  - 초기 데이터 로드: `/Ssu1000q/onLoad.do`
  - 학과 조회: `/Ssu1000q/deptList.do`
  - 교과목 조회: `/Ssu1000q/mainSearch.do`
- 학기 값은 모든 조회에서 직접 넘겨야 합니다.
- 캠퍼스별 상위 조직은 `onLoad.do` 응답의 대학 목록을 기준으로 동적으로 찾습니다.
- 가천대 조회에는 `WMONID`가 포함된 유효 세션이 필요하며, `GACHON_COOKIE`로 직접 주입할 수 있습니다.
- 관련 환경 변수
  - `GACHON_COOKIE`
  - `GACHON_TIMEOUT`
  - `GACHON_RETRY_TOTAL`
  - `GACHON_RETRY_BACKOFF`
  - `GACHON_SLEEP_SECONDS`
  - `GACHON_USER_AGENT`

</details>

<details>
<summary>인하대학교 (`inha`)</summary>

- 지원 캠퍼스: 용현 (`yonghyeon`)
- 시작 페이지: `https://sugang.inha.ac.kr/sugang/SU_51001/Lec_Time_Search.htm`
- 확인된 API 경로
  - 교과목 조회: `/SU_51001/Lec_Time_Search.aspx`
  - 대학/학과 조회: `/SU_51001/curriculum.aspx`
- 인하대는 ASP.NET WebForms 기반으로, `__VIEWSTATE`와 `__EVENTTARGET`을 이용한 PostBack 처리가 필요합니다.
- 단과대학 및 학부(과) 계층 구조는 교과과정표를 분석하여 생성하며, 실제 수강신청 시스템의 분류를 따릅니다.
- 관련 환경 변수
  - `INHA_TIMEOUT`
  - `INHA_SLEEP_SECONDS`

</details>

<details>
<summary>성신여자대학교 (`sungshin`)</summary>

- 지원 캠퍼스: 수정 (`COMM060.1`), 운정 (`COMM060.2`)
- 시작 페이지: `https://sugang.sungshin.ac.kr/findBCRM02010.do`
- 확인된 API 경로
  - 초기화 및 코드 로드: `/findBCRM02010OnLoad.do`
  - 교과목 조회: `/findBCRM02010Main.do`
- 성신여대는 AJAX 기반의 JSON API를 사용합니다. `onLoad.do`를 통해 학기, 캠퍼스, 이수구분 등의 메타데이터를 가져오고, `Main.do`를 통해 실제 강의 목록을 조회합니다.
- 학기 코드는 `COMM063.10`(1학기), `COMM063.20`(2학기) 형식을 사용합니다.
- 관련 환경 변수
  - `SUNGSHIN_TIMEOUT`
  - `SUNGSHIN_SLEEP_SECONDS`

</details>

## 문서

- [환경 변수 문서](docs/environment-variables.md)
- [세션 처리 문서](docs/session-handling.md)

## 테스트

```bash
pytest
```

## 제한 사항
- 강의 시간 파싱은 best-effort 방식이라 완벽하지 않을 수 있습니다. 대신 원본 문자열은 항상 같이 보존합니다.
