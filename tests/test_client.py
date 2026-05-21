import json

from requests import Response
from typing import cast

import requests

from k_univ_mcp.providers.yonsei.client import FACULTIES_PATH, YonseiAuthenticationError, YonseiClient


class FakeSession:
    def __init__(self, responses: list[Response]) -> None:
        self.responses = responses
        self.headers: dict[str, str] = {}
        self.cookies: dict[str, str] = {}
        self.calls: list[tuple[str, dict[str, str], int]] = []

    def post(self, url: str, data: dict[str, str], timeout: int) -> Response:
        self.calls.append((url, data, timeout))
        if not self.responses:
            raise AssertionError("No fake responses left for YonseiClient test.")
        return self.responses.pop(0)


def make_response(*, status_code: int = 200, content_type: str = "application/json", body: str = "{}") -> Response:
    response = Response()
    response.status_code = status_code
    response.headers["content-type"] = content_type
    response._content = body.encode("utf-8")
    return response


def test_decode_response_raises_auth_error_for_html_body() -> None:
    client = YonseiClient(cookie_header="JSESSIONID=test; NetFunnel_ID=test")
    response = make_response(content_type="text/html; charset=UTF-8", body="<html><body>login</body></html>")

    try:
        client._decode_response("/example", response)
    except YonseiAuthenticationError as exc:
        assert "HTML instead of JSON" in str(exc)
    else:
        raise AssertionError("Expected HTML response to be classified as an authentication/session failure.")


