from app.core.llm import parse_json_object


def test_parse_plain_object():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_fenced_json():
    assert parse_json_object("```json\n{\"verdict\": \"supported\"}\n```")["verdict"] == "supported"


def test_parse_prose_wrapped_json():
    text = 'Sure, here you go:\n{"queries": ["a", "b"]}\nHope that helps.'
    assert parse_json_object(text)["queries"] == ["a", "b"]


def test_parse_garbage_returns_empty():
    assert parse_json_object("not json at all") == {}
