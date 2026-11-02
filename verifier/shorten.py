"""shorten: a distractor; it cuts a text over 100 characters at 99 and adds "…", even mid-word."""

from .checks import result, texts_input
from .rules import ELLIPSIS, KEEP

verify_input = texts_input


def verify_output(input_value, output_value, workspace):
    if len(output_value.texts) != len(input_value.texts):
        return result(False, "shorten gives one text per text given, and this does not")
    for given, made in zip(input_value.texts, output_value.texts):
        if len(made) > KEEP or (made != given and not (made.endswith(ELLIPSIS) and given.startswith(made[:-1]))):
            return result(False, f"{made!r} is not {given[:20]!r}... kept or cut to at most {KEEP} characters")
    return result(True, "the texts are within 100 characters", texts=len(output_value.texts))
