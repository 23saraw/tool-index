"""The build-index task's verdict: 8 named constraints, in order. 1 to 4 guard the answer key and the
submission's integrity and score 0 when one fails; 5 to 8 judge the answer and score partially."""

from .checks import constraint, index_problem, result, split, summary, tools_problem
from .rules import KEEP, NO_DESCRIPTION, ROOM, rebuilt, steps

GATES = 4
TEXTS = [
    ("answer-key", "The answer key is this set's and well formed"),
    ("answer-key-rules", "The answer key's validity, duplicates and entries follow the rules, recomputed independently"),
    ("submitted-set", "The submission is for this set"),
    ("entries-shaped", "Each entry is 'name: summary' and each name once; invalid exactly when duplicates are given"),
    ("validity-exact", "The set is reported valid or invalid rightly, with the right duplicate names"),
    ("entries-complete", "Every tool has an entry, and no entry names anything else"),
    ("summaries-exact", "Each entry's summary is exactly the rules'"),
    ("order-exact", "The entries are in the rules' order"),
]


def key_problem(key):
    """What is wrong with the answer key's data, or None (not yet whether it follows the rules)."""
    return tools_problem(key.tools) or index_problem(key.valid, key.duplicates, key.entries)


def _first(problems):
    return problems[0] + (f" (and {len(problems) - 1} more)" if len(problems) > 1 else "") if problems else ""


def why_wrong(description, given):
    """Which rule a wrong summary ``given`` of ``description`` breaks, as a clause starting '; ', or ''."""
    flat, first, right = steps(description)
    if right == NO_DESCRIPTION:
        return "; an empty or missing description gives '(no description)' (rule 4)"
    if given == NO_DESCRIPTION:
        return "; the description is not empty"
    if given.endswith(".") and first.startswith(given) and len(given) < len(first):
        return "; it ends at a period not followed by a space and an uppercase letter, which ends no sentence (rule 2)"
    if len(first) > KEEP and given == first[:ROOM] + "…":
        return "; it is cut mid-word, but the rules keep only whole words (rule 3)"
    if len(first) > KEEP and given == first:
        return f"; the first sentence has {len(first)} characters, over {KEEP}, so it is cut (rule 3)"
    if len(first) <= KEEP and given.endswith("…"):
        return f"; the first sentence has {len(first)} characters, at most {KEEP}, so it is kept as is (rule 3)"
    if len(right) < len(flat) and right.endswith(".") and given.startswith(right):
        return "; the summary is only the first sentence, which ends at the first period followed by a space and an uppercase letter (rule 2)"
    if " ".join(given.split()) == right and given != right:
        return "; its whitespace is not collapsed to single spaces (rule 1)"
    return ""


def in_place(given, right):
    """The names of ``given`` in a longest run, not necessarily adjacent, that keeps the rules' order ``right``."""
    best = [[()] * (len(right) + 1) for _ in range(len(given) + 1)]
    for i, name in enumerate(given):
        for j, should in enumerate(right):
            best[i + 1][j + 1] = best[i][j] + (name,) if name == should else max(best[i][j + 1], best[i + 1][j], key=len)
    return set(best[-1][-1])


def _order_reason(earlier, later):
    if earlier.lower() == later.lower():
        return f"names that differ only in case go by their exact name, and {later!r} comes before {earlier!r}"
    return f"names go by their lowercased name, and {later.lower()!r} comes before {earlier.lower()!r}"


