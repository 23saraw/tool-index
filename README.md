# Tool Indexer

A `nanoagent.plugin/v0001` plugin. Its task, `build-index`, has an agent
build the compact tool index another agent would start with: given a bundled
set of full tool schemas (each with a name, a description and parameters), it
writes one line per tool, the tool's name and a one-line summary of its
description, under the fixed rules below. No network. The verifier rebuilds
the index in its own code and compares it exactly, line by line.

## Tools

| Tool | Does | Code |
|---|---|---|
| `load_index` | The answer key: the set, its tools, and its index under the rules. The agent never sees it | `src/plugin/index.py`, `src/plugin/rules.py` |
| `read_tools` | Every tool in a set: name, description (`null` when missing) and parameters as JSON text, in file order, exactly as written | `src/plugin/index.py` |
| `measure` | Each text's length in characters (`…` is one) | `src/plugin/index.py` |
| `first_sentence` | A distractor: collapses whitespace and cuts after the first period followed by a space. True about itself, but it splits "e.g. weekends", which rule 2 does not | `src/plugin/index.py` |
| `shorten` | A distractor: cuts a text over 100 characters to its first 99 and "…", even mid-word. True about itself, but rule 3 keeps only whole words | `src/plugin/index.py` |

No tool builds the index: the agent applies the rules itself. Its plan is
`read_tools`, then `measure` with the summaries it needs counted, then
`submit`: three or four tool calls.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `build-index` | Builds a bundled set's compact index, or reports the set invalid when two tools share a name | `agent`, with `read_tools`, `measure`, `first_sentence` and `shorten`; reference `load_index` |

## The rules

1. **Whitespace.** Collapse all runs of whitespace (including newlines) in
   the description to single spaces, then trim.
2. **First sentence.** The summary is the description's first sentence:
   everything up to and including the first period that is followed by a
   space and an uppercase letter, or the whole description if there is none.
   Only periods end sentences, not `?` or `!`. So "Adds days, e.g.
   weekends." stays whole, but "Uses e.g. The calendar." splits after
   "e.g.". An uppercase letter is `A` to `Z`; rule 1 applies first, so a
   period followed by a newline and a capital ends a sentence.
3. **Length.** A summary of 100 characters or fewer is kept as is. A longer
   one is cut to the most whole words that fit in 99 characters, followed by
   "…" (one character, so the total is at most 100). If the first word alone
   is longer than 99 characters, cut it at 99 and add "…". Words are the
   space-separated pieces after rule 1, and "…" follows the last kept word
   with no space. Characters are Unicode code points.
4. **No description.** A tool with an empty or missing description gets
   "(no description)". A description that is only whitespace is empty after
   rule 1, so it gets the same.
5. **Order.** Entries are sorted by lowercased name; names differing only in
   case are ordered by their exact name (`Export_notes` before
   `export_notes`). Two tools with exactly the same name make the schema set
   invalid: its submission has `valid: false`, each such name once in
   `duplicates`, and no entries. Names differing only in case are distinct.
6. **Format.** Each entry renders as "name: summary", one per line. The
   submission gives the lines as `entries`, in order; the rendered index is
   them joined by newlines.

## Sets

The bundled sets, in `src/plugin/data/sets/`, are invented. The expectations
were derived by hand (`tests/expected.py`) and both implementations are tested
against them.

**set-1** (valid, 14 tools):

| Tool | Trap | Summary |
|---|---|---|
| `merge_contacts` | first sentence of exactly 100 characters | kept as is |
| `find_slots` | first sentence of 101 characters | "…blocked focus…" (96): whole words, not "focus tim…" |
| `ping_service` | no period | the whole description |
| `add_days` | "e.g." followed by lowercase | "Adds days to a date, e.g. weekends." |
| `pick_source` | "e.g." followed by uppercase | "Uses e.g." |
| `ask_user` | `?` and `!` before the first sentence end | "Asks the user a question? Waits for the reply! Then returns it." |
| `export_notes` | "Markdown.\n\n  Each": newlines and double spaces | "Exports notes as Markdown." |
| `Export_notes` | tabs, newlines, leading and repeated spaces; differs from `export_notes` only in case | "Exports notes as plain text, one file per folder.", listed first |
| `log_event`, `clear_cache`, `noop` | empty, missing, whitespace-only description | "(no description)" |
| `hash_blob` | one word of 120 characters | its first 99, then "…" |
| `Zeta_sync`, `alpha_sync` | uppercase sorts first unless lowercased | `alpha_sync` first, `Zeta_sync` last |

**set-2** (invalid): `send_note` twice, plus `Send_note` and `list_notes`.
The submission is `valid: false`, `duplicates: ["send_note"]`, `entries: []`.

## Constraints

