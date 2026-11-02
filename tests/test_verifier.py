from __future__ import annotations

import copy
import json
import random

import pytest
from expected import JUST_OVER, SETS, answer
from slimconfig import build_output, plain_output

import verifier
from contract import IndexOutput, KeyOutput, LengthsOutput, SetInput, TextsInput, TextsOutput, Tool, ToolsOutput
from plugin.index import first_sentence, load_index, measure, read_tools, shorten

IDS = [
    "answer-key", "answer-key-rules", "submitted-set", "entries-shaped",
    "validity-exact", "entries-complete", "summaries-exact", "order-exact",
]


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def key_json(name: str) -> dict:
    return plain_output(load_index(SetInput(set=name)))


def judge(name: str, submitted: dict, key: dict | None = None, arguments: str | None = None) -> dict:
    reference = build_output(key_json(name) if key is None else key, KeyOutput)
    given = build_output({"set": arguments or name}, SetInput)
    return verifier.verify_task("build-index", given, build_output(submitted, IndexOutput), reference, ".")


def failing(verdict: dict) -> list[str]:
    return [entry["id"] for entry in verdict["details"]["constraints"] if entry["ok"] is False]


def set_summary(submitted: dict, name: str, text: str) -> None:
    submitted["entries"] = [f"{name}: {text}" if entry.split(": ")[0] == name else entry for entry in submitted["entries"]]


def test_every_tool_resolves_to_a_module_with_both_checks() -> None:
    # The host calls verify_input and verify_output on every tool call; a missing one only fails a real run.
    assert set(verifier.TOOLS) == set(Tool)
    for module in verifier.TOOLS.values():
        assert callable(module.verify_input) and callable(module.verify_output)


# Correct.
@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("set-1.json", "All 8 checks hold: 14 tools indexed, 2 summaries cut, 3 without a description."),
        ("set-2.json", "All 8 checks hold: set-2.json is invalid: send_note names more than one tool."),
    ],
)
def test_the_hand_derived_answer_holds_every_constraint(name: str, message: str) -> None:
    verdict = judge(name, answer(name))
    assert verdict["valid"] is True and verdict["score"] == 1.0 and verdict["message"] == message
    assert [entry["id"] for entry in verdict["details"]["constraints"]] == IDS


def test_each_tool_approves_its_own_real_output() -> None:
    one = build_output({"set": "set-1.json"}, SetInput)
    texts = build_output({"texts": [JUST_OVER, "Uses e.g. The calendar.", "a.  B"]}, TextsInput)
    cases = [
        ("load_index", one, load_index(one), KeyOutput),
        ("read_tools", one, read_tools(one), ToolsOutput),
        ("measure", texts, measure(texts), LengthsOutput),
        ("first_sentence", texts, first_sentence(texts), TextsOutput),
        ("shorten", texts, shorten(texts), TextsOutput),
    ]
    for tool, given, made, cls in cases:
        assert verifier.verify_input(tool, given)["valid"] is True, tool
        verdict = verifier.verify_output(tool, given, build_output(plain_output(made), cls), ".")
        assert verdict["valid"] is True, (tool, verdict["message"])