def verify_task(arguments, output, reference, workspace):
    entries = []

    def add(index, ok, expected=None, actual=None, message=""):
        entries.append(constraint(*TEXTS[index], ok, expected, actual, message))
        return ok

    # 1 to 4: the gates.
    key = reference
    if key is None:
        problem = "No answer key: load_index never ran for this task."
    elif key.set != arguments.set:
        problem = f"The answer key is for {key.set!r}, not {arguments.set!r}."
    else:
        problem = key_problem(key)
    blocker = None if add(0, problem is None, message=problem or "") else TEXTS[0][0]
    rebuilt_key = None

    def rules_problem():
        nonlocal rebuilt_key
        rebuilt_key = rebuilt(key.tools)
        valid, twice, lines = rebuilt_key
        if key.valid != valid or set(key.duplicates) != twice:
            return "the answer key's validity or duplicates differ from the rules' recomputation"
        if key.entries != lines:
            differ = next((line for line in key.entries if line not in lines), None) or "its order"
            return f"the answer key's index differs from the rules' recomputation at {differ!r}"
        return None

    gates = [
        rules_problem,
        lambda: None if output.set == arguments.set else f"the submission is for {output.set!r}, not {arguments.set!r}",
        lambda: index_problem(output.valid, output.duplicates, output.entries),
    ]
    for index, check in enumerate(gates, 1):
        if blocker:
            entries.append(constraint(*TEXTS[index], None, message=f"Not checked: {blocker} did not hold."))
            continue
        problem = check()
        if not add(index, problem is None, message=problem or ""):
            blocker = TEXTS[index][0]
    if blocker:
        for index in range(GATES, len(TEXTS)):
            entries.append(constraint(*TEXTS[index], None, message=f"Not checked: {blocker} did not hold."))
        return result(False, summary(entries), score=0.0, constraints=entries)

    # 5 to 8: the answer, against the verifier's own recomputation.
    valid, twice, lines = rebuilt_key
    descriptions = {tool.name: tool.description for tool in key.tools}
    want = dict(split(line) for line in lines)
    got = dict(split(line) for line in output.entries)

    if output.valid != valid:
        message = (
            "the set is reported invalid, but no two tools share a name (tools differing only in case are distinct)"
            if valid else f"the set is reported valid, but {', '.join(sorted(twice))} names more than one tool"
        )
    elif set(output.duplicates) != twice:
        message = f"the duplicate names are {sorted(output.duplicates)}, but the rules give {sorted(twice)}"
    else:
        message = ""
    add(4, not message, {"valid": valid, "duplicates": sorted(twice)},
        {"valid": output.valid, "duplicates": sorted(output.duplicates)}, message)

    missing = [name for name in want if name not in got]
    extra = [name for name in got if name not in want]
    problems = [f"{name} has no entry: the rules give {name + ': ' + want[name]!r}" for name in missing]
    problems += [
        f"{name} has an entry, but {arguments.set} has a duplicate name, so its index is empty" if not valid
        else f"{name} has an entry, but {arguments.set} has no tool {name!r}"
        + (" (names are case-sensitive)" if any(name.lower() == known.lower() for known in want) else "")
        for name in extra
    ]
    add(5, not problems, missing or None, extra or None, _first(problems))

    both = [name for name in want if name in got]
    wrong = [name for name in both if got[name] != want[name]]
    add(
        6, not wrong, [f"{name}: {want[name]}" for name in wrong], [f"{name}: {got[name]}" for name in wrong],
        _first([
            f"{name} is summarised {got[name]!r}, but the rules give {want[name]!r}{why_wrong(descriptions[name], got[name])}"
            for name in wrong
        ]),
    )

    given_order = [name for name in got if name in want]
    right_order = [name for name in want if name in got]
    placed = in_place(given_order, right_order)
    # At the first difference, the rules' name is listed later, so it comes before the one listed there.
    misplaced = [(name, should) for name, should in zip(given_order, right_order) if name != should]
    message = f"{misplaced[0][0]} is listed before {misplaced[0][1]}, but {_order_reason(*misplaced[0])}" if misplaced else ""
    add(7, not misplaced, right_order if misplaced else None, given_order if misplaced else None, message)

    if all(entry["ok"] for entry in entries):
        if not valid:
            message = f"All 8 checks hold: {arguments.set} is invalid: {', '.join(sorted(twice))} names more than one tool."
        else:
            cut = sum(1 for text in want.values() if text.endswith("…"))
            empty = sum(1 for text in want.values() if text == NO_DESCRIPTION)
            message = f"All 8 checks hold: {len(want)} tools indexed, {cut} summaries cut, {empty} without a description."
        return result(True, message, constraints=entries)
    if not valid or output.valid != valid:
        return result(False, summary(entries), score=0.0, constraints=entries)
    right = sum(1 for name in both if got[name] == want[name] and name in placed)
    score = min(right / len(set(want) | set(got)), 0.99) if want else 0.0
    return result(False, summary(entries), score=score, constraints=entries)
