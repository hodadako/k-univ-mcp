from k_univ_mcp.semester import (
    normalize_provider_semester,
    semester_display_label,
    semester_display_name,
    semester_help_text,
)


def test_normalize_provider_semester_maps_unified_inputs() -> None:
    assert normalize_provider_semester("yonsei", "1") == "10"
    assert normalize_provider_semester("yonsei", "summer") == "15"
    assert normalize_provider_semester("gachon", "winter") == "25"
    assert normalize_provider_semester("dongguk", "summer") == "여름학기"
    assert normalize_provider_semester("sungshin", "2") == "COMM063.20"
    assert normalize_provider_semester("soongsil", "winter") == "겨울학기"
    assert normalize_provider_semester("hanyang", "2") == "20"
    assert normalize_provider_semester("inha", "1") == "1"


def test_normalize_provider_semester_keeps_legacy_codes() -> None:
    assert normalize_provider_semester("dongguk", "CM160.10") == "CM160.10"
    assert normalize_provider_semester("sungshin", "COMM063.10") == "COMM063.10"
    assert normalize_provider_semester("yonsei", "10") == "10"


def test_semester_display_helpers_convert_provider_codes_to_labels() -> None:
    assert semester_display_label("COMM063.10") == "1학기"
    assert semester_display_label("10") == "1학기"
    assert semester_display_label("2026-1학기") == "1학기"
    assert semester_display_label("2026학년도 1학기") == "1학기"
    assert semester_display_label("여름학기") == "여름학기"
    assert semester_display_name("COMM063.10", year="2026") == "1학기"


def test_semester_help_mentions_unified_inputs() -> None:
    help_text = semester_help_text()
    assert "summer" in help_text
    assert "winter" in help_text
