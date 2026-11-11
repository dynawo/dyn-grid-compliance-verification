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

- Read the whole issue before starting: its description and every one of its comments.
- A pull request points to one issue and nothing else. The issue is where the work is explained, in
  general terms and without code detail, and anything that needs saying beyond what is already
  written there — a decision taken along the way, a finding, a constraint — goes as a comment on the
  issue, at that same level, not into the pull request.
- Keep the disk as clean as possible: delete every temporary working directory the work created
  once the development is finished — the run and comparison trees under the home directory or in
  `/tmp`, the `Results` trees produced to try something out, and any copy of the repository made to
  audit it. Reference material and the repository itself stay.
- The curves of the examples — the `ReferenceCurves` and `ProducerCurves` directories — are not
  versioned: `tools/scripts/regenerate_curves.sh` regenerates them once per release, they ship as
  the `dycov_examples.zip` asset, and `tools/scripts/fetch_example_curves.sh` brings them to a
  checkout. A change to an example carries no curves and leaves nothing about them pending.
- The virtual environment of the project is `dycov_venv`, at the root of the repository, and it is
  the only one: it is the one `build_and_install.sh` and `installers/linux_install.sh` create, the
  one `.gitignore` knows, and the one that holds the development tools (`dycov_venv/bin/ruff`).
  Never work in a `.venv` — a bare `uv run` silently makes one, so call the environment explicitly
  (`dycov_venv/bin/python`, or source `dycov_venv/bin/activate`) and delete any `.venv` that turns up.
- Python package installed in editable mode. Tests under `tests/` mirror the `src/dycov/` layout;
  run with `pytest`.
- Prefer reusing existing utilities (e.g. `replace_placeholders.*`, `create_curves`) over introducing
  parallel implementations.
- Do not add comments that merely restate the code or narrate history (e.g. that a file was moved, or
  how a value is computed). A comment is warranted only to explain a functional *why* that cannot be
  deduced from the code — which should be rare, because a small, well-named method usually removes the
  need. Prefer extracting such a method over writing the comment. Functional directives that the code
  genuinely requires (`# type: ignore`, `# noqa`, etc.) are not comments in this sense and stay.

## Commits and branches

- **The user is the one who commits.** Claude never commits, never pushes and never opens a pull
  request or closes an issue; the work ends at an uncommitted working tree plus a summary of what
  changed and why. Not even a local commit "without pushing": that already takes the review decision
  away, and the message states an intent that is the user's to write. A phrase that could mean either
  *describe* or *execute* ("dame los commits", "los commits que harías") means describe — print the
  branch name, the file groupings and the messages as text, and stop.
- **No trailers, in the commit message or in the pull request description**: no `Co-authored-by`, no
  "Generated with" footer, no tool attribution of any kind. The history of this repository names the
  people who work on it.
- **One line per commit message, conventional style, no body** — `fix(parameter_checks): correct the
  trafo reactance check`. The detail lives in the diff, in the design document or in the issue.
- **A file's changes travel in a single commit**: the same file is not split across several commits
  of one branch.
- **Nothing reaches `master` outside the flow issue → branch → pull request**, not even a deletion
  that looks trivial. Branch from the *local* master, never from the remote one: `switch master`,
  `pull --ff-only origin master`, then `switch -c <branch>`. A branch started off `origin/master`
  keeps that upstream, and a plain push then lands straight on master with no review — it has
  happened twice. Verify with `git rev-parse --abbrev-ref <branch>@{upstream}`.
- The branch name is derived from the issue title, so keep out of that title whatever a shell or a
  branch name dislikes — parentheses, quotes, backticks, `$`, `&`, `;`, `#`, `*`, `?`, `:` — and
  write the identifier in prose instead.
- **One problem per pull request, one branch at a time**, and branches are never stacked on one
  another. If fixing A uncovers B, B is another issue, not another commit in A's branch.
- **The history only moves forward.** No rebase and no force-push over anything published; when a
  decision is reversed, a new commit applies the reversal and its message tells why.
- Git work happens in the everyday checkout, not in a linked worktree or in a copy beside it.
