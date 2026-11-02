"""Both implementations of the rules (the plugin's and the verifier's) against the hand-derived answers."""

from __future__ import annotations

import pytest
from expected import EXACTLY_100, JUST_OVER, SETS

from contract import SetInput, ToolSchema
from plugin import rules as plugin_rules
from plugin.index import load_index, read_tools
from verifier import rules as verifier_rules


def both(description: str | None) -> str:
    """The summary of ``description`` under both implementations, which must agree."""
    plugin, verifier = plugin_rules.summary(description), verifier_rules.steps(description)[2]
    assert plugin == verifier, (plugin, verifier)
    return plugin


@pytest.mark.parametrize("name", sorted(SETS))
def test_the_plugin_builds_each_index_as_derived_by_hand(name: str) -> None:
    key = load_index(SetInput(set=name))
    assert {"valid": key.valid, "duplicates": key.duplicates, "entries": key.entries} == SETS[name]


@pytest.mark.parametrize("name", sorted(SETS))
def test_the_verifier_builds_each_index_as_derived_by_hand(name: str) -> None:
    valid, twice, entries = verifier_rules.rebuilt(read_tools(SetInput(set=name)).tools)
    assert {"valid": valid, "duplicates": sorted(twice), "entries": entries} == SETS[name]


def test_the_boundary_texts_have_the_lengths_they_claim() -> None:
    assert len(EXACTLY_100) == 100 and len(JUST_OVER) == 101
    assert len(SETS["set-1.json"]["entries"][6].removeprefix("find_slots: ")) == 96
    assert len(SETS["set-1.json"]["entries"][7].removeprefix("hash_blob: ")) == 100


# One description at a time, against both implementations.
@pytest.mark.parametrize(
    ("description", "summary"),
    [
        (EXACTLY_100 + " More.", EXACTLY_100),  # exactly 100: kept
        (JUST_OVER, JUST_OVER[:95] + "…"),  # 101: whole words within 99
        ("a" * 99 + " b" * 5, "a" * 99 + "…"),  # the first word fills 99 exactly
        ("a" * 100 + " b", "a" * 99 + "…"),  # the first word alone is over 99
        ("a" * 100, "a" * 100),  # one word of exactly 100: kept
        ("a" * 98 + " b " + "c" * 10, "a" * 98 + "…"),  # "b" would make 100, one too many
        ("No period here", "No period here"),
        ("Adds days, e.g. weekends.", "Adds days, e.g. weekends."),
        ("Uses e.g. The calendar.", "Uses e.g."),
        ("Ends here.Next starts.", "Ends here.Next starts."),  # no space after the period
        ("Ends here. 2 more follow.", "Ends here. 2 more follow."),  # a digit is not an uppercase letter
        ("Ends here. Émile says hi.", "Ends here. Émile says hi."),  # only A to Z count
        ("Ends here.  Next one.", "Ends here."),  # double space collapses first, then splits
        ("Ends here.\nNext one.", "Ends here."),
        ("Really? Yes! Done. Next.", "Really? Yes! Done."),
        ("  Padded\t\ttext.  ", "Padded text."),
        ("", "(no description)"),
        (None, "(no description)"),
        ("\n \t", "(no description)"),
        ("…" * 101, "…" * 99 + "…"),  # the ellipsis is one character
    ],
)
def test_both_implementations_agree_on_each_boundary(description: str | None, summary: str) -> None:
    assert both(description) == summary
    assert len(summary) <= 100


@pytest.mark.parametrize(
    ("names", "order"),
    [
        (["b", "A", "a", "B"], ["A", "a", "B", "b"]),
        (["Zeta_sync", "alpha_sync"], ["alpha_sync", "Zeta_sync"]),
        (["ab", "a_b", "aB"], ["a_b", "aB", "ab"]),  # "_" sorts before letters once lowercased
        (["send_note", "Send_note"], ["Send_note", "send_note"]),
    ],
)
def test_both_implementations_order_names_alike(names: list[str], order: list[str]) -> None:
    tools = [ToolSchema(name=name, description="x", parameters="{}") for name in names]
    assert [entry.split(": ")[0] for entry in verifier_rules.rebuilt(tools)[2]] == order
    assert [entry.split(": ")[0] for entry in plugin_rules.index([(name, "x") for name in names])[2]] == order


def test_a_duplicate_name_makes_the_set_invalid_for_both() -> None:
    names = ["send_note", "Send_note", "send_note", "list_notes", "list_notes"]
    assert plugin_rules.index([(name, "x") for name in names]) == (False, ["list_notes", "send_note"], [])
    tools = [ToolSchema(name=name, description="x", parameters="{}") for name in names]
    assert verifier_rules.rebuilt(tools) == (False, {"list_notes", "send_note"}, [])
