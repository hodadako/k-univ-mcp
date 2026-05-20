from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from k_univ_mcp.export_runtime import ExportFailureDiagnostic, ExportProgress, FailureCallback, ProgressCallback
from k_univ_mcp.models import Campus, College, Course, Department, RawPayloadDump
from k_univ_mcp.providers.hanyang.client import HanyangClient
from k_univ_mcp.providers.hanyang.models import HanyangCourseRow
from k_univ_mcp.providers.hanyang.parser import build_course
from k_univ_mcp.semester import normalize_provider_semester
from k_univ_mcp.settings import AppSettings

@dataclass(frozen=True, slots=True)
class HanyangOrgOption:
    code: str
    name: str
    campus_code: str | None
    category: str


HANYANG_ORG_OPTIONS: dict[str, HanyangOrgOption] = {
    "H0002256": HanyangOrgOption("H0002256", "대학(학부/서울)", "seoul", "undergraduate"),
    "H0002601": HanyangOrgOption("H0002601", "의학과(학부/서울)", "seoul", "undergraduate"),
    "Y0000316": HanyangOrgOption("Y0000316", "대학(학부/ERICA)", "erica", "undergraduate"),
    "H0002435": HanyangOrgOption("H0002435", "국제여름학교(서울)", "seoul", "special"),
    "H0000476": HanyangOrgOption("H0000476", "일반대학원", None, "graduate"),
    "H0001999": HanyangOrgOption("H0001999", "도시대학원", None, "graduate"),
    "H0001640": HanyangOrgOption("H0001640", "경영대학원", None, "graduate"),
    "H0001981": HanyangOrgOption("H0001981", "국제학대학원(2025-1학기 이전)(서울/대학원)", "seoul", "graduate"),
    "H0005128": HanyangOrgOption("H0005128", "국제대학원", None, "graduate"),
    "H0000457": HanyangOrgOption("H0000457", "경영전문대학원", None, "graduate"),
    "H0000364": HanyangOrgOption("H0000364", "의학전문대학원", "seoul", "graduate"),
    "H0000368": HanyangOrgOption("H0000368", "법학전문대학원", None, "graduate"),
    "H0000449": HanyangOrgOption("H0000449", "의생명공학전문대학원", None, "graduate"),
    "H0000454": HanyangOrgOption("H0000454", "기술경영전문대학원", None, "graduate"),
    "H0000372": HanyangOrgOption("H0000372", "글로벌경영전문대학원", None, "graduate"),
    "H0002058": HanyangOrgOption("H0002058", "공학대학원", None, "graduate"),
    "H0000401": HanyangOrgOption("H0000401", "공공정책대학원", None, "graduate"),
    "H0001754": HanyangOrgOption("H0001754", "교육대학원", None, "graduate"),
    "H0002028": HanyangOrgOption("H0002028", "국제관광대학원", None, "graduate"),
    "H0001932": HanyangOrgOption("H0001932", "언론정보대학원(대학원/서울)", "seoul", "graduate"),
    "H0003667": HanyangOrgOption("H0003667", "도시융합개발대학원", None, "graduate"),
    "H0003812": HanyangOrgOption("H0003812", "부동산융합대학원", None, "graduate"),
    "H0002244": HanyangOrgOption("H0002244", "임상간호정보대학원", None, "graduate"),
    "H0004528": HanyangOrgOption("H0004528", "임상간호대학원", None, "graduate"),
    "H0003902": HanyangOrgOption("H0003902", "보건대학원", None, "graduate"),
    "Y0000213": HanyangOrgOption("Y0000213", "기업경영대학원", "erica", "graduate"),
    "Y0000223": HanyangOrgOption("Y0000223", "이노베이션대학원", "erica", "graduate"),
    "Y0001037": HanyangOrgOption("Y0001037", "공학기술대학원", "erica", "graduate"),
    "Y0001049": HanyangOrgOption("Y0001049", "문화산업대학원", "erica", "graduate"),
    "Y0001055": HanyangOrgOption("Y0001055", "예술디자인대학원", "erica", "graduate"),
    "Y0001197": HanyangOrgOption("Y0001197", "융합산업대학원", "erica", "graduate"),
    "Y0000268": HanyangOrgOption("Y0000268", "산업경영대학원", "erica", "graduate"),
    "Y0000302": HanyangOrgOption("Y0000302", "디자인대학원", "erica", "graduate"),
    "Y0000178": HanyangOrgOption("Y0000178", "산업경영디자인대학원", "erica", "graduate"),
    "H0004053": HanyangOrgOption("H0004053", "상담심리대학원", None, "graduate"),
    "H0004653": HanyangOrgOption("H0004653", "인공지능융합대학원", None, "graduate"),
    "H0004239": HanyangOrgOption("H0004239", "국제겨울학교(서울)", "seoul", "special"),
    "Y0001114": HanyangOrgOption("Y0001114", "국제여름학교(ERICA)", "erica", "special"),
    "Y0001157": HanyangOrgOption("Y0001157", "국제겨울학교(ERICA)", "erica", "special"),
    "H0005114": HanyangOrgOption("H0005114", "창업대학원", None, "graduate"),
}


