# CLI 예시

학교별 CLI 사용 예시는 아래를 참고합니다.

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
