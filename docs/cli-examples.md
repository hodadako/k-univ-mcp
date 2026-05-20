# CLI 예시

학교별 CLI 사용 예시는 아래를 참고합니다.

설치된 entrypoint가 잡혀 있으면 `k-univ-mcp ...` 형태로 실행할 수 있고, 아니면 `python -m k_univ_mcp.cli ...` 형태로 동일하게 실행할 수 있습니다.

## 런타임 세션이 필요한 학교

- 연세대 `departments`, `courses`, `export`는 CLI에서 기본적으로 headless browser bootstrap을 자동 시도합니다. 필요하면 `YONSEI_COOKIE`를 직접 넣거나 `bootstrap` 명령으로 세션을 명시적으로 확보할 수도 있습니다.
- 동국대는 browser bootstrap 기반 세션이 사실상 필요하고, `export`에는 `--batch-size`가 필수입니다.
- `all export`도 내부적으로 동국대 export를 함께 실행하므로 `--batch-size`가 필수입니다.
- CLI `export` 실행 중에는 stderr에 먼저 `loading` 상태가 보이고, 실제 작업량이 계산되면 진행률 bar(`#` 채움, `.` 빈칸, `%` 표기)로 전환됩니다. 실패 지점 진단 로그도 stderr에 출력되며 stdout JSON 결과는 그대로 유지됩니다.
- 가천대는 기본 CLI 흐름에서 `WMONID`를 자동 확보하므로 별도 env 없이 바로 실행되는 편입니다.
- 한양대도 기본 CLI 흐름에서 내장 기본값으로 바로 실행되며, `HANYANG_COOKIE`/`HANYANG_TK`는 선택적 override입니다.
- 먼저 `doctor` 명령으로 런타임 준비 상태를 확인할 수 있습니다.
- 연세대는 `bootstrap` 명령으로 headless/headed browser bootstrap을 명시적으로 실행해 세션 쿠키를 확보할 수 있습니다.
- 동국대도 `bootstrap` 명령으로 서울/WISE 세션 상태를 미리 확보할 수 있습니다.

```bash
python -m k_univ_mcp.cli yonsei doctor
python -m k_univ_mcp.cli dongguk doctor
python -m k_univ_mcp.cli yonsei bootstrap
python -m k_univ_mcp.cli dongguk bootstrap
python -m k_univ_mcp.cli yonsei bootstrap --export-shell
python -m k_univ_mcp.cli yonsei bootstrap --write-env
python -m k_univ_mcp.cli dongguk bootstrap --write-env .env.local
```

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
python -m k_univ_mcp.cli all export --year 2026 --semester 1 --batch-size 20 --outdir out

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
python -m k_univ_mcp.cli hanyang colleges --campus graduate-general --year 2026 --semester 1
python -m k_univ_mcp.cli hanyang departments --campus graduate-general --college graduate-general --year 2026 --semester 1
python -m k_univ_mcp.cli hanyang courses --year 2026 --semester 1 --campus graduate-general --college graduate-general --department graduate-general
python -m k_univ_mcp.cli hanyang export --year 2026 --semester winter --campus seoul --outdir out
python -m k_univ_mcp.cli hanyang export --year 2026 --semester 1 --campus graduate-general --outdir out
```

구버전 CLI 호환을 위해 `universities`/`faculties`, `--univ`, `--faculty`도 별칭으로 계속 받을 수 있지만, 문서와 기본 사용법은 `colleges`/`departments`, `--college`, `--department`를 기준으로 합니다.

export 기본 출력 경로는 `<outdir>/<영문 학교 디렉토리명>/`입니다. 예를 들어 `--outdir out`으로 연세대를 export하면 파일은 `out/yonsei/` 아래에 생성됩니다.

한양대는 `campuses`에서 학부(`seoul`, `erica`)뿐 아니라 대학원 public campus slug도 함께 노출합니다. 예를 들어 `graduate-general`, `graduate-business`, `erica-graduate-innovation` 같은 값을 `--campus`에 직접 넣어 호출할 수 있습니다. 다만 `hanyang export`에서 `--campus`를 생략한 기본 수집 범위는 기존 호환성을 위해 학부(`seoul`, `erica`)만 포함합니다.
