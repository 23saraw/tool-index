"""read_tools: the set's tool schemas, as written."""

from .checks import result, set_input, tools_problem

verify_input = set_input


def verify_output(input_value, output_value, workspace):
    if output_value.set != input_value.set:
        return result(False, f"read_tools gave {output_value.set!r}, not {input_value.set!r}")
    problem = tools_problem(output_value.tools)
    if problem:
        return result(False, problem)
    return result(True, "the tools are read", tools=len(output_value.tools))
