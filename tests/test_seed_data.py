from k_univ_mcp.providers.yonsei.models import YonseiDepartmentRow, YonseiSeedDataError


def test_department_row_requires_code_and_name() -> None:
    try:
        YonseiDepartmentRow.from_payload({"deptCd": "s1"})
    except YonseiSeedDataError as exc:
        assert "deptCd" in str(exc) or "deptNm" in str(exc)
    else:
        raise AssertionError("Expected malformed seed row to be rejected.")