def test_post_refreshes_and_retries_after_json_parse_failure() -> None:
    refreshes: list[str] = []
    session = FakeSession(
        [
            make_response(body="not-json"),
            make_response(body=json.dumps({"dsFaclyCd": [{"deptCd": "0301", "deptNm": "수학전공"}]})),
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=stale; NetFunnel_ID=stale",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
        refresh_cookie_header=lambda: refreshes.append("refreshed") or "JSESSIONID=fresh; NetFunnel_ID=fresh",
    )

    payload = client._post(FACULTIES_PATH, {"@d1#univCd": "s1103"})

    assert payload["dsFaclyCd"][0]["deptCd"] == "0301"
    assert refreshes == ["refreshed"]
    assert len(session.calls) == 2
    assert client.cookie_header == "JSESSIONID=fresh; NetFunnel_ID=fresh"


def test_post_refreshes_after_auth_like_json_payload() -> None:
    refreshes: list[str] = []
    session = FakeSession(
        [
            make_response(body=json.dumps({"resultMsg": "Session expired. Please login again."})),
            make_response(body=json.dumps({"dsFaclyCd": [{"deptCd": "0301", "deptNm": "수학전공"}]})),
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=stale; NetFunnel_ID=stale",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
        refresh_cookie_header=lambda: refreshes.append("refreshed") or "JSESSIONID=fresh; NetFunnel_ID=fresh",
    )

    departments = client.list_faculties("2026", "10", "s1", "s1103")

    assert departments[0]["deptCd"] == "0301"
    assert refreshes == ["refreshed"]
    assert len(session.calls) == 2


def test_post_bootstraps_before_first_request_when_cookie_header_is_empty() -> None:
    refreshes: list[str] = []
    session = FakeSession(
        [
            make_response(body=json.dumps({"dsUnivCd": [{"deptCd": "s1103", "deptNm": "이과대학"}]})),
        ]
    )
    client = YonseiClient(
        cookie_header="",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
        refresh_cookie_header=lambda: refreshes.append("refreshed") or "JSESSIONID=fresh; NetFunnel_ID=fresh",
    )

    colleges = client.list_universities("2026", "10", "s1")

    assert colleges[0]["deptCd"] == "s1103"
    assert refreshes == ["refreshed"]
    assert len(session.calls) == 1
    assert client.cookie_header == "JSESSIONID=fresh; NetFunnel_ID=fresh"


def test_apply_cookie_header_replaces_stale_cookies_instead_of_merging() -> None:
    client = YonseiClient(cookie_header="JSESSIONID=stale; NetFunnel_ID=stale; OLD_COOKIE=legacy")

    client._apply_cookie_header("JSESSIONID=fresh; NetFunnel_ID=fresh")

    assert client.session is not None
    cookies = client.session.cookies.get_dict()
    assert cookies["JSESSIONID"] == "fresh"
    assert cookies["NetFunnel_ID"] == "fresh"
    assert "OLD_COOKIE" not in cookies


def test_list_campuses_uses_live_discovery_endpoint_with_semester_scoped_payload() -> None:
    session = FakeSession(
        [
            make_response(
                body=json.dumps({"dsCampsBusnsCd": [{"deptCd": "s1", "deptNm": "신촌캠퍼스"}]})
            )
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=test; NetFunnel_ID=test",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
    )

    campuses = client.list_campuses("2026", "11")

    assert campuses[0]["deptCd"] == "s1"
    assert len(session.calls) == 1
    _, data, _ = session.calls[0]
    assert data["@d1#dsNm"] == "dsCampsBusnsCd"
    assert data["@d1#lv1"] == "%"
    assert data["@d1#lv2"] == "%"
    assert data["@d1#lv3"] == "%"
    assert data["@d1#univGbn"] == "A"
    assert data["@d1#findAuthGbn"] == "8"
    assert data["@d1#syy"] == "2026"
    assert data["@d1#smtDivCd"] == "11"


def test_list_universities_uses_live_discovery_endpoint_with_semester_and_campus() -> None:
    session = FakeSession(
        [
            make_response(
                body=json.dumps({"dsUnivCd": [{"deptCd": "s1103", "deptNm": "이과대학"}]})
            )
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=test; NetFunnel_ID=test",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
    )

    colleges = client.list_universities("2026", "11", "s1")

    assert colleges[0]["deptCd"] == "s1103"
    assert len(session.calls) == 1
    _, data, _ = session.calls[0]
    assert data["@d1#dsNm"] == "dsUnivCd"
    assert data["@d1#lv1"] == "s1"
    assert data["@d1#lv2"] == "%"
    assert data["@d1#lv3"] == "%"
    assert data["@d1#syy"] == "2026"
    assert data["@d1#smtDivCd"] == "11"


def test_list_faculties_uses_live_discovery_endpoint_with_semester_campus_and_college() -> None:
    session = FakeSession(
        [
            make_response(
                body=json.dumps({"dsFaclyCd": [{"deptCd": "0301", "deptNm": "수학전공"}]})
            )
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=test; NetFunnel_ID=test",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
    )

    departments = client.list_faculties("2026", "10", "s1", "s1103")

    assert departments[0]["deptCd"] == "0301"
    assert len(session.calls) == 1
    _, data, _ = session.calls[0]
    assert data["@d1#dsNm"] == "dsFaclyCd"
    assert data["@d1#lv1"] == "s1"
    assert data["@d1#lv2"] == "s1103"
    assert data["@d1#lv3"] == "%"
    assert data["@d1#syy"] == "2026"
    assert data["@d1#smtDivCd"] == "10"


def test_list_faculties_uses_fallback_department_list_when_primary_key_is_empty() -> None:
    session = FakeSession(
        [
            make_response(
                body=json.dumps(
                    {
                        "dsFaclyCd": [],
                        "dsFaclyAlt": [{"deptCd": "0301", "deptNm": "수학전공"}],
                    }
                )
            )
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=test; NetFunnel_ID=test",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
    )

    departments = client.list_faculties("2026", "10", "s1", "s1103")

    assert departments == [{"deptCd": "0301", "deptNm": "수학전공"}]
    assert len(session.calls) == 1


def test_list_faculties_refreshes_after_abnormal_empty_payload() -> None:
    refreshes: list[str] = []
    session = FakeSession(
        [
            make_response(body=json.dumps({"dsFaclyCd": []})),
            make_response(body=json.dumps({"dsFaclyCd": [{"deptCd": "0301", "deptNm": "수학전공"}]})),
        ]
    )
    client = YonseiClient(
        cookie_header="JSESSIONID=stale; NetFunnel_ID=stale",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
        refresh_cookie_header=lambda: refreshes.append("refreshed") or "JSESSIONID=fresh; NetFunnel_ID=fresh",
    )

    departments = client.list_faculties("2026", "10", "s1", "s1103")

    assert departments[0]["deptCd"] == "0301"
    assert refreshes == ["refreshed"]
    assert len(session.calls) == 2


def test_list_courses_does_not_refresh_for_plain_empty_results() -> None:
    refreshes: list[str] = []
    session = FakeSession([make_response(body=json.dumps({"dsSlessyList": []}))])
    client = YonseiClient(
        cookie_header="JSESSIONID=stable; NetFunnel_ID=stable",
        session=cast(requests.Session, cast(object, session)),
        sleep_seconds=0,
        refresh_cookie_header=lambda: refreshes.append("unexpected") or "JSESSIONID=fresh; NetFunnel_ID=fresh",
    )

    courses = client.list_courses("2026", "10", "s1", "s1103", "0301")

    assert courses == []
    assert refreshes == []
    assert len(session.calls) == 1


def test_refresh_gate_skips_duplicate_bootstrap_when_cookie_already_changed() -> None:
    refreshes: list[str] = []
    client = YonseiClient(
        cookie_header="JSESSIONID=stale; NetFunnel_ID=stale",
        sleep_seconds=0,
        refresh_cookie_header=lambda: refreshes.append("unexpected") or "JSESSIONID=new; NetFunnel_ID=new",
    )
    client._apply_cookie_header("JSESSIONID=fresh; NetFunnel_ID=fresh")
    refreshed = client._refresh_session_if_needed("JSESSIONID=stale; NetFunnel_ID=stale")

    assert refreshed is True
    assert refreshes == []
