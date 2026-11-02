"""measure: each text's length in characters."""

from .checks import result, texts_input

verify_input = texts_input


def verify_output(input_value, output_value, workspace):
    if output_value.lengths != [len(text) for text in input_value.texts]:
        return result(False, "measure gives each text's length in characters, in order, and this is not that")
    return result(True, "the texts are measured", texts=len(output_value.lengths))