# Wrong and boundary: each trap set-1 is built around fails summaries-exact with the rule it breaks.
@pytest.mark.parametrize(
    ("name", "text", "why"),
    [
        (  # "e.g." then lowercase
            "add_days", "Adds days to a date, e.g.",
            "it ends at a period not followed by a space and an uppercase letter, which ends no sentence (rule 2)",
        ),
        (  # "e.g." then uppercase
            "pick_source", "Uses e.g. The calendar feed.",
            "the summary is only the first sentence, which ends at the first period followed by a space and an uppercase letter (rule 2)",
        ),
        (  # newlines and double spaces
            "export_notes", "Exports notes as Markdown. Each note becomes one file.",
            "the summary is only the first sentence, which ends at the first period followed by a space and an uppercase letter (rule 2)",
        ),
        (
            "Export_notes", "Exports  notes as plain text, one file per folder.",
            "its whitespace is not collapsed to single spaces (rule 1)",
        ),
        (  # 101 characters
            "find_slots", JUST_OVER[:99] + "…", "it is cut mid-word, but the rules keep only whole words (rule 3)",
        ),
        ("find_slots", JUST_OVER, "the first sentence has 101 characters, over 100, so it is cut (rule 3)"),
        (  # exactly 100 characters
            "merge_contacts", "Merges duplicate contacts that share one email address or phone number, then keeps the newest…",
            "the first sentence has 100 characters, at most 100, so it is kept as is (rule 3)",
        ),
        (  # a word longer than 99
            "hash_blob", "0123456789" * 9 + "…",  # cut at 90, as if at a word boundary inside the word
            "",
        ),
        ("log_event", "No description.", "an empty or missing description gives '(no description)' (rule 4)"),  # empty
        ("clear_cache", "Clears the cache.", "an empty or missing description gives '(no description)' (rule 4)"),  # missing
        ("noop", "(none)", "an empty or missing description gives '(no description)' (rule 4)"),  # whitespace only
        ("ping_service", "(no description)", "the description is not empty"),
        ("ping_service", "Checks that the service is up and answering.", ""),  # no period: nothing is added
    ],
)
def test_each_trap_fails_summaries_exact_with_the_reason(name: str, text: str, why: str) -> None:
    submitted = answer("set-1.json")
    want = next(entry for entry in submitted["entries"] if entry.startswith(name + ": ")).removeprefix(name + ": ")
    set_summary(submitted, name, text)
    verdict = judge("set-1.json", submitted)
    assert failing(verdict) == ["summaries-exact"]
    assert verdict["message"] == (
        f"summaries-exact: {name} is summarised {text!r}, but the rules give {want!r}" + (f"; {why}" if why else "")
    )
    assert verdict["score"] == pytest.approx(13 / 14)


@pytest.mark.parametrize(
    ("swap", "message", "score"),
    [
        (  # two names differing only in case
            (4, 5),
            (
                "order-exact: export_notes is listed before Export_notes, but names that differ only in case go by"
                " their exact name, and 'Export_notes' comes before 'export_notes'"
            ),
            13 / 14,
        ),
        (
            (12, 13),
            (
                "order-exact: Zeta_sync is listed before ping_service, but names go by their lowercased name,"
                " and 'ping_service' comes before 'zeta_sync'"
            ),
            13 / 14,
        ),
    ],
)
def test_a_wrong_order_fails_order_exact(swap: tuple[int, int], message: str, score: float) -> None:
    submitted = answer("set-1.json")
    entries = submitted["entries"]
    entries[swap[0]], entries[swap[1]] = entries[swap[1]], entries[swap[0]]
    verdict = judge("set-1.json", submitted)
    assert failing(verdict) == ["order-exact"] and verdict["message"] == message
    assert verdict["score"] == pytest.approx(score)


def test_a_case_sensitive_sort_is_caught() -> None:
    submitted = answer("set-1.json")
    submitted["entries"].sort()
    verdict = judge("set-1.json", submitted)
    assert failing(verdict) == ["order-exact"]
    assert verdict["message"] == (
        "order-exact: Export_notes is listed before add_days, but names go by their lowercased name,"
        " and 'add_days' comes before 'export_notes'"
    )
    assert verdict["score"] == pytest.approx(12 / 14)  # Export_notes and Zeta_sync are out of place


def test_trusting_both_distractors_is_caught() -> None:
    tools = {tool.name: tool.description for tool in read_tools(SetInput(set="set-1.json")).tools}
    names = [entry.split(": ")[0] for entry in answer("set-1.json")["entries"]]
    cut = shorten(first_sentence(TextsInput(texts=[tools[name] or "" for name in names])))
    entries = [f"{name}: {text or '(no description)'}" for name, text in zip(names, cut.texts)]
    verdict = judge("set-1.json", {"set": "set-1.json", "valid": True, "duplicates": [], "entries": entries})
    assert failing(verdict) == ["summaries-exact"]
    assert verdict["details"]["constraints"][6]["expected"] == [
        "add_days: Adds days to a date, e.g. weekends.",
        "find_slots: Finds open meeting slots across every invited calendar, skipping holidays and any blocked focus…",
    ]
    assert verdict["score"] == pytest.approx(12 / 14)