@dataclass(frozen=True, slots=True)
class HanyangCampusOption:
    code: str
    name: str
    default_request_org_code: str
    source_campus_code: str | None
    category: str


HANYANG_PUBLIC_CAMPUS_OPTIONS: tuple[HanyangCampusOption, ...] = (
    HanyangCampusOption("seoul", "서울캠퍼스", "H0002256", "seoul", "undergraduate"),
    HanyangCampusOption("erica", "ERICA캠퍼스", "Y0000316", "erica", "undergraduate"),
    HanyangCampusOption("graduate-general", "일반대학원", "H0000476", None, "graduate"),
    HanyangCampusOption("graduate-urban", "도시대학원", "H0001999", None, "graduate"),
    HanyangCampusOption("graduate-business", "경영대학원", "H0001640", None, "graduate"),
    HanyangCampusOption("graduate-international-studies-legacy", "국제학대학원(2025-1학기 이전)(서울/대학원)", "H0001981", "seoul", "graduate"),
    HanyangCampusOption("graduate-international", "국제대학원", "H0005128", None, "graduate"),
    HanyangCampusOption("graduate-business-admin", "경영전문대학원", "H0000457", None, "graduate"),
    HanyangCampusOption("graduate-medical", "의학전문대학원", "H0000364", "seoul", "graduate"),
    HanyangCampusOption("graduate-law", "법학전문대학원", "H0000368", None, "graduate"),
    HanyangCampusOption("graduate-biomedical-engineering", "의생명공학전문대학원", "H0000449", None, "graduate"),
    HanyangCampusOption("graduate-technology-management", "기술경영전문대학원", "H0000454", None, "graduate"),
    HanyangCampusOption("graduate-global-management", "글로벌경영전문대학원", "H0000372", None, "graduate"),
    HanyangCampusOption("graduate-engineering", "공학대학원", "H0002058", None, "graduate"),
    HanyangCampusOption("graduate-public-policy", "공공정책대학원", "H0000401", None, "graduate"),
    HanyangCampusOption("graduate-education", "교육대학원", "H0001754", None, "graduate"),
    HanyangCampusOption("graduate-international-tourism", "국제관광대학원", "H0002028", None, "graduate"),
    HanyangCampusOption("graduate-journalism-and-mass-communication", "언론정보대학원(대학원/서울)", "H0001932", "seoul", "graduate"),
    HanyangCampusOption("graduate-urban-convergence-development", "도시융합개발대학원", "H0003667", None, "graduate"),
    HanyangCampusOption("graduate-real-estate-convergence", "부동산융합대학원", "H0003812", None, "graduate"),
    HanyangCampusOption("graduate-clinical-nursing-informatics", "임상간호정보대학원", "H0002244", None, "graduate"),
    HanyangCampusOption("graduate-clinical-nursing", "임상간호대학원", "H0004528", None, "graduate"),
    HanyangCampusOption("graduate-public-health", "보건대학원", "H0003902", None, "graduate"),
    HanyangCampusOption("erica-graduate-business-management", "기업경영대학원", "Y0000213", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-innovation", "이노베이션대학원", "Y0000223", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-engineering-technology", "공학기술대학원", "Y0001037", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-cultural-industries", "문화산업대학원", "Y0001049", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-arts-and-design", "예술디자인대학원", "Y0001055", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-convergence-industry", "융합산업대학원", "Y0001197", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-industrial-management", "산업경영대학원", "Y0000268", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-design", "디자인대학원", "Y0000302", "erica", "graduate"),
    HanyangCampusOption("erica-graduate-industrial-management-design", "산업경영디자인대학원", "Y0000178", "erica", "graduate"),
    HanyangCampusOption("graduate-counseling-psychology", "상담심리대학원", "H0004053", None, "graduate"),
    HanyangCampusOption("graduate-ai-convergence", "인공지능융합대학원", "H0004653", None, "graduate"),
    HanyangCampusOption("graduate-entrepreneurship", "창업대학원", "H0005114", None, "graduate"),
)

HANYANG_PUBLIC_CAMPUS_OPTIONS_BY_CODE: dict[str, HanyangCampusOption] = {
    option.code: option for option in HANYANG_PUBLIC_CAMPUS_OPTIONS
}

HANYANG_PUBLIC_CAMPUS_CODE_BY_REQUEST_ORG_CODE: dict[str, str] = {
    option.default_request_org_code: option.code for option in HANYANG_PUBLIC_CAMPUS_OPTIONS
}

HANYANG_CAMPUSES = {
    option.code: option.name for option in HANYANG_PUBLIC_CAMPUS_OPTIONS
}

HANYANG_DEFAULT_REQUEST_ORG_CODES = {
    option.code: option.default_request_org_code for option in HANYANG_PUBLIC_CAMPUS_OPTIONS
}

HANYANG_DEFAULT_COLLECT_CAMPUS_CODES: tuple[str, ...] = tuple(
    option.code for option in HANYANG_PUBLIC_CAMPUS_OPTIONS if option.category == "undergraduate"
)

HANYANG_COLLEGES: dict[str, tuple[str, ...]] = {
    "seoul": (
        "공과대학",
        "의과대학",
        "간호대학",
        "인문과학대학",
        "사회과학대학",
        "자연과학대학",
        "정책과학대학",
        "경제금융대학",
        "경영대학",
        "사범대학",
        "생활과학대학",
        "음악대학",
        "예술·체육대학",
        "국제대학",
        "기술혁신대학",
        "한양YK인터칼리지",
        "서울 공통",
    ),
    "erica": (
        "공학대학",
        "소프트웨어융합대학",
        "약학대학",
        "첨단융합대학",
        "글로벌문화통상대학",
        "커뮤니케이션&컬처대학",
        "경상대학",
        "디자인대학",
        "예체능대학",
        "LIONS칼리지",
    ),
}

HANYANG_DEPARTMENT_TO_COLLEGE: dict[str, dict[str, str]] = {
    "seoul": {
        "간호학과": "간호대학",
        "간호학과(야)": "간호대학",
        "건설환경공학과": "공과대학",
        "건축공학부": "공과대학",
        "건축학부": "공과대학",
        "경영공학전공": "기술혁신대학",
        "경영학부": "경영대학",
        "경제금융학부": "경제금융대학",
        "관광학부": "사회과학대학",
        "관현악과": "음악대학",
        "국악과": "음악대학",
        "교육공학과": "사범대학",
        "교육학과": "사범대학",
        "국어교육과": "사범대학",
        "국어국문학과": "인문과학대학",
        "국제학부": "국제대학",
        "글로벌콘텐츠융합학부": "국제대학",
        "기계공학부": "공과대학",
        "기술혁신대학": "기술혁신대학",
        "데이터사이언스학부": "공과대학",
        "데이터사이언스전공": "공과대학",
        "데이터융합서비스디자인융합전공": "기술혁신대학",
        "도시공학과": "공과대학",
        "독어독문학과": "인문과학대학",
        "무용학과": "예술·체육대학",
        "물리학과": "자연과학대학",
        "미디어커뮤니케이션학과": "사회과학대학",
        "미래인문학융합학부": "인문과학대학",
        "미래자동차공학과": "공과대학",
        "반도체공학과": "공과대학",
        "바이오메디컬공학전공": "공과대학",
        "사학과": "인문과학대학",
        "사회학과": "사회과학대학",
        "산업공학과": "공과대학",
        "산업융합학부": "기술혁신대학",
        "생명공학과": "공과대학",
        "생명과학과": "자연과학대학",
        "성악과": "음악대학",
        "수학과": "자연과학대학",
        "수학교육과": "사범대학",
        "사회혁신융합전공": "서울 공통",
        "스포츠매니지먼트전공": "예술·체육대학",
        "스포츠사이언스전공": "예술·체육대학",
        "스포츠산업과학부": "예술·체육대학",
        "식품영양학과": "생활과학대학",
        "신소재공학부": "공과대학",
        "심리뇌과학전공": "공과대학",
        "실내건축디자인학과": "생활과학대학",
        "에너지공학과": "공과대학",
        "연극영화학과": "예술·체육대학",
        "영어교육과": "사범대학",
        "중국경제통상전공": "국제대학",
        "영어영문학과": "인문과학대학",
        "원자력공학과": "공과대학",
        "유기나노공학과": "공과대학",
        "융합전자공학부": "공과대학",
        "응용미술교육과": "사범대학",
        "글로벌 CEO 창업 융합전공": "서울 공통",
        "의류학과": "생활과학대학",
        "의예과": "의과대학",
        "의학과": "의과대학",
        "자원환경공학과": "공과대학",
        "작곡과": "음악대학",
        "전기·생체공학부": "공과대학",
        "전기·생체공학부 바이오메디컬공학전공": "공과대학",
        "전기·생체공학부 전기공학전공": "공과대학",
        "전기공학전공": "공과대학",
        "정보공학전공": "기술혁신대학",
        "정보시스템학과": "공과대학",
        "정책학과": "정책과학대학",
        "통상한국어커뮤니케이션전공": "인문과학대학",
        "정치외교학과": "사회과학대학",
        "중어중문학과": "인문과학대학",
        "철학과": "인문과학대학",
        "컴퓨터소프트웨어학부": "공과대학",
        "파이낸스경영학과": "경영대학",
        "빅데이터융합전공": "자연과학대학",
        "피아노과": "음악대학",
        "한양인터칼리지학부": "한양YK인터칼리지",
        "행정학과": "정책과학대학",
        "화학공학과": "공과대학",
        "화학과": "자연과학대학",
    },
    "erica": {
        "ICT융합학부": "소프트웨어융합대학",
        "게임학부": "소프트웨어융합대학",
        "광고홍보학과": "커뮤니케이션&컬처대학",
        "기계공학과": "공학대학",
        "로봇공학과": "공학대학",
        "문화인류학과": "글로벌문화통상대학",
        "분자생명과학과": "첨단융합대학",
        "산업경영공학과": "공학대학",
        "생명나노공학과": "첨단융합대학",
        "소프트웨어학부": "소프트웨어융합대학",
        "스마트융합공학부": "공학대학",
        "약학과": "약학대학",
        "언론정보학과": "커뮤니케이션&컬처대학",
        "응용수학과": "첨단융합대학",
        "인공지능학과": "소프트웨어융합대학",
        "일본학과": "글로벌문화통상대학",
        "중국학과": "글로벌문화통상대학",
        "컴퓨터학부": "소프트웨어융합대학",
    },
}


def _normalize_hanyang_org_name(name: str | None) -> str:
    if not name:
        return ""
    collapsed = " ".join(name.replace("\xa0", " ").replace("ㆍ", "·").split())
    return collapsed


@dataclass(slots=True)
class HanyangService:
    client: HanyangClient
    pgm_id: str = "P310278"
    menu_id: str = "M006631"
    tk: str = ""
    page_size: int = 500

    @staticmethod
    def _extract_data_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
        for value in payload.values():
            if not isinstance(value, list) or not value:
                continue
            first = value[0]
            if not isinstance(first, dict):
                continue
            data_list = first.get("list", [])
            if isinstance(data_list, list):
                return data_list
        return []

    def _fetch_all_course_rows(
        self,
        *,
        year: str,
        semester: str,
        org_code: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        skip_rows = 0
        total_count: int | None = None

        while True:
            payload = self.client.find_courses(
                year=year,
                semester=semester,
                org_code=org_code,
                pgm_id=self.pgm_id,
                menu_id=self.menu_id,
                tk=self.tk,
                skip_rows=skip_rows,
                max_rows=self.page_size,
            )
            page_rows = self._extract_data_list(payload)
            if not page_rows:
                break

            rows.extend(page_rows)

            if total_count is None:
                raw_total = page_rows[0].get("totalCnt")
                try:
                    total_count = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total_count = None

            if total_count is not None and len(rows) >= total_count:
                break
            if len(page_rows) < self.page_size:
                break

            skip_rows += len(page_rows)

        return rows

    @staticmethod
    def _normalize_semester(semester: str) -> str:
        return normalize_provider_semester("hanyang", semester)

    @staticmethod
    def _campus_option(campus_code: str) -> HanyangCampusOption:
        if campus_code in HANYANG_PUBLIC_CAMPUS_OPTIONS_BY_CODE:
            return HANYANG_PUBLIC_CAMPUS_OPTIONS_BY_CODE[campus_code]
        public_campus_code = HANYANG_PUBLIC_CAMPUS_CODE_BY_REQUEST_ORG_CODE.get(campus_code)
        if public_campus_code is not None:
            return HANYANG_PUBLIC_CAMPUS_OPTIONS_BY_CODE[public_campus_code]
        raise ValueError(f"Unsupported Hanyang campus code: {campus_code}")

    @classmethod
    def _public_campus_code(cls, campus_code: str) -> str:
        return cls._campus_option(campus_code).code

    @classmethod
    def _default_request_org_code(cls, campus_code: str) -> str:
        return cls._campus_option(campus_code).default_request_org_code

    @classmethod
    def _campus_name(cls, campus_code: str) -> str:
        return cls._campus_option(campus_code).name

    @classmethod
    def _build_campus(cls, campus_code: str) -> Campus:
        option = cls._campus_option(campus_code)
        raw: dict[str, str] = {
            "defaultRequestOrgCode": option.default_request_org_code,
            "category": option.category,
        }
        if option.source_campus_code is not None:
            raw["sourceCampusCode"] = option.source_campus_code
        return Campus(code=option.code, name=option.name, raw=raw)

    @staticmethod
    def _default_colleges(public_campus_code: str) -> list[College]:
        return [
            College(
                campus_code=public_campus_code,
                code=public_campus_code,
                name="전체",
                raw={},
            )
        ]

    @staticmethod
    def _college_name_to_code(campus_code: str, college_name: str | None) -> str:
        normalized_name = _normalize_hanyang_org_name(college_name)
        if normalized_name in HANYANG_COLLEGES.get(campus_code, ()):
            return normalized_name
        return normalized_name

    def _list_college_items(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str,
    ) -> list[dict[str, Any]]:
        payload = self.client.list_programs(
            year=year,
            semester=semester,
            org_code=self._default_request_org_code(campus_code),
            pgm_id=self.pgm_id,
            menu_id=self.menu_id,
            tk=self.tk,
        )
        return self._extract_data_list(payload)

    def _fallback_department_to_college(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str,
    ) -> dict[str, str]:
        try:
            items = self._list_college_items(
                year=year,
                semester=semester,
                campus_code=campus_code,
            )
        except Exception:
            return {}

        mapping: dict[str, str] = {}
        for item in items:
            org_name = item.get("pgmSosokNm")
            if not isinstance(org_name, str):
                continue
            normalized_org_name = _normalize_hanyang_org_name(org_name)
            parts = normalized_org_name.split()
            if len(parts) < 3:
                continue
            college_name = parts[1]
            department_path = " ".join(parts[2:])
            mapping[department_path] = college_name
            mapping[parts[-1]] = college_name
            mapping[parts[2]] = college_name
        return mapping

    @staticmethod
    def _known_college_names(campus_code: str) -> tuple[str, ...]:
        return HANYANG_COLLEGES.get(campus_code, ())

    @classmethod
    def _is_known_college_name(cls, campus_code: str, name: str) -> bool:
        return name in cls._known_college_names(campus_code)

    @staticmethod
    def _common_college_fallback_name(campus_code: str) -> str | None:
        if campus_code == "seoul":
            return "서울 공통"
        return None

    @staticmethod
    def _candidate_org_names(row: HanyangCourseRow) -> list[str]:
        candidate_names: list[str] = []
        for value in (
            row.slg_sosok_nm,
            row.ban_sosok_nm,
            row.gnj_sosok_nm,
            row.jojik_gb_nm,
        ):
            normalized_value = _normalize_hanyang_org_name(value)
            if normalized_value and normalized_value not in candidate_names:
                candidate_names.append(normalized_value)
        return candidate_names

    def _resolve_college_for_row(
        self,
        row: HanyangCourseRow,
        *,
        year: str,
        semester: str,
        campus_code: str,
        fallback_department_map: dict[str, str],
    ) -> tuple[str, str | None]:
        del year, semester

        normalized_row_college_name = _normalize_hanyang_org_name(row.jojik_gb_nm)
        if self._is_known_college_name(campus_code, normalized_row_college_name):
            return normalized_row_college_name, normalized_row_college_name
        if normalized_row_college_name.endswith(" 대학"):
            stripped_name = normalized_row_college_name.split(" ", 1)[-1]
            if self._is_known_college_name(campus_code, stripped_name):
                return stripped_name, stripped_name

        static_mapping = HANYANG_DEPARTMENT_TO_COLLEGE.get(campus_code, {})
        for candidate_name in self._candidate_org_names(row):
            college_name = static_mapping.get(candidate_name)
            if college_name is not None:
                return self._college_name_to_code(campus_code, college_name), college_name

        for candidate_name in self._candidate_org_names(row):
            college_name = fallback_department_map.get(candidate_name)
            if college_name is not None:
                return self._college_name_to_code(campus_code, college_name), college_name

        common_college_name = self._common_college_fallback_name(campus_code)
        if common_college_name is not None:
            return common_college_name, common_college_name

        college_code = self._college_name_to_code(campus_code, normalized_row_college_name)
        if not college_code:
            college_code = normalized_row_college_name or campus_code
        return college_code, normalized_row_college_name or None

    def get_campuses(self, *, year: str, semester: str) -> list[Campus]:
        _ = self._normalize_semester(semester)
        return [self._build_campus(option.code) for option in HANYANG_PUBLIC_CAMPUS_OPTIONS]

    def get_colleges(
        self,
        campus_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[College]:
        _ = self._normalize_semester(semester)
        public_campus_code = self._public_campus_code(campus_code)
        college_names = HANYANG_COLLEGES.get(public_campus_code, ())
        if not college_names:
            return self._default_colleges(public_campus_code)

        return [
            College(
                campus_code=public_campus_code,
                code=college_name,
                name=college_name,
                raw={"source": "static_mapping"},
            )
            for college_name in college_names
        ]

    def get_departments(
        self,
        campus_code: str,
        college_code: str,
        *,
        year: str,
        semester: str,
    ) -> list[Department]:
        public_campus_code = self._public_campus_code(campus_code)
        return [
            Department(
                campus_code=public_campus_code,
                college_code=college_code,
                code=college_code,
                name="전체",
                raw={"code": college_code},
            )
        ]

    def get_courses(
        self,
        year: str,
        semester: str,
        campus_code: str,
        college_code: str,
        department_code: str,
    ) -> list[Course]:
        resolved_semester = self._normalize_semester(semester)
        public_campus_code = self._public_campus_code(campus_code)
        fallback_department_map = self._fallback_department_to_college(
            year=year,
            semester=resolved_semester,
            campus_code=campus_code,
        )
        rows = self._fetch_all_course_rows(
            year=year,
            semester=resolved_semester,
            org_code=self._default_request_org_code(campus_code),
        )

        courses: list[Course] = []
        for item in rows:
            row = HanyangCourseRow(item)
            resolved_college_code, resolved_college_name = self._resolve_college_for_row(
                row,
                year=year,
                semester=resolved_semester,
                campus_code=public_campus_code,
                fallback_department_map=fallback_department_map,
            )
            courses.append(
                build_course(
                    row,
                    year=year,
                    semester=resolved_semester,
                    campus_code=public_campus_code,
                    campus_name=self._campus_name(public_campus_code),
                    college_code=resolved_college_code,
                    college_name=resolved_college_name,
                )
            )

        if college_code and college_code != public_campus_code:
            courses = [c for c in courses if c.college_code == college_code]

        if department_code and department_code != public_campus_code:
            courses = [c for c in courses if c.department_code == department_code]

        return courses

    def collect_courses(
        self,
        *,
        year: str,
        semester: str,
        campus_code: str | None = None,
        college_code: str | None = None,
        department_code: str | None = None,
        progress_callback: ProgressCallback | None = None,
        failure_callback: FailureCallback | None = None,
    ) -> tuple[list[Course], list[RawPayloadDump]]:
        resolved_semester = self._normalize_semester(semester)
        courses: list[Course] = []
        raw_payloads: list[RawPayloadDump] = []

        resolved_public_campus_code = (
            self._public_campus_code(campus_code) if campus_code is not None else None
        )
        if resolved_public_campus_code is None:
            campuses = [self._build_campus(public_code) for public_code in HANYANG_DEFAULT_COLLECT_CAMPUS_CODES]
        else:
            campuses = [self._build_campus(resolved_public_campus_code)]

        for current, campus in enumerate(campuses, start=1):
            try:
                fallback_department_map = self._fallback_department_to_college(
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                )
                data_list = self._fetch_all_course_rows(
                    year=year,
                    semester=resolved_semester,
                    org_code=self._default_request_org_code(campus.code),
                )
            except Exception as exc:
                if failure_callback is not None:
                    failure_callback(
                        ExportFailureDiagnostic(
                            provider="hanyang",
                            stage="collect_courses",
                            error_type=type(exc).__name__,
                            message=str(exc),
                            year=year,
                            semester=resolved_semester,
                            campus_code=campus.code,
                            college_code=college_code,
                            department_code=department_code,
                        )
                    )
                raise

            raw_payloads.append(
                RawPayloadDump(
                    provider="hanyang",
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                    college_code=campus.code,
                    department_code=campus.code,
                    payload=data_list,
                )
            )

            for item in data_list:
                row = HanyangCourseRow(item)
                resolved_college_code, resolved_college_name = self._resolve_college_for_row(
                    row,
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                    fallback_department_map=fallback_department_map,
                )
                course = build_course(
                    row,
                    year=year,
                    semester=resolved_semester,
                    campus_code=campus.code,
                    campus_name=campus.name,
                    college_code=resolved_college_code,
                    college_name=resolved_college_name,
                )

                if (
                    college_code
                    and college_code != campus.code
                    and course.college_code != college_code
                ):
                    continue
                if (
                    department_code
                    and department_code != campus.code
                    and course.department_code != department_code
                ):
                    continue

                courses.append(course)

            if progress_callback is not None:
                progress_callback(
                    ExportProgress(
                        provider="hanyang",
                        current=current,
                        total=len(campuses),
                        label=campus.name,
                        campus_code=campus.code,
                        college_code=college_code,
                        department_code=department_code,
                    )
                )

        return courses, raw_payloads


def create_hanyang_service(settings: AppSettings | None = None) -> HanyangService:
    app_settings = settings or AppSettings.from_env()
    client = HanyangClient(
        cookie_header=app_settings.hanyang_cookie or "",
        timeout=app_settings.hanyang_timeout,
        sleep_seconds=app_settings.hanyang_sleep_seconds,
    )
    return HanyangService(
        client=client,
        pgm_id=app_settings.hanyang_pgm_id,
        menu_id=app_settings.hanyang_menu_id,
        tk=app_settings.hanyang_tk,
    )
