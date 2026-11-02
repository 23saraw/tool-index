"""load_index: the build-index answer key."""

from .checks import result, set_input
from .rules import rebuilt
from .task import key_problem

verify_input = set_input


def verify_output(input_value, output_value, workspace):
    if output_value.set != input_value.set:
        return result(False, f"the answer key is for {output_value.set!r}, not {input_value.set!r}")
    problem = key_problem(output_value)
    if problem:
        return result(False, problem)
    valid, twice, lines = rebuilt(output_value.tools)
    if (output_value.valid, set(output_value.duplicates), output_value.entries) != (valid, twice, lines):
        return result(False, "the answer key's index differs from the rules' recomputation")
    return result(True, "the answer key follows the rules", tools=len(output_value.tools))
