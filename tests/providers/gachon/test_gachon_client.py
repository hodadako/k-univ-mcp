from requests import Response
from requests.cookies import RequestsCookieJar
from typing import cast

import requests

from k_univ_mcp.providers.gachon.client import DEPT_LIST_PATH, MAIN_SEARCH_PATH, ONLOAD_PATH, GachonClient


class FakeSession:
    def __init__(self, responses: list[Response]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.cookies = RequestsCookieJar()
        self.calls: list[tuple[str, str, dict[str, str] | None, int]] = []

    def mount(self, *_args, **_kwargs) -> None:
        return None

    def get(self, url: str, timeout: int) -> Response:
        self.calls.append(("GET", url, None, timeout))
        self.cookies.set("WMONID", "test-cookie")
        if not self.responses:
            raise AssertionError("No fake responses left for GachonClient test.")
        return self.responses.pop(0)

    def post(self, url: str, data: dict[str, str], timeout: int) -> Response:
        self.calls.append(("POST", url, data, timeout))
        if not self.responses:
            raise AssertionError("No fake responses left for GachonClient test.")
        return self.responses.pop(0)


def make_response(*, status_code: int = 200, content_type: str = "application/json", body: str = "{}") -> Response:
    response = Response()
    response.status_code = status_code
    response.headers["content-type"] = content_type
    response._content = body.encode("utf-8")
    return response


def test_list_universities_bootstraps_wmonid_and_reads_onload_payload() -> None:
    session = FakeSession(
        [
            make_response(body="ok", content_type="text/plain"),
            make_response(body='{"yearHakgi": {"YEAR": "2026", "TERM_CD": "10"}, "cbUnivCD": [{"DPT_CD": "COL01", "LABEL": "AI대학"}]}'),
        ]
    )
    client = GachonClient(session=cast(requests.Session, cast(object, session)))

    terms, universities = client.list_universities("20")

    assert terms == [{"YEAR": "2026", "TERM_CD": "10"}]
    assert universities == [{"DPT_CD": "COL01", "LABEL": "AI대학"}]
    assert session.calls[0][0] == "GET"
    assert session.calls[1][1].endswith(ONLOAD_PATH)


def test_list_faculties_builds_expected_form_data() -> None:
    session = FakeSession([make_response(body='{"cbDeptCD": [{"DPT_CD": "D001", "LABEL": "컴퓨터공학과"}]}')])
    session.cookies.set("WMONID", "test-cookie")
    client = GachonClient(session=cast(requests.Session, cast(object, session)))

    faculties = client.list_faculties("2026", "10", "21", "COL01")

    assert faculties == [{"DPT_CD": "D001", "LABEL": "컴퓨터공학과"}]
    method, url, data, timeout = session.calls[0]
    assert method == "POST"
    assert url.endswith(DEPT_LIST_PATH)
    assert timeout == client.timeout
    assert data is not None
    assert data["@d1#groupType"] == "21"
    assert data["@d1#searchYear"] == "2026"
    assert data["@d1#searchTerm"] == "10"
    assert data["@d1#searchUnivCD"] == "COL01"
    assert data["@d1#searchDeptCD"] == ""
    assert data["@d1#"] == "SendData"


def test_list_courses_returns_dsmain_rows() -> None:
    session = FakeSession([make_response(body='{"dsMain": [{"HAKSU_NO": "CSE101", "SUBJECT_NM_KOR": "자료구조"}]}')])
    session.cookies.set("WMONID", "test-cookie")
    client = GachonClient(session=cast(requests.Session, cast(object, session)))

    courses = client.list_courses("2026", "10", "20", "COL01", "D001")

    assert courses == [{"HAKSU_NO": "CSE101", "SUBJECT_NM_KOR": "자료구조"}]
    method, url, data, _timeout = session.calls[0]
    assert method == "POST"
    assert url.endswith(MAIN_SEARCH_PATH)
    assert data is not None
    assert data["@d1#groupType"] == "20"
    assert data["@d1#searchUnivCD"] == "COL01"
    assert data["@d1#searchDeptCD"] == "D001"
