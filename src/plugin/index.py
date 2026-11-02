"""The tools. Every one reads only the bundled data in data/ and writes nothing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from contract import KeyOutput, LengthsOutput, SetInput, TextsInput, TextsOutput, ToolSchema, ToolsOutput
from plugin.rules import LONGEST, collapse, index

DATA = Path(__file__).parent / "data"
SET_NAME = re.compile(r"[a-z0-9-]+\.json")
TOOL_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def load(name: str) -> ToolsOutput:
    """The set file ``name``, checked: tool names, string descriptions, parameters that are JSON objects."""
    if not SET_NAME.fullmatch(name):
        raise ValueError(f"{name!r} is not a set file name (lowercase letters, digits and '-', then .json)")
    path = DATA / "sets" / name
    if not path.is_file():
        sets = sorted(file.name for file in (DATA / "sets").glob("*.json"))
        raise FileNotFoundError(f"no set {name!r}: the sets are {', '.join(sets)}")
    tools = []
    for entry in json.loads(path.read_text(encoding="utf-8")):
        if not (isinstance(entry.get("name"), str) and TOOL_NAME.fullmatch(entry["name"])):
            raise ValueError(f"{name} has the tool name {entry.get('name')!r}: letters, digits and '_', first a letter")
        description = entry.get("description")
        if description is not None and not isinstance(description, str):
            raise TypeError(f"{name}'s {entry['name']} has a description that is not a string")
        if not isinstance(entry.get("parameters"), dict):
            raise TypeError(f"{name}'s {entry['name']} has parameters that are not a JSON object")
        tools.append(ToolSchema(name=entry["name"], description=description, parameters=json.dumps(entry["parameters"])))
    return ToolsOutput(set=name, tools=tools)


def load_index(given: SetInput) -> KeyOutput:
    tools = load(given.set).tools
    valid, duplicates, entries = index([(tool.name, tool.description) for tool in tools])
    return KeyOutput(set=given.set, tools=tools, valid=valid, duplicates=duplicates, entries=entries)


def read_tools(given: SetInput) -> ToolsOutput:
    return load(given.set)


def measure(given: TextsInput) -> LengthsOutput:
    return LengthsOutput(lengths=[len(text) for text in given.texts])


def first_sentence(given: TextsInput) -> TextsOutput:
    """A distractor: cuts after the first period followed by a space, so "e.g. weekends" ends a sentence."""
    texts = []
    for text in map(collapse, given.texts):
        found = text.find(". ")
        texts.append(text if found < 0 else text[: found + 1])
    return TextsOutput(texts=texts)


def shorten(given: TextsInput) -> TextsOutput:
    """A distractor: a text over 100 characters becomes its first 99 and "…", even mid-word."""
    return TextsOutput(texts=[text if len(text) <= LONGEST else text[: LONGEST - 1] + "…" for text in given.texts])
