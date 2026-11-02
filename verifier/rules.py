"""The index rules, written again apart from src/plugin/rules.py and sharing no code with it.

It walks each description one character at a time, keeps every step of a summary so a message can say which
rule a wrong one broke, and orders names by comparing them itself. A wrong rule would have to be written the
same wrong way twice for the key to pass."""

NO_DESCRIPTION = "(no description)"
KEEP = 100  # a summary this long or shorter is kept
ROOM = 99  # characters a cut summary keeps before the ellipsis
ELLIPSIS = "…"


def squeezed(text):
    """Rule 1, a character at a time: whitespace runs become one space, none at either end."""
    out, gap = [], False
    for char in text:
        if char.isspace():
            gap = bool(out)
        else:
            if gap:
                out.append(" ")
            out.append(char)
            gap = False
    return "".join(out)


def sentence_end(text):
    """Rule 2: the index just past the first sentence's period, or len(text) when only one sentence."""
    for at in range(len(text) - 2):
        if text[at] == "." and text[at + 1] == " " and "A" <= text[at + 2] <= "Z":
            return at + 1
    return len(text)


def fitted(text):
    """Rule 3: ``text`` within 100 characters, cut after the last whole word that fits in 99."""
    if len(text) <= KEEP:
        return text
    space = text.rfind(" ", 0, ROOM + 1)  # a space at index 99 still leaves 99 characters before it
    return (text[:space] if space > 0 else text[:ROOM]) + ELLIPSIS


def steps(description):
    """(collapsed, first sentence, summary) for a description, or (None, None, NO_DESCRIPTION) for none."""
    flat = squeezed(description) if description else ""
    if not flat:
        return None, None, NO_DESCRIPTION
    first = flat[: sentence_end(flat)]
    return flat, first, fitted(first)


def before(a, b):
    """Rule 5: whether name ``a`` comes before name ``b``."""
    low_a, low_b = a.lower(), b.lower()
    return low_a < low_b if low_a != low_b else a < b


def ordered(names):
    """``names`` in rule-5 order, by insertion."""
    out = []
    for name in names:
        at = len(out)
        while at > 0 and before(name, out[at - 1]):
            at -= 1
        out.insert(at, name)
    return out


def rebuilt(tools):
    """(valid, {duplicate names}, [entries]) for ``tools``, a list of ToolSchema: rules 4 to 6."""
    seen, twice = set(), set()
    for tool in tools:
        (twice if tool.name in seen else seen).add(tool.name)
    if twice:
        return False, twice, []
    by_name = {tool.name: tool.description for tool in tools}
    return True, set(), [f"{name}: {steps(by_name[name])[2]}" for name in ordered(list(by_name))]