# Validity and duplicates (set-2).
@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {"valid": True, "duplicates": [], "entries": ["list_notes: Lists notes in a folder."]},
            "validity-exact: the set is reported valid, but send_note names more than one tool (+1 more)",
        ),
        (  # names differing only in case are not duplicates
            {"duplicates": ["Send_note", "send_note"]},
            "validity-exact: the duplicate names are ['Send_note', 'send_note'], but the rules give ['send_note']",
        ),
    ],
)
def test_a_wrong_validity_scores_zero(change: dict, message: str) -> None:
    submitted = answer("set-2.json")
    submitted.update(change)
    verdict = judge("set-2.json", submitted)
    assert verdict["message"] == message and verdict["score"] == 0.0


def test_calling_a_valid_set_invalid_scores_zero() -> None:
    submitted = {"set": "set-1.json", "valid": False, "duplicates": ["export_notes"], "entries": []}
    verdict = judge("set-1.json", submitted)
    assert failing(verdict) == ["validity-exact", "entries-complete"] and verdict["score"] == 0.0
    assert verdict["message"].startswith("validity-exact: the set is reported invalid, but no two tools share a name")


# Missing.
def test_a_dropped_or_extra_entry_fails_entries_complete() -> None:
    submitted = answer("set-1.json")
    submitted["entries"].pop(3)
    verdict = judge("set-1.json", submitted)
    assert failing(verdict) == ["entries-complete"] and verdict["score"] == pytest.approx(13 / 14)
    assert verdict["message"] == "entries-complete: clear_cache has no entry: the rules give 'clear_cache: (no description)'"
    submitted = answer("set-1.json")
    submitted["entries"].insert(12, "Ping_service: Checks that the service is up and answering")
    verdict = judge("set-1.json", submitted)
    assert verdict["message"] == (
        "entries-complete: Ping_service has an entry, but set-1.json has no tool 'Ping_service' (names are case-sensitive)"
    )
    assert verdict["score"] == pytest.approx(14 / 15)


def test_an_empty_index_for_a_valid_set_scores_zero() -> None:
    verdict = judge("set-1.json", {"set": "set-1.json", "valid": True, "duplicates": [], "entries": []})
    assert failing(verdict) == ["entries-complete"] and verdict["score"] == 0.0
    assert verdict["details"]["constraints"][5]["expected"][-1] == "... 8 more"


# Malformed: gates that score 0.
@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: s.update(set="set-2.json"), "submitted-set: the submission is for 'set-2.json', not 'set-1.json'"),
        (lambda s: s["entries"].__setitem__(0, "add_days - Adds days"), "entries-shaped: 'add_days - Adds days' is not an entry"),
        (lambda s: s["entries"].__setitem__(0, "add_days: "), "entries-shaped: 'add_days: ' is not an entry"),
        (lambda s: s["entries"].__setitem__(0, "add days: Adds"), "entries-shaped: 'add days: Adds' is not an entry"),
        (lambda s: s["entries"].append(s["entries"][0]), "entries-shaped: add_days has more than one entry"),
        (lambda s: s.update(valid=False), "entries-shaped: the set is reported invalid with no duplicate names"),
        (lambda s: s.update(duplicates=["noop"]), "entries-shaped: the set is reported valid with duplicate names"),
        (
            lambda s: s.update(valid=False, duplicates=["noop"]),
            "entries-shaped: an invalid set has no index, and this gives entries",
        ),
    ],
)
def test_a_malformed_submission_fails_its_gate_and_scores_zero(change, message: str) -> None:
    submitted = answer("set-1.json")
    change(submitted)
    verdict = judge("set-1.json", submitted)
    assert verdict["valid"] is False and verdict["score"] == 0.0
    assert verdict["message"].startswith(message), verdict["message"]
    later = verdict["details"]["constraints"][IDS.index(failing(verdict)[0]) + 1 :]
    assert all(entry["ok"] is None and entry["message"].startswith("Not checked") for entry in later)


