# DyCoV test suite conventions

Canonical style for every unit test in this repository. New tests must follow it; existing
tests are normalized to it whenever they are touched (coverage work, fixes, refactors).
Reference examples of the target style:

- `tests/dycov/electrical/test_initialization_calcs.py` — the regression tests
  (`test_initialize_topo_s_with_main_xfmr`, `test_initialize_topo_m_power_share`, the islanding
  pair): docstrings stating the topology and the issue they guard against, `_make_*` factories,
  intention comments on assert groups, explicit expected numeric values.
- `tests/dycov/curves/dynawo/orchestrator/test_model_setup.py` — file structure: module-level
  patch target constant, parametrizable `_make_*` factories, section banners.

## Layout

`tests/dycov/` mirrors the `src/dycov/` package layout one-to-one; tests for the standalone
utilities under `tools/` live in `tests/tools/`. Run everything with:

```bash
./dycov_venv/bin/pytest tests -q
./dycov_venv/bin/ruff check src/dycov tests
```

## File structure

1. Shebang + encoding + the standard project copyright header (`(c) <year> RTE / Developed by
   Grupo AIA` block). Tests under `tests/tools/` keep the header style of the tool they test.
2. A one-line module docstring stating what is under test.
3. All imports at module level — never import inside a test function or a helper. This includes
   `dycov` imports: if importing the module under test at collection time is a problem, that is
   a design smell to fix in the module, not in the test.
4. Shared helpers and dummies (module constants, `_make_*` factories, `Dummy*` classes,
   fixtures), defined once per file. If reused across files, move them to a `conftest.py`.
5. Test functions, optionally grouped under section banners of the form:

   ```python
   # ---------------------------------------------------------------------------
   # Section name
   # ---------------------------------------------------------------------------
   ```

## Test style

- **AAA with blank lines**: arrange, act and assert separated by a blank line. One behavior per
  test; split tests that verify unrelated things.
- **Every test asserts something.** A test that only checks "it does not raise" must at least
  assert on the returned value or the observable side effect.
- **Names** follow `test_<unit>_<scenario>` (e.g. `test_get_event_times_missing_values`,
  `test_apply_control_mode_without_parameters`). The name alone should say what failing means.
- **Readable asserts**: `math.isnan(x)`, `pytest.approx(...)` — never tricks like `x != x`.
  Avoid asserting on private attributes when a public accessor exists.
- **Numeric results** are compared against explicit expected values with `pytest.approx` or a
  documented tolerance helper (see `REL_ERR`/`ABS_ERR` in `test_initialization_calcs.py`) —
  never with type-only checks (`isinstance(x, complex)` proves nothing about the result).
- **Regression tests** carry a docstring naming the issue and the misbehavior they guard
  against, and group asserts with a short intention comment when the values alone don't tell
  the story.
- **No `print()` in tests**: the assert (and its message, if any) is the diagnostic. Tests are
  functions pytest collects — never a `test_*` wrapper that just calls private `_helpers` that
  do the real asserting.
- **No dead scaffolding**: only build the dummies/patches the exercised code path actually uses.

## Mocking policy

Pick the mechanism by need — do not mix them gratuitously within a file:

- **`monkeypatch` (default)** for replacing attributes, module globals, config values and
  environment. Prefer it together with plain `Dummy*` classes or factory helpers.
- **`unittest.mock` (`Mock`, `patch`)** only when the test needs to *spy on calls*
  (`assert_called*`, `side_effect` sequencing) or stub an external boundary
  (`subprocess.run`, `builtins.input`). Keep `patch` as a context manager, and place the
  assertions *after* the `with` block, not inside it.
- **Dummies**: hand-written `Dummy*` classes are the preferred stand-in for project objects
  (producers, validators, configs). Define them once at module level with constructor knobs
  (`DummyValidator(has_validations=False)`) instead of redefining near-copies per test.
- **Fixtures** (`@pytest.fixture`) for reusable arrange steps with teardown or captured state
  (e.g. a `debug_logs` fixture that patches the logger and returns the captured list —
  see `tests/dycov/configuration/test_dump.py`).

## Migration status

The canon was applied on 2026-07-22 to: `test_dump.py`, `test_manage_files.py`,
`test_omega_file.py`, `test_model_parameters.py`, `test_operating_condition.py`,
`test_dynawo_par.py`. The rest of the suite is normalized incrementally: whenever a test file
is touched, leave it fully conforming.
