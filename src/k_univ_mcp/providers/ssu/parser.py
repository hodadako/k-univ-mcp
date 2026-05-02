from __future__ import annotations

from typing import Any
from bs4 import BeautifulSoup, Tag
from k_univ_mcp.providers.ssu.models import SsuCourseRow


class SsuParser:
    def parse_courses(self, html: str) -> list[SsuCourseRow]:
        soup = BeautifulSoup(html, "html.parser")

        # Look for the course table.
        # Based on exploration, Table 1 with ID WD0184 (or similar) contains the data.
        # But IDs might change. Let's look for tr elements that have a certain structure.
        # SAP Web Dynpro rows usually have 'lsTableRow' class or are inside a table with ct="ST".

        rows: list[SsuCourseRow] = []

        # Find all tables with ct="ST"
        tables = soup.find_all(attrs={"ct": "ST"})
        for table in tables:
            tr_elements = table.find_all("tr")
            for tr in tr_elements:
                tds = tr.find_all("td")
                if len(tds) < 15: # SSU course table has many columns
                    continue

                # Check if it's a header or "no data" row
                texts = [td.get_text(strip=True) for td in tds]
                if "계획" in texts or "해당 테이블에 데이터가 없습니다" in texts[0]:
                    continue

                # Column mapping based on observation:
                # 0: 계획 (Plan)
                # 1: 이수구분(주전공)
                # 2: 이수구분(다전공)
                # 3: 공학인증
                # 4: 과목번호
                # 5: 과목명
                # 6: 수강유의사항 (Syllabus info?)
                # 7: 강좌유형정보 (Section?) -> Wait, in screenshot '분반' is separate.
                # Let's re-verify from Table 1 Row 1 output:
                # 계획 | 이수구분(주전공) | 이수구분(다전공) | 공학인증 | 과목번호 | 과목명 | 수강유의사항 | 강좌유형정보 | 분반 | 교수명 | 개설학과 | 시간/학점(설계) | 수강인원 | 여석 | 강의시간(강의실) | 수강대상

                if len(texts) >= 16:
                    rows.append(SsuCourseRow(
                        plan=texts[0],
                        completion_division_major=texts[1],
                        completion_division_multimajor=texts[2],
                        engineering_certification=texts[3],
                        course_number=texts[4],
                        course_name=texts[5],
                        syllabus_info=texts[6],
                        section=texts[8],
                        professor=texts[9],
                        department=texts[10],
                        time_credits=texts[11],
                        capacity=texts[12],
                        vacancy=texts[13],
                        time_location=texts[14],
                        target_audience=texts[15],
                        raw={"tds": texts}
                    ))

        return rows
