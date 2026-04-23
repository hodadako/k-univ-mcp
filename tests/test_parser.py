from k_univ_mcp.providers.yonsei.parser import parse_meeting_slots


def test_parse_meeting_slots_handles_compound_patterns() -> None:
    slots, warnings = parse_meeting_slots("월6,7,수6")
    assert warnings == []
    assert [(slot.day_code, slot.period) for slot in slots] == [("MON", 6), ("MON", 7), ("WED", 6)]


def test_parse_meeting_slots_handles_parentheses_and_slashes() -> None:
    slots, warnings = parse_meeting_slots("목6(목7,8,9,10)")
    assert warnings == []
    assert [(slot.day_code, slot.period) for slot in slots] == [
        ("THU", 6),
        ("THU", 7),
        ("THU", 8),
        ("THU", 9),
        ("THU", 10),
    ]


def test_parse_meeting_slots_preserves_nonfatal_warnings() -> None:
    slots, warnings = parse_meeting_slots("수1,2(미정)")
    assert [(slot.day_code, slot.period) for slot in slots] == [("WED", 1), ("WED", 2)]
    assert warnings == ["Unparsed time token: 미정"]
