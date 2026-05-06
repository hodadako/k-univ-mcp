# k-univ-mcp

한국 대학의 강의편람·시간표 데이터를 CLI, 파일 export, MCP 서버 형태로 사용할 수 있게 만든 Python 프로젝트입니다.

공용 조직 명칭은 다음처럼 통일합니다.

- `College`: 캠퍼스 아래의 단과대학 또는 그에 준하는 상위 학사 조직
- `Department`: 실제 강좌 조회에 사용하는 하위 조직 단위

## 지원 대학

학교별로 수강신청 시스템이 제공하는 학기 코드와 실제 조회 가능한 학기는 다를 수 있습니다. CLI와 MCP의 기본 학기 입력은 모든 학교에서 `1`, `2`, `summer`, `winter`로 통일하고, 내부에서 학교별 raw code로 변환합니다. 기존 raw provider code(`10`, `CM160.10`, `COMM063.10` 등)도 하위 호환을 위해 계속 받을 수 있습니다.

| 대학교 | Provider | 조회 계층 | Export | 학기 입력 형식 | 비고 |
| --- | --- | --- | --- | --- | --- |
| 연세대학교 | `yonsei` | 캠퍼스 → College → Department → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | 신촌/미래 지원, 캠퍼스/College 시드 fallback 일부 지원 |
| 동국대학교 | `dongguk` | 캠퍼스 → College → Department → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | 서울/WISE 지원, browser bootstrap 기반 live 세션 사용 |
| 가천대학교 | `gachon` | 캠퍼스 → College → Department → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | 글로벌/메디컬 지원, `WMONID` 기반 세션 필요 |
| 인하대학교 | `inha` | 캠퍼스 → College(단과대학) → Department(학부/과) → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | 용현캠퍼스 지원, ASP.NET PostBack 기반 세션 사용 |
| 성신여자대학교 | `sungshin` | 캠퍼스 → College → Department → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | 수정/운정캠퍼스 지원, AJAX 기반 JSON API 사용 |
| 숭실대학교 | `soongsil` | 캠퍼스 → College → Department → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | SAP Web Dynpro 기반, Playwright 자동화 사용 |
| 한양대학교 | `hanyang` | 캠퍼스 → College → Department → 교과목 | CSV, XLSX, JSON, JSONL, raw JSON archive | `1`, `2`, `summer`, `winter` | 서울/ERICA 지원, `tk` 파라미터 필요 |

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
playwright install chromium
```

## CLI 예시

```bash
python -m k_univ_mcp.cli yonsei campuses --year 2026 --semester 1
python -m k_univ_mcp.cli yonsei colleges --campus sinchon-undergraduate --year 2026 --semester 1
python -m k_univ_mcp.cli yonsei departments --campus sinchon-undergraduate --college s1103 --year 2026 --semester 1
python -m k_univ_mcp.cli yonsei courses --year 2026 --semester 1 --campus sinchon-undergraduate --college s1103 --department 0301
python -m k_univ_mcp.cli yonsei export --year 2026 --semester 1 --campus sinchon-undergraduate --outdir out

python -m k_univ_mcp.cli dongguk campuses --year 2026 --semester 1
python -m k_univ_mcp.cli dongguk colleges --campus seoul --year 2026 --semester 1
python -m k_univ_mcp.cli dongguk departments --campus seoul --college DS0312 --year 2026 --semester 1
python -m k_univ_mcp.cli dongguk courses --year 2026 --semester 1 --campus seoul --college DS0312 --department DS031201
python -m k_univ_mcp.cli dongguk export --year 2026 --semester winter --batch-size 20 --outdir out

python -m k_univ_mcp.cli gachon campuses --year 2026 --semester 1
python -m k_univ_mcp.cli gachon colleges --campus gachon-global --year 2026 --semester 1
python -m k_univ_mcp.cli gachon departments --campus gachon-global --college COL01 --year 2026 --semester 1
python -m k_univ_mcp.cli gachon courses --year 2026 --semester 1 --campus gachon-global --college COL01 --department D001
python -m k_univ_mcp.cli gachon export --year 2026 --semester 2 --campus gachon-global --outdir out

python -m k_univ_mcp.cli inha campuses --year 2026 --semester 1
python -m k_univ_mcp.cli inha colleges --campus yonghyeon --year 2026 --semester 1
python -m k_univ_mcp.cli inha departments --campus yonghyeon --college 공과대학 --year 2026 --semester 1
python -m k_univ_mcp.cli inha courses --year 2026 --semester 1 --campus yonghyeon --college 공과대학 --department 0194002
python -m k_univ_mcp.cli inha export --year 2026 --semester 2 --campus yonghyeon --college 공과대학 --department 0194002 --outdir out