`verifier/task.py` judges the submission against 8 constraints, in order.
Every entry of the verdict's `details.constraints` has the keys
`{id, constraint, ok, expected, actual, message}`; `ok` is `true`, `false`, or
`null` when a check it needs did not hold.

| # | id | What it checks | Example failure message |
|---|---|---|---|
| 1 | `answer-key` | The answer key is this set's and well formed: tool names, parameters that are JSON objects, an index shaped as in 4 | find_slots's parameters are not a JSON object |
| 2 | `answer-key-rules` | The key's validity, duplicates and entries equal the verifier's own recomputation | the answer key's index differs from the rules' recomputation at 'hash_blob: x' |
| 3 | `submitted-set` | The submission is for this set | the submission is for 'set-2.json', not 'set-1.json' |
| 4 | `entries-shaped` | Each entry is "name: summary", each name once; invalid exactly when duplicates are given, with no entries then | 'add_days - Adds days' is not an entry 'name: summary' |
| 5 | `validity-exact` | `valid` and `duplicates` are right | the duplicate names are ['Send_note', 'send_note'], but the rules give ['send_note'] |
| 6 | `entries-complete` | Every tool has an entry, and no entry names anything else | clear_cache has no entry: the rules give 'clear_cache: (no description)' |
| 7 | `summaries-exact` | Each summary is exactly the rules', with the rule a wrong one breaks | find_slots is summarised '…focus tim…', but the rules give '…focus…'; it is cut mid-word, but the rules keep only whole words (rule 3) |
| 8 | `order-exact` | The entries are in rule-5 order | export_notes is listed before Export_notes, but names that differ only in case go by their exact name |

How it is scored:

- **Valid** only when all 8 hold; the score is then 1.0.
- **Score 0** when any of 1 to 4 fails, or when the set's validity is wrong.
- **Otherwise** the score is the share of tools (expected or submitted) whose entry is exactly right and in place (in a longest run that keeps the rules' order), at most 0.99.
- **The message** names the first failing constraint, why, and how many more fail.

`verifier/rules.py` is a second implementation of the rules that shares no
code with `src/plugin/rules.py`: it walks each description one character at
a time and orders names by insertion, where the plugin uses `str.split`, a
regular expression and `sorted`. Constraint 2 checks that the answer key
agrees with it, so a wrong rule would have to be written the same wrong way
twice to pass. Every tool call is checked as well: `verify_input` refuses a
malformed set name and an empty or oversized text list, and `verify_output`
holds each tool's output to what it promises.

## Limitations

- **Only the bundled sets.** The task input names one of the sets in
  `src/plugin/data/sets/`; a person cannot bring schemas of their own.
- **No provenance gate.** The plugin writes no files, so the verifier cannot
  prove the agent called the tools. The answer depends on data only the tools
  give, so a correct answer without them would be a guess.
- **Parameters are carried, not used.** The index summarises descriptions
  only; the parameters are there because a real schema has them.
- **A plain sentence rule.** Rule 2 is deliberately simple: "Dr. Smith"
  ends a sentence after "Dr.", and a sentence ending in `?` or `!` runs on.

## Layout

```text
.
├── nanoagent.yaml   # manifest: id, runtime, permissions (none), tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable names this plugin needs (none)
├── src/plugin/      # the MCP server (__main__.py), the tools (index.py), the rules (rules.py)
│   └── data/sets/   # the bundled schema sets
├── tests/           # hand-derived answers (expected.py), both rule implementations, the tools, the verifier
├── ui/              # how the page draws outputs: drawn from the JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier: one module per tool, rules.py, and the task's 8 constraints in task.py
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv lock --check
```

With the `nanoagent` CLI installed in a separate environment:

```bash
nanoagent plugin inspect .                        # every plugin rule
nanoagent plugin agent config=run.yaml home=out   # the agent task; needs OPENROUTER_API_KEY
```

A `run.yaml` for one set (`args.json` holds the task input, e.g.
`{"set": "set-1.json"}`; give `plugin` and `arguments` as absolute paths).
The run folder gets `result.json`, `reference.json`, `messages.json` and
`verdict.json`, and the command exits 1 unless the verdict is valid:

```yaml
_ > nanoagent.cli.plugin.PluginOpenRouterAgentConfig:
plugin: /path/to/tool-index
task: build-index
arguments: /path/to/args.json
inputs: []
timeout: 60
llm > nanoagent.llm.openrouter.OpenRouterConfig:
  model: deepseek/deepseek-v4-flash-0731
  max_tokens: null
  temperature: null
  max_attempts: 3
  read_timeout: 180
  input_price: 0.0
  output_price: 0.0
harness > nanoagent.harness.nanoagent.NanoAgentConfig:
  max_steps: 8
  cost_limit: null
  token_limit: null
  context_window: null
  hooks: []
  skills: null
  context_files: []
  events: null
```
