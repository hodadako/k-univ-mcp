from requests import Response
from typing import cast

import requests
from requests.cookies import RequestsCookieJar

from k_univ_mcp.providers.dongguk.bootstrap import DonggukSessionState
from k_univ_mcp.providers.dongguk.client import LIST_URL, LOAD_URL, SEMESTER_URL, DonggukAuthenticationError, DonggukClient


class FakeSession:
    def __init__(self, responses: list[Response]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.cookies = RequestsCookieJar()
        self.calls: list[tuple[str, str, dict[str, str], int]] = []

    def mount(self, *_args, **_kwargs) -> None:
        return None

    def request(self, method: str, url: str, data: dict[str, str], timeout: int) -> Response:
        self.calls.append((method, url, data, timeout))
        if not self.responses:
            raise AssertionError("No fake responses left for DonggukClient test.")
        return self.responses.pop(0)


def make_response(*, status_code: int = 200, content_type: str = "application/json", body: str = "{}") -> Response:
    response = Response()
    response.status_code = status_code
    response.headers["content-type"] = content_type
    response._content = body.encode("utf-8")
    return response


def test_list_courses_builds_expected_form_data() -> None:
    session = FakeSession([make_response(body='{"dsMain": []}')])
    client = DonggukClient(session=cast(requests.Session, cast(object, session)))
    client._session_ready = True
    client._course_page_payload = {}
    client._session_state = DonggukSessionState(
        cookie_header="JSESSIONID=test",
        running_nana="nana",
        running_main_open_key="open-key",
        running_login_iden_no="login-iden",
    )

    courses = client.list_courses("2026", "CM160.10", "CM030.10", "DS0304", "DS030412")

    assert courses == []
    assert len(session.calls) == 1
    method, url, data, timeout = session.calls[0]
    assert method == "POST"
    assert url == f"https://support.dongguk.edu{LIST_URL}"
    assert timeout == client.timeout
    assert data["@d1#OPEN_YY"] == "2026"
    assert data["@d1#OPEN_SEM_CD"] == "CM160.10"
    assert data["@d1#OPEN_ORGN_CLSF_CD"] == "CM015.110"
    assert data["@d1#DPT_CD"] == "DS030412"
    assert data["@d1#COLG_CD"] == "DS0304"
    assert data["@d1#CAMP_FG"] == "S"
    assert data["@d1#CONN_ORGN_CD"] == "DS03"
    assert data["@d#"] == "@d1#"
    assert data["@d1#"] == "dmSearch"
    assert data["@d1#tp"] == "dm"
    assert data["_runningNana"] == "nana"
    assert data["_runningMainOpenKey"] == "open-key"
    assert data["_runningLoginIdenNo"] == "login-iden"


def test_list_courses_uses_wise_adapter_values() -> None:
    session = FakeSession([make_response(body='{"dsMain": []}')])
    client = DonggukClient(
        session=cast(requests.Session, cast(object, session)),
        base_url="https://support.dongguk.ac.kr",
        referer="https://support.dongguk.ac.kr/unis/index.do?t=6544684B636D786A4E6B4A46566E63355A45394D536D78524E44526F647A3039",
        campus_code="CM030.21",
        campus_fg="K",
        orgn_clsf_cd="CM015.230",
        conn_orgn_cd="DK",
    )
    client._session_ready = True
    client._course_page_payload = {}
    client._session_state = DonggukSessionState(
        cookie_header="JSESSIONID=test",
        running_nana="nana",
        running_main_open_key="open-key",
        running_login_iden_no="login-iden",
    )

    courses = client.list_courses("2026", "CM160.10", "CM030.21", "DK01", "DK0101")

    assert courses == []
    method, url, data, timeout = session.calls[0]
    assert method == "POST"
    assert url == f"https://support.dongguk.ac.kr{LIST_URL}"
    assert timeout == client.timeout
    assert data["@d1#OPEN_ORGN_CLSF_CD"] == "CM015.230"
    assert data["@d1#CAMP_FG"] == "K"
    assert data["@d1#CONN_ORGN_CD"] == "DK"


def test_bootstrap_uses_refresh_session_state_when_available() -> None:
    session = FakeSession([make_response(body='{"dsCodeOrgnClsfCd": []}')])
    client = DonggukClient(
        session=cast(requests.Session, cast(object, session)),
        refresh_session_state=lambda: DonggukSessionState(
            cookie_header="JSESSIONID=test; locale=ko",
            running_nana="nana",
            running_main_open_key="open-key",
            running_login_iden_no="login-iden",
        ),
    )

    payload = client.load_course_page()

    assert payload == {"dsCodeOrgnClsfCd": []}
    assert len(session.calls) == 1
    method, url, data, _timeout = session.calls[0]
    assert method == "POST"
    assert url == f"https://support.dongguk.edu{LOAD_URL}"
    assert data["_runningNana"] == "nana"
    assert data["_runningMainOpenKey"] == "open-key"
    assert data["_runningLoginIdenNo"] == "login-iden"


def test_bootstrap_uses_custom_index_path_for_http_bootstrap() -> None:
    session = FakeSession(
        [
            make_response(body="<html>index</html>", content_type="text/html"),
            make_response(body='{"ERRMSGINFO": {"STATUSCODE": -3000, "ERRMSG": "로그인 후 잘못된 방법으로 데이터 요청이 수행되어 로그아웃 처리 되었습니다."}}'),
        ]
    )
    client = DonggukClient(
        session=cast(requests.Session, cast(object, session)),
        base_url="https://support.dongguk.ac.kr",
        index_path="/unis/index.do?t=wise-token",
        referer="https://support.dongguk.ac.kr/unis/index.do?t=wise-token",
    )
    try:
        client._bootstrap_once()
    except DonggukAuthenticationError:
        pass
    else:
        raise AssertionError("Expected custom-index bootstrap test to stop after verifying the request path.")

    method, url, _data, _timeout = session.calls[0]
    assert method == "GET"
    assert url == "https://support.dongguk.ac.kr/unis/index.do?t=wise-token"


def test_fetch_semesters_uses_semester_endpoint_with_orgn_code() -> None:
    session = FakeSession([
        make_response(body='{"dsCodeOrgnClsfCd": []}'),
        make_response(body='{"__dsCodeSemCd": [{"ORGN_CLSF_CD": "CM015.110", "SEM_CD": "CM160.10", "CD_NM": "1학기"}]}'),
    ])
    client = DonggukClient(
        session=cast(requests.Session, cast(object, session)),
        refresh_session_state=lambda: DonggukSessionState(
            cookie_header="JSESSIONID=test; locale=ko",
            running_nana="nana",
            running_main_open_key="open-key",
            running_login_iden_no="login-iden",
        ),
    )

    semesters = client.fetch_semesters()

    assert semesters == [{"ORGN_CLSF_CD": "CM015.110", "SEM_CD": "CM160.10", "CD_NM": "1학기"}]
    assert len(session.calls) == 2
    method, url, data, timeout = session.calls[1]
    assert method == "POST"
    assert url == f"https://support.dongguk.edu{SEMESTER_URL}"
    assert timeout == client.timeout
    assert data["ORGN_CLSF_CD"] == "CM015.110"
    assert data["_runningNana"] == "nana"
    assert data["_runningMainOpenKey"] == "open-key"
    assert data["_runningLoginIdenNo"] == "login-iden"


def test_decode_response_rejects_logout_error_payload() -> None:
    client = DonggukClient(session=cast(requests.Session, cast(object, FakeSession([]))))

    try:
        client._decode_response(
            LOAD_URL,
            make_response(
                body='{"ERRMSGINFO": {"STATUSCODE": -3000, "ERRMSG": "로그인 후 잘못된 방법으로 데이터 요청이 수행되어 로그아웃 처리 되었습니다."}}'
            ),
        )
    except DonggukAuthenticationError as exc:
        assert "auth-like error payload" in str(exc)
    else:
        raise AssertionError("Expected logout payload to be treated as an authentication error.")