python -m k_univ_mcp.cli sungshin campuses --year 2025 --semester 1
python -m k_univ_mcp.cli sungshin colleges --campus sujeong --year 2025 --semester 1
python -m k_univ_mcp.cli sungshin departments --campus sujeong --college COMM075.101 --year 2025 --semester 1
python -m k_univ_mcp.cli sungshin courses --year 2025 --semester 1 --campus sujeong --college COMM075.101 --department 2170100
python -m k_univ_mcp.cli sungshin export --year 2025 --semester 2 --campus sujeong --college COMM075.101 --department 2170100 --outdir out

python -m k_univ_mcp.cli soongsil campuses --year 2026 --semester 1
python -m k_univ_mcp.cli soongsil colleges --campus soongsil --year 2026 --semester 1
python -m k_univ_mcp.cli soongsil departments --campus soongsil --college soongsil_all --year 2026 --semester 1
python -m k_univ_mcp.cli soongsil courses --year 2026 --semester 1 --campus soongsil --college soongsil_all --department soongsil_all
python -m k_univ_mcp.cli soongsil export --year 2026 --semester 2 --outdir out

python -m k_univ_mcp.cli hanyang campuses --year 2026 --semester 1
python -m k_univ_mcp.cli hanyang colleges --campus seoul --year 2026 --semester 1
python -m k_univ_mcp.cli hanyang departments --campus seoul --college seoul --year 2026 --semester 1
python -m k_univ_mcp.cli hanyang courses --year 2026 --semester summer --campus seoul --college seoul --department seoul
python -m k_univ_mcp.cli hanyang export --year 2026 --semester winter --campus seoul --outdir out
```

구버전 CLI 호환을 위해 `universities`/`faculties`, `--univ`, `--faculty`도 별칭으로 계속 받을 수 있지만, 문서와 기본 사용법은 `colleges`/`departments`, `--college`, `--department`를 기준으로 합니다.

export 기본 출력 경로는 `<outdir>/<영문 학교 디렉토리명>/`입니다. 예를 들어 `--outdir out`으로 연세대를 export하면 파일은 `out/yonsei/` 아래에 생성됩니다.

## MCP 도구

- `yonsei_get_campuses`
- `yonsei_get_colleges`
- `yonsei_get_departments`
- `yonsei_get_courses`
- `yonsei_export_courses`
- `dongguk_get_campuses`
- `dongguk_get_colleges`
- `dongguk_get_departments`
- `dongguk_get_courses`
- `dongguk_export_courses`
- `gachon_get_campuses`
- `gachon_get_colleges`
- `gachon_get_departments`
- `gachon_get_courses`
- `gachon_export_courses`
- `inha_get_campuses`
- `inha_get_colleges`
- `inha_get_departments`
- `inha_get_courses`
- `inha_export_courses`
- `sungshin_get_campuses`
- `sungshin_get_colleges`
- `sungshin_get_departments`
- `sungshin_get_courses`
- `sungshin_export_courses`
- `soongsil_get_campuses`
- `soongsil_get_colleges`
- `soongsil_get_departments`
- `soongsil_get_courses`
- `soongsil_export_courses`
- `hanyang_get_campuses`
- `hanyang_get_colleges`
- `hanyang_get_departments`
- `hanyang_get_courses`
- `hanyang_export_courses`

## MCP 서버 실행

```bash
python -m k_univ_mcp.mcp_server
```

기본 transport는 `stdio`입니다.

## 학교별 상세

<details>
<summary>연세대학교 (`yonsei`)</summary>

- 시작 페이지: `https://underwood1.yonsei.ac.kr/com/lgin/SsoCtr/initExtPageWork.do?link=handbList&locale=ko`
- public campus slug
  - `sinchon-undergraduate`, `sinchon-graduate`, `sinchon-medical`
  - `mirae-undergraduate`, `mirae-graduate`, `mirae-medical`
- 확인된 API 경로
  - 조직 조회: `/sch/sles/SlescsCtr/findSchSlesHandbList.do`
  - 교과목 조회: `/sch/sles/SlessyCtr/findAtnlcHandbList.do`
- 학기 값은 모든 조회에서 직접 넘겨야 합니다.
- 캠퍼스 → College → Department 구조는 응답을 따라 동적으로 찾습니다.
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
  - 서울: public slug `seoul`, upstream code `CM030.10`, `https://support.dongguk.edu`
  - WISE: public slug `wise`, upstream code `CM030.21`, `https://support.dongguk.ac.kr`
- 시작 페이지
  - 서울: `https://support.dongguk.edu/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039`
  - WISE: `https://support.dongguk.ac.kr/unis/index.do?t=654867724D6E564B57577777554374315558647861564273646A524251543039`
- 확인된 API 경로
  - 화면 초기화: `/ed/edc/lesn/EdcLesn010/doLoad.do`
  - 학기 코드 조회: `/ed/sys/doListSemCd.do`
  - 교과목 조회: `/ed/edc/lesn/EdcLesn010/doList.do`