def test_duplicate_names_given_twice_are_malformed() -> None:
    submitted = answer("set-2.json")
    submitted["duplicates"] = ["send_note", "send_note"]
    assert judge("set-2.json", submitted)["message"] == "entries-shaped: a duplicate name is given twice: give each once"


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.update(valid="true"),
        lambda s: s.pop("duplicates"),
        lambda s: s.update(entries="add_days: Adds days"),
        lambda s: s.update(entries=[{"name": "add_days"}]),
    ],
)
def test_a_submission_outside_the_contract_never_reaches_the_verifier(change) -> None:
    # Unreachable in verify_task: build_output checks the contract first, as the sandbox does.
    submitted = answer("set-1.json")
    change(submitted)
    with pytest.raises((TypeError, ValueError, KeyError)):
        build_output(submitted, IndexOutput)


# The answer key.
def test_no_answer_key_fails_first() -> None:
    given = build_output({"set": "set-1.json"}, SetInput)
    verdict = verifier.verify_task("build-index", given, build_output(answer("set-1.json"), IndexOutput), None, ".")
    assert verdict["message"] == "answer-key: No answer key: load_index never ran for this task." and verdict["score"] == 0.0
    assert [entry["ok"] for entry in verdict["details"]["constraints"]] == [False] + [None] * 7


def test_an_answer_key_for_another_set_fails() -> None:
    verdict = judge("set-1.json", answer("set-1.json"), arguments="set-2.json")
    assert verdict["message"] == "answer-key: The answer key is for 'set-1.json', not 'set-2.json'."


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda k: k["tools"][0].update(parameters="[]"), "answer-key: find_slots's parameters are not a JSON object"),
        (lambda k: k["tools"][0].update(parameters="{"), "answer-key: find_slots's parameters are not a JSON object"),
        (lambda k: k["tools"][0].update(name="find slots"), "answer-key: 'find slots' is not a tool name"),
        (lambda k: k.update(valid=False), "answer-key: the set is reported invalid with no duplicate names"),
    ],
)
def test_a_malformed_answer_key_fails_first(change, message: str) -> None:
    key = key_json("set-1.json")
    change(key)
    verdict = judge("set-1.json", answer("set-1.json"), key=key)
    assert failing(verdict) == ["answer-key"] and verdict["message"].startswith(message), verdict["message"]


@pytest.mark.parametrize(
    ("name", "change", "message"),
    [
        (
            "set-1.json", lambda k: k["entries"].__setitem__(7, "hash_blob: x"),
            "answer-key-rules: the answer key's index differs from the rules' recomputation at 'hash_blob: x'",
        ),
        (
            "set-1.json", lambda k: k["entries"].sort(),
            "answer-key-rules: the answer key's index differs from the rules' recomputation at 'its order'",
        ),
        (
            "set-2.json", lambda k: k.update(duplicates=["list_notes"]),
            "answer-key-rules: the answer key's validity or duplicates differ from the rules' recomputation",
        ),
    ],
)
def test_a_tampered_answer_key_fails_its_rules_check(name: str, change, message: str) -> None:
    key = key_json(name)
    change(key)
    verdict = judge(name, answer(name), key=key)
    assert verdict["message"] == message
    given = build_output({"set": name}, SetInput)
    assert verifier.verify_output("load_index", given, build_output(key, KeyOutput), ".")["valid"] is False


# The tools' own checks.
def test_tool_inputs_are_checked() -> None:
    assert verifier.verify_input("read_tools", build_output({"set": "../set-1.json"}, SetInput))["valid"] is False
    assert verifier.verify_input("measure", build_output({"texts": []}, TextsInput))["valid"] is False
    assert verifier.verify_input("shorten", build_output({"texts": ["x"] * 31}, TextsInput))["valid"] is False
    assert verifier.verify_input("first_sentence", build_output({"texts": ["x" * 2001]}, TextsInput))["valid"] is False


