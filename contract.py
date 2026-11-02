"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output

SET = "A bundled schema set file's name, such as 'set-1.json'"
ENTRIES = "The index: one 'name: summary' line per tool, in the rules' order; [] when the set is invalid"


class Tool(Enum):
    LOAD_INDEX = "load_index"
    READ_TOOLS = "read_tools"
    MEASURE = "measure"
    FIRST_SENTENCE = "first_sentence"
    SHORTEN = "shorten"


class Task(Enum):
    BUILD_INDEX = "build-index"


@dataclass
class SetInput(Output):
    set: Annotated[str, SET]


@dataclass
class ToolSchema(Output):
    name: Annotated[str, "The tool's name, exactly as written"]
    description: Annotated[str | None, "The tool's description, exactly as written; null when it has none"]
    parameters: Annotated[str, "The tool's parameter schema: a JSON object's text"]


@dataclass
class ToolsOutput(Output):
    set: Annotated[str, SET]
    tools: Annotated[list[ToolSchema], "Every tool schema in the set, in file order, as written"]


@dataclass
class TextsInput(Output):
    texts: Annotated[list[str], "The texts, exactly as they should be read"]


@dataclass
class LengthsOutput(Output):
    lengths: Annotated[list[int], "Each text's length in characters, in order ('…' is one character)"]


@dataclass
class TextsOutput(Output):
    texts: Annotated[list[str], "One text per text given, in order"]


@dataclass
class IndexOutput(Output):
    set: Annotated[str, SET]
    valid: Annotated[bool, "Whether no two tools have exactly the same name"]
    duplicates: Annotated[list[str], "Each name more than one tool has, once; [] when the set is valid"]
    entries: Annotated[list[str], ENTRIES]


@dataclass
class KeyOutput(Output):
    set: Annotated[str, SET]
    tools: Annotated[list[ToolSchema], "The set's tool schemas, as written"]
    valid: Annotated[bool, "Whether no two tools have exactly the same name"]
    duplicates: Annotated[list[str], "The expected duplicate names"]
    entries: Annotated[list[str], "The expected index"]


TOOLS = {
    Tool.LOAD_INDEX: (SetInput, KeyOutput),
    Tool.READ_TOOLS: (SetInput, ToolsOutput),
    Tool.MEASURE: (TextsInput, LengthsOutput),
    Tool.FIRST_SENTENCE: (TextsInput, TextsOutput),
    Tool.SHORTEN: (TextsInput, TextsOutput),
}
TASKS = {Task.BUILD_INDEX: (SetInput, IndexOutput)}
