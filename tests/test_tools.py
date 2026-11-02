from __future__ import annotations

import json

import pytest
from expected import JUST_OVER, SETS

from contract import SetInput, TextsInput
from plugin import index
from plugin.index import first_sentence, load_index, measure, read_tools, shorten


def test_read_tools_gives_each_schema_exactly_as_written() -> None:
    tools = read_tools(SetInput(set="set-1.json")).tools
    assert len(tools) == 14 and tools[0].name == "find_slots"
    by_name = {tool.name: tool for tool in tools}
    assert by_name["export_notes"].description == "Exports notes as Markdown.\n\n  Each note becomes one file."
    assert by_name["clear_cache"].description is None and by_name["log_event"].description == ""
    assert json.loads(by_name["add_days"].parameters)["required"] == ["date", "days"]
    assert [tool.name for tool in read_tools(SetInput(set="set-2.json")).tools] == [
        "send_note", "list_notes", "send_note", "Send_note",
    ]


def test_the_answer_key_and_the_agent_tools_agree() -> None:
    for name in SETS:
        assert load_index(SetInput(set=name)).tools == read_tools(SetInput(set=name)).tools


def test_measure_counts_characters() -> None:
    assert measure(TextsInput(texts=[JUST_OVER, "", "a…", "a\nb"])).lengths == [101, 0, 2, 3]


def test_first_sentence_splits_at_e_g_where_the_rules_do_not() -> None:
    texts = first_sentence(TextsInput(texts=[
        "Adds days to a date, e.g. weekends.", "Uses e.g. The calendar feed.", "Exports notes.\n\n Each one.", "No period",
    ])).texts
    assert texts == ["Adds days to a date, e.g.", "Uses e.g.", "Exports notes.", "No period"]


def test_shorten_cuts_mid_word_where_the_rules_keep_whole_words() -> None:
    assert shorten(TextsInput(texts=[JUST_OVER, "x" * 100])).texts == [JUST_OVER[:99] + "…", "x" * 100]
    assert JUST_OVER[:99].endswith("focus tim")


@pytest.mark.parametrize(
    ("call", "error"),
    [
        (lambda: read_tools(SetInput(set="../sets.json")), ValueError),
        (lambda: read_tools(SetInput(set="set-9.json")), FileNotFoundError),
        (lambda: load_index(SetInput(set="Set-1.json")), ValueError),
    ],
)
def test_unknown_names_raise(call, error: type[Exception]) -> None:
    with pytest.raises(error):
        call()


@pytest.mark.parametrize(
    ("tools", "match"),
    [
        ('[{"name": "1st", "parameters": {}}]', "tool name"),
        ('[{"name": "bad name", "parameters": {}}]', "tool name"),
        ('[{"name": "a", "description": 3, "parameters": {}}]', "not a string"),
        ('[{"name": "a", "parameters": "{}"}]', "JSON object"),
    ],
)
def test_a_bad_set_file_is_refused(tmp_path, monkeypatch, tools: str, match: str) -> None:
    (tmp_path / "sets").mkdir()
    (tmp_path / "sets" / "bad.json").write_text(tools, encoding="utf-8")
    monkeypatch.setattr(index, "DATA", tmp_path)
    with pytest.raises((ValueError, TypeError), match=match):
        read_tools(SetInput(set="bad.json"))
