from k_univ_mcp.providers.sungshin.parser import build_course

def test_build_course():
    row = {
        "sbjNm": "Test Course",
        "sbjEnm": "Test Course En",
        "sbjNo": "AA0001",
        "dvcls": "001",
        "profDsc": "Prof. Test",
        "tmtblKorDsc": "Mon/1-3",
        "roomKorDsc": "Room 101",
        "cmpCdNm": "Campus A",
        "cpdivNm": "Major",
        "cdtHcnt": "3.0/3.0/0.0",
        "semCd": "COMM063.10",
        "orgClsfCd": "COMM075.101",
        "crsNm": "Bachelor",
        "dptMjrCd": "1234567",
        "opDptmjrNm": "Dept of Test"
    }

    course = build_course(row, year="2025", semester="COMM063.10")

    assert course.title == "Test Course"
    assert course.course_code == "AA0001"
    assert course.professor_name == "Prof. Test"
    assert course.credits == "3.0"
    assert course.course_key == "AA0001-001"
