"""The index rules (the README's 1 to 6). The verifier writes them again apart from this."""

from __future__ import annotations

import re
from collections import Counter

LONGEST = 100  # characters a summary may have
CUT = 99  # characters a cut summary keeps before "…"
NONE = "(no description)"
SENTENCE_END = re.compile(r"\. [A-Z]")


def collapse(text: str) -> str:
    """Rule 1: every run of whitespace becomes one space, then the ends are trimmed."""
    return " ".join(text.split())


def first_sentence(text: str) -> str:
    """Rule 2: up to and including the first period followed by a space and an uppercase letter."""
    found = SENTENCE_END.search(text)
    return text[: found.start() + 1] if found else text


def shortened(text: str) -> str:
    """Rule 3: the most whole words that fit in 99 characters, then "…", when the text is over 100."""
    if len(text) <= LONGEST:
        return text
    words = text.split(" ")
    if len(words[0]) > CUT:
        return words[0][:CUT] + "…"
    kept = words[0]
    for word in words[1:]:
        if len(kept) + 1 + len(word) > CUT:
            break
        kept += " " + word
    return kept + "…"


def summary(description: str | None) -> str:
    """Rules 1 to 4: a description's one-line summary."""
    text = collapse(description or "")
    return shortened(first_sentence(text)) if text else NONE


def duplicates(names: list[str]) -> list[str]:
    """Rule 5: each name more than one tool has, once, in rule-5 order."""
    return sorted((name for name, count in Counter(names).items() if count > 1), key=lambda name: (name.lower(), name))


def index(tools: list[tuple[str, str | None]]) -> tuple[bool, list[str], list[str]]:
    """(valid, duplicates, entries) for ``tools``, (name, description) pairs: rules 5 and 6."""
    twice = duplicates([name for name, _ in tools])
    if twice:
        return False, twice, []
    ordered = sorted(tools, key=lambda tool: (tool[0].lower(), tool[0]))
    return True, [], [f"{name}: {summary(description)}" for name, description in ordered]
