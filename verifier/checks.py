"""Checks shared by the tool verifiers. Pure functions of their arguments."""

import json
import re

SET_NAME = re.compile(r"[a-z0-9-]+\.json")
TOOL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
MAX_TEXTS = 30  # texts one measure, first_sentence or shorten call may give
MAX_TEXT = 2_000  # characters one of those texts may have
MOST = 6  # list entries a constraint's expected or actual shows


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def constraint(identifier, text, ok, expected=None, actual=None, message=""):
    """One constraint's entry, always with the same keys: ok is True (holds), False (fails) or None (not
    checked: a check it needs did not hold); message says why it fails or was not checked, "" when it holds."""

    def cut(value):
        if isinstance(value, list) and len(value) > MOST:
            return value[:MOST] + [f"... {len(value) - MOST} more"]
        return value

    return {
        "id": identifier,
        "constraint": text,
        "ok": ok,
        "expected": cut(expected),
        "actual": cut(actual),
        "message": "" if ok is True else message or text,
    }


def summary(constraints):
    """A failed verdict's message: the first failing constraint, its id and why, then how many more fail."""
    failed = [entry for entry in constraints if entry["ok"] is False]
    more = f" (+{len(failed) - 1} more)" if len(failed) > 1 else ""
    return f"{failed[0]['id']}: {failed[0]['message']}{more}"


def set_input(value):
    if not SET_NAME.fullmatch(value.set):
        return result(False, f"{value.set!r} is not a set file name (lowercase letters, digits and '-', then .json)")
    return result(True, "input is valid")


def texts_input(value):
    if not 1 <= len(value.texts) <= MAX_TEXTS:
        return result(False, f"give 1 to {MAX_TEXTS} texts, not {len(value.texts)}")
    if any(len(text) > MAX_TEXT for text in value.texts):
        return result(False, f"each text has at most {MAX_TEXT} characters")
    return result(True, "input is valid")


def tools_problem(tools):
    """What is wrong with tool schemas as written, or None: names in the pattern, parameters JSON objects."""
    for tool in tools:
        if not TOOL_NAME.fullmatch(tool.name):
            return f"{tool.name!r} is not a tool name (letters, digits and '_', first a letter)"
        try:
            parameters = json.loads(tool.parameters)
        except ValueError:
            parameters = None
        if type(parameters) is not dict:
            return f"{tool.name}'s parameters are not a JSON object"
    return None


def split(entry):
    """(name, summary) of an entry 'name: summary', or None when it is not one."""
    name, colon, text = entry.partition(": ")
    return (name, text) if colon and TOOL_NAME.fullmatch(name) and text else None


def index_problem(valid, duplicates, entries):
    """What is wrong with an index as written, or None (not whether it is right): entries 'name: summary',
    each name once; duplicates each once; invalid exactly when duplicates are given, with no entries then."""
    for entry in entries:
        if split(entry) is None:
            return f"{entry!r} is not an entry 'name: summary'"
    names = [split(entry)[0] for entry in entries]
    twice = sorted({name for name in names if names.count(name) > 1})
    if twice:
        return f"{twice[0]} has more than one entry: give each tool one"
    if len(set(duplicates)) != len(duplicates):
        return "a duplicate name is given twice: give each once"
    if valid == bool(duplicates):
        state = "valid with duplicate names" if valid else "invalid with no duplicate names"
        return f"the set is reported {state}: a set is invalid exactly when two tools share a name"
    if not valid and entries:
        return "an invalid set has no index, and this gives entries"
    return None
