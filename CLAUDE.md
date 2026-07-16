# CLAUDE.md

Guidance for Claude Code when working in the DyCoV repository.

## Project

DyCoV validates dynamic grid-connection models by running Dynawo dynamic simulations and checking
their curves against compliance criteria. The simulation subsystem lives under
`src/dycov/curves/dynawo/`.

## Architecture map

The map below is imported so it loads automatically every session — prefer it over re-exploring the
codebase. Keep it dense but short; update it when the subsystem structure changes.

@docs/design/DyCoV_architecture_map.md

## Conventions

- Python package installed in editable mode. Tests under `tests/` mirror the `src/dycov/` layout;
  run with `pytest`.
- Prefer reusing existing utilities (e.g. `replace_placeholders.*`, `create_curves`) over introducing
  parallel implementations.
- Do not add comments that merely restate the code or narrate history (e.g. that a file was moved, or
  how a value is computed). A comment is warranted only to explain a functional *why* that cannot be
  deduced from the code — which should be rare, because a small, well-named method usually removes the
  need. Prefer extracting such a method over writing the comment. Functional directives that the code
  genuinely requires (`# type: ignore`, `# noqa`, etc.) are not comments in this sense and stay.