@pytest.mark.parametrize(
    ("tool", "given", "made", "input_class", "cls"),
    [
        ("read_tools", {"set": "set-1.json"}, {"set": "set-2.json", "tools": []}, SetInput, ToolsOutput),
        (
            "read_tools", {"set": "set-1.json"},
            {"set": "set-1.json", "tools": [{"name": "a", "description": None, "parameters": "[]"}]}, SetInput, ToolsOutput,
        ),
        ("measure", {"texts": ["a…"]}, {"lengths": [4]}, TextsInput, LengthsOutput),  # bytes, not characters
        ("first_sentence", {"texts": ["a. B", "c"]}, {"texts": ["a."]}, TextsInput, TextsOutput),
        ("first_sentence", {"texts": ["a b. C"]}, {"texts": ["a b"]}, TextsInput, TextsOutput),
        ("shorten", {"texts": ["x" * 101]}, {"texts": ["x" * 101]}, TextsInput, TextsOutput),
        ("shorten", {"texts": ["x" * 101]}, {"texts": ["y…"]}, TextsInput, TextsOutput),
    ],
)
def test_a_wrong_tool_output_is_refused(tool, given, made, input_class, cls) -> None:
    verdict = verifier.verify_output(tool, build_output(given, input_class), build_output(made, cls), ".")
    assert verdict["valid"] is False


# Determinism, size and robustness.
def test_the_verdict_is_deterministic_and_small() -> None:
    empty = {"set": "set-1.json", "valid": True, "duplicates": [], "entries": []}
    first, second = judge("set-1.json", empty), judge("set-1.json", empty)
    assert first == second
    assert len(json.dumps(first)) < 8_000


def mutate(value, rng: random.Random):
    """``value`` with one random change somewhere inside it."""
    if isinstance(value, dict) and value:
        key = rng.choice(sorted(value))
        return {**value, key: mutate(value[key], rng)}
    if isinstance(value, list) and value and rng.random() < 0.7:
        index = rng.randrange(len(value))
        choice = rng.random()
        if choice < 0.3:
            return value[:index] + value[index + 1 :]
        if choice < 0.5:
            return [*value, copy.deepcopy(value[index])]
        if choice < 0.6:
            return list(reversed(value))
        return value[:index] + [mutate(value[index], rng)] + value[index + 1 :]
    # Mostly a value of the same type, so most mutations reach the verifier rather than build_output's refusal.
    same = {
        str: ["", "a", "noop", "send_note", "Send_note", "noop: x", "noop: (no description)", ": x", "a: b: c",
              "{}", "[]", "{", "set-1.json", "set-2.json", "x" * 120, "…"],
        bool: [True, False],
        list: [[]],
    }.get(type(value))
    if same and rng.random() < 0.85:
        return rng.choice(same)
    return rng.choice([None, "", 0, True, []])


@pytest.mark.parametrize("name", sorted(SETS))
def test_a_mutated_submission_or_key_always_gets_a_verdict(name: str) -> None:
    rng = random.Random(name)
    checked = 0
    for _ in range(300):
        submitted, key = answer(name), key_json(name)
        for _ in range(rng.randint(1, 3)):
            if rng.random() < 0.6:
                submitted = mutate(submitted, rng)
            else:
                key = mutate(key, rng)
        try:
            built_output, built_key = build_output(submitted, IndexOutput), build_output(key, KeyOutput)
        except (TypeError, ValueError, KeyError):
            continue  # the sandbox refuses it before the verifier sees it
        given = build_output({"set": name}, SetInput)
        verdict = verifier.verify_task("build-index", given, built_output, built_key, ".")
        assert set(verdict) == {"valid", "score", "message", "details"}
        assert 0.0 <= verdict["score"] <= 1.0 and verdict["message"]
        json.dumps(verdict)
        checked += 1
    assert checked > 150
