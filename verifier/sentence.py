"""first_sentence: a distractor; it ends a sentence at any period followed by a space, so "e.g. weekends" splits."""

from .checks import result, texts_input
from .rules import squeezed

verify_input = texts_input


def verify_output(input_value, output_value, workspace):
    if len(output_value.texts) != len(input_value.texts):
        return result(False, "first_sentence gives one text per text given, and this does not")
    for given, made in zip(input_value.texts, output_value.texts):
        flat = squeezed(given)
        if not flat.startswith(made) or (made != flat and not made.endswith(".")):
            return result(False, f"{made!r} is not the start of {flat!r} up to a period")
    return result(True, "the texts are cut at their first period", texts=len(output_value.texts))
