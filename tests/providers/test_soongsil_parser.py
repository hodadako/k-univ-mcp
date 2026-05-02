from k_univ_mcp.providers.soongsil.parser import SoongsilParser


def test_soongsil_parser_ignores_contact_table_and_reads_course_table() -> None:
    html = """
    <html>
      <body>
        <table id="WD1E" ct="ST">
          <tbody>
            <tr>
              <td>비고</td><td>문의부서</td><td>문의담당자</td><td>문의전화번호</td>
              <td>학부</td><td>교무처 학사팀</td><td>안효상</td><td>02-820-0154</td>
              <td>중소기업대학원</td><td>국제처 국제팀</td><td>강민구</td><td>02-820-0782</td>
              <td>정보과학대학원</td><td>관리처 관리팀</td><td>정연민</td><td>02-820-0191</td>
            </tr>
          </tbody>
        </table>
        <table id="WD0184" ct="ST">
          <tbody id="WD0184-contentTBody">
            <tr rt="2" role="row">
              <th>계획</th><th>계획</th><th>이수구분(주전공)</th><th>이수구분(주전공)</th>
              <th>이수구분(다전공)</th><th>이수구분(다전공)</th><th>공학인증</th><th>공학인증</th>
              <th>과목번호</th><th>과목번호</th><th>과목명</th><th>과목명</th>
              <th>수강유의사항</th><th>수강유의사항</th><th>강좌유형정보</th><th>강좌유형정보</th>
              <th>분반</th><th>분반</th><th>교수명</th><th>교수명</th>
              <th>개설학과</th><th>개설학과</th><th>시간/학점(설계)</th><th>시간/학점(설계)</th>
              <th>수강인원</th><th>수강인원</th><th>여석</th><th>여석</th>
              <th>강의시간(강의실)</th><th>강의시간(강의실)</th><th>수강대상</th><th>수강대상</th>
            </tr>
            <tr rt="1" role="row">
              <td></td><td>전기-국문</td><td>복선-국문/부선-국문</td><td></td>
              <td>2150517201</td><td>국어연구의기초</td><td></td><td></td>
              <td>01</td><td>오충연</td><td>국어국문학과</td><td>3.0/3.0</td>
              <td>37</td><td>3</td><td>화 목 13:30-14:45 (조만식기념관 12312-오충연)</td><td>1학년 국문</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    rows = SoongsilParser().parse_courses(html)

    assert len(rows) == 1
    assert rows[0].course_number == "2150517201"
    assert rows[0].course_name == "국어연구의기초"
    assert rows[0].professor == "오충연"
    assert rows[0].department == "국어국문학과"
