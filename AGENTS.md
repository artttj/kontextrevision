# AGENTS.md

## Tools and commands

Run tests with `python3 -m pytest tests/ -q` from the repo root.

Target Python 3.9. No `match` statements, no `X | Y` union syntax, no `tomllib`.
Use `typing.List`, `typing.Dict`, `typing.Optional`.

`scan.py` and `apply.py` use the standard library only. Never add a dependency to
either. pytest is a dev dependency for tests, not a runtime one.

## Workflow requirements

`scan.py` never writes. `apply.py` is the only module permitted to touch disk.
Keep them free of shared imports so the writer stays small enough to audit alone.

Never bypass `apply.py` when changing an instruction file, including this one.
The guards live there.

Every guard needs a test on both sides of its boundary, one that refuses and one
that permits. A guard with only a happy-path test survives any regression that
disables it.

No comments in code. Docstrings explain what a function is for; if the reasoning
behind a constant is not obvious, put it in the docstring.

Commit messages: `type: summary under 72 chars`. No `Co-Authored-By` lines.
Stage files by name, never `git add .`.

## Project-specific context

Statistics in `README.md` and `docs/proof/` come from a 250-file corpus scanned
with `scan.py`. Any change to `parse_sections`, `extract_commands`, or
`extract_paths` invalidates them. Re-measure before shipping, because published
numbers about other people's repositories have to be right.

Never claim a referenced command is missing without fully resolving the manifest
first. Makefile `include` directives nest, and included paths can live inside git
submodules that are invisible over raw HTTP. Naive checking produced false
accusations against Google, OpenShift, and Exoscale during this project's own
research. Refuse to judge rather than guess.