- `doLoad.do`는 코드/조직 목록과 화면 초기화 payload를 주고, 학기 코드는 `doListSemCd.do`, 실제 강의 목록은 `doList.do`에서 조회합니다.
- 학기 입력은 기본적으로 `1`, `2`, `summer`, `winter`를 권장하며, `1학기`, `2학기`, `여름학기`, `겨울학기`, `CM160.10` 같은 legacy/raw code도 계속 허용하고 내부에서 학교 코드로 맞춥니다.
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
  - 글로벌: public slug `gachon-global` (`groupType=20`)
  - 메디컬: public slug `gachon-medical` (`groupType=21`)
- 시작 페이지: `https://info.gachon.ac.kr/ssu/showTimetable.do`
- 확인된 API 경로
  - 초기 데이터 로드: `/Ssu1000q/onLoad.do`
  - Department 조회: `/Ssu1000q/deptList.do`
  - 교과목 조회: `/Ssu1000q/mainSearch.do`
- 학기 값은 모든 조회에서 직접 넘겨야 합니다.
- 캠퍼스별 상위 조직은 `onLoad.do` 응답의 College 목록을 기준으로 동적으로 찾습니다.
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

- 지원 캠퍼스: 용현 (public slug `yonghyeon`)
- 시작 페이지: `https://sugang.inha.ac.kr/sugang/SU_51001/Lec_Time_Search.htm`
- 확인된 API 경로
  - 교과목 조회: `/SU_51001/Lec_Time_Search.aspx`
  - College/Department 조회: `/SU_51001/curriculum.aspx`
- 인하대는 ASP.NET WebForms 기반으로, `__VIEWSTATE`와 `__EVENTTARGET`을 이용한 PostBack 처리가 필요합니다.
- 단과대학 및 실제 Department 계층 구조는 교과과정표를 분석하여 생성하며, 실제 수강신청 시스템의 분류를 따릅니다.
- 관련 환경 변수
  - `INHA_TIMEOUT`
  - `INHA_SLEEP_SECONDS`

</details>

<details>
<summary>성신여자대학교 (`sungshin`)</summary>

- 지원 캠퍼스: 수정 (public slug `sujeong`, upstream code `COMM060.1`), 운정 (public slug `unjeong`, upstream code `COMM060.2`)
- 시작 페이지: `https://sugang.sungshin.ac.kr/findBCRM02010.do`
- 확인된 API 경로
  - 초기화 및 코드 로드: `/findBCRM02010OnLoad.do`
  - 교과목 조회: `/findBCRM02010Main.do`
- 성신여대는 AJAX 기반의 JSON API를 사용합니다. `onLoad.do`를 통해 학기, 캠퍼스, 이수구분 등의 메타데이터를 가져오고, `Main.do`를 통해 실제 강의 목록을 조회합니다.
- 기본 학기 입력은 `1`, `2`, `summer`, `winter`를 사용합니다. 현재 확인된 raw 학기 코드는 `COMM063.10`(1학기), `COMM063.20`(2학기)이며 이 값도 계속 허용합니다.
- 관련 환경 변수
  - `SUNGSHIN_TIMEOUT`
  - `SUNGSHIN_SLEEP_SECONDS`

</details>

<details>
<summary>숭실대학교 (`soongsil`)</summary>

- 지원 캠퍼스: 숭실 (public slug `soongsil`)
- 시작 페이지: `https://ecc.ssu.ac.kr/sap/bc/webdynpro/sap/zcmw2100?sap-language=KO`
- 숭실대는 SAP Web Dynpro 기반으로 동작하며, Playwright를 이용한 브라우저 자동화 방식으로 데이터를 조회합니다.
- College → Department 계층을 동적으로 탐색해 교과목을 조회합니다.

</details>

<details>
<summary>한양대학교 (`hanyang`)</summary>

- 지원 캠퍼스
  - 서울: public slug `seoul`, upstream code `H0002256`
  - ERICA: public slug `erica`, upstream code `H0002263`
- 시작 페이지: `https://portal.hanyang.ac.kr/sugang/sulg.do`
- 확인된 API 경로
  - 교과목 조회: `/sugang/SgscAct/findSuupSearchSugangSiganpyo.do`
  - 조직(프로그램) 조회: `/sugang/SgscAct/findPgmList.do`
- 한양대는 `pgmId`, `menuId`, `tk` 파라미터가 필요하며, 이는 브라우저 세션에서 추출해야 합니다.
- 관련 환경 변수
  - `HANYANG_COOKIE`
  - `HANYANG_PGM_ID`
  - `HANYANG_MENU_ID`
  - `HANYANG_TK`
  - `HANYANG_TIMEOUT`
  - `HANYANG_SLEEP_SECONDS`

</details>

## 문서

- [환경 변수 문서](docs/environment-variables.md)
- [세션 처리 문서](docs/session-handling.md)
- [데이터 규약](docs/conventions.md)
- [깃 규칙](docs/git-rules.md)
