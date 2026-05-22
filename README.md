# k-univ-mcp

한국 대학의 강의편람·시간표 데이터를 CLI, 파일 export, MCP 서버 형태로 사용할 수 있게 만든 Python 프로젝트입니다.

공용 조직 명칭은 다음처럼 통일합니다.

- `College`: 캠퍼스 아래의 단과대학 또는 그에 준하는 상위 학사 조직
- `Department`: 실제 강좌 조회에 사용하는 하위 조직 단위

## 지원 대학

| 대학교 | 지원 캠퍼스 |
| --- | --- |
| 연세대학교 | 신촌, 미래 |
| 동국대학교 | 서울, WISE |
| 가천대학교 | 글로벌, 메디컬 |
| 인하대학교 | 용현 |
| 성신여자대학교 | 수정, 운정 |
| 숭실대학교 | 숭실 |
| 한양대학교 | 서울, ERICA |
| 명지대학교 | 인문, 자연 |

## 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
playwright install chromium
```

## 테스트

```bash
python -m pytest
```

GitHub Actions는 모든 push와 pull request마다 같은 테스트 명령을 실행합니다.

## CLI 예시

자세한 사용 예시는 [`docs/cli-examples.md`](docs/cli-examples.md)를 참고하세요.

## MCP 도구

자세한 도구 목록은 [`docs/mcp-tools.md`](docs/mcp-tools.md)를 참고하세요.

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
- 요청 관련 환경 변수
  - `YONSEI_TIMEOUT`
  - MCP tool 요청의 전체 timeout은 호출하는 MCP client/runtime 쪽에서 별도로 관리될 수 있습니다.

</details>

<details>
<summary>명지대학교 (`myongji`)</summary>

- 지원 캠퍼스
  - 인문: public slug `inmun`
  - 자연: public slug `jayeon`
- 현재 구현은 명지대 학사공지 게시판에서 공지를 찾고, 첨부된 PDF 시간표를 파싱하는 방식입니다.
- 지원 학기
  - `1`: 1학기 편입생 오리엔테이션 공지에 포함된 강의시간표 PDF 기준
  - `summer`: 하계 계절수업 공지의 시간표 PDF 기준
  - `winter`: 동계 계절수업 공지의 시간표 PDF 기준
  - `2`: 현재 미지원
- 현재 main 브랜치에서는 CLI와 MCP에서 `myongji` provider 이름으로 조회와 export를 사용할 수 있습니다.
- 관련 환경 변수
  - `MYONGJI_TIMEOUT`
  - `MYONGJI_SLEEP_SECONDS`

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
  - 서울: public slug `seoul`, default undergraduate request org code `H0002256`
  - ERICA: public slug `erica`, default undergraduate request org code `Y0000316`
  - 대학원도 별도 public campus slug로 노출합니다. 예: `graduate-general`, `graduate-business`, `graduate-law`, `erica-graduate-innovation`
- 학부 외 대학원 조직은 public campus slug -> request org code 매핑으로 관리합니다.
- `campuses` 명령은 학부/대학원 slug를 모두 보여주지만, `export`에서 `--campus`를 생략하면 기본 수집 범위는 기존과 같이 학부(`seoul`, `erica`)만 포함합니다.
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



