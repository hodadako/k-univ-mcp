from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag
from k_univ_mcp.providers.soongsil.models import SoongsilCourseRow


COURSE_HEADERS = {
    "과목번호",
    "과목명",
    "교수명",
    "개설학과",
    "강의시간(강의실)",
}


class SoongsilParser:
    def parse_courses(self, html: str) -> list[SoongsilCourseRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[SoongsilCourseRow] = []

        table = self._find_course_table(soup)
        if table is None:
            return rows

        for tr in table.select("tbody[id$='-contentTBody'] > tr"):
            if tr.get("rt") != "1":
                continue
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"], recursive=False)]
            if len(cells) < 16:
                cells.extend([""] * (16 - len(cells)))
            if not cells[4] or not cells[5]:
                continue

            rows.append(
                SoongsilCourseRow(
                    plan=cells[0],
                    completion_division_major=cells[1],
                    completion_division_multimajor=cells[2],
                    engineering_certification=cells[3],
                    course_number=cells[4],
                    course_name=cells[5],
                    syllabus_info=cells[6],
                    section=cells[8],
                    professor=cells[9],
                    department=cells[10],
                    time_credits=cells[11],
                    capacity=cells[12],
                    vacancy=cells[13],
                    time_location=cells[14],
                    target_audience=cells[15],
                    raw={"tds": cells},
                )
            )

        return rows

    def _find_course_table(self, soup: BeautifulSoup) -> Tag | None:
        for table in soup.find_all(attrs={"ct": "ST"}):
            header_texts = {
                re.sub(r"\s+", " ", header.get_text(" ", strip=True))
                for header in table.find_all("th")
            }
            if COURSE_HEADERS.issubset(header_texts):
                return table
        return None
