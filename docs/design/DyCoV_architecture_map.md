# DyCoV architecture map

Concise pointer map of the Dynawo simulation subsystem — file paths + one line per component.
Kept dense-but-short so it can be `@`-imported from `CLAUDE.md` without bloating context.

## CLI execution flow (current, authoritative backend)

```
DynawoCurves.obtain_simulated_curve()          orchestrator/curves.py
  └─ ModelSetup.complete_model()               orchestrator/model_setup.py:545   (writes .jobs/.par/.dyd/.crv/solvers.par)
  └─ [bisection, optional]                      orchestrator/bisection.py         (HIZ / bolted / CCT)
  └─ DynawoCurves.__execute_simulation()        orchestrator/curves.py
       └─ SolverRetryStrategy.run()             runtime/retry_strategy.py         (backend-agnostic; up to 4 retries)
            └─ DynawoSimulator.run_base()       runtime/dynawo_simulator.py       ← THE backend seam
                 └─ run_dynawo_process()        runtime/_process.py:67           subprocess: [launcher, "jobs", "TSOModel.jobs"]
                 └─ create_curves()             runtime/_curves.py:515            post-process outputs/curves/curves.csv
```

`DynawoResult(succeeded, log, timeline_error, curves, sim_time)` is the namedtuple returned by the seam
(defined in `runtime/dynawo_simulator.py`). `run_simple()` is the retry-less variant used by CCT bisection.
`timeline_error` carries the first error Dynawo logged, stripped of its timestamp and level
(`find_timeline_error`, `runtime/_process.py`), so the retry message and the failure warning quote what
Dynawo said instead of the fact that it said something; a run that reports nothing leaves no log file,
which is the ordinary case and not worth a warning.

## Input file generation (io/)

All extend `FileVariables` (`io/file_variables.py`); fill template placeholders then dump to disk:
- `JobsFile` (`io/jobs.py`) — solver_lib/solver_id/producer_dyd/dynawo_log_level → `TSOModel.jobs`;
  the log level is `[Dynawo] log_level` (default `WARN`), raised to `DEBUG` when DyCoV runs in debug
- `ParFile` (`io/par.py`) — line/gen init + event params → `TSOModel.par`
- `DydFile` (`io/dyd.py`) — dynamic model → `TSOModel.dyd`
- `SolversFile` (`io/solvers.py`) — solver tuning → `solvers.par`
- `TableFile` (`io/table.py`)
- `crv.create_curves_file()` (`io/crv.py`) — builds `TSOModel.crv` + returns `curves_dict` (tool var ↔ Dynawo curve id)

Templates live in `src/dycov/model_lib/`; DyCoV **copies templates and fills placeholders** — it does NOT
build network structure dynamically.

**Config value definitions** (any multiplier-based `PCSDescription.ini` value): resolved data-driven,
not per-key. `value_registry.unit_characteristics(producer, u_dim)` is the single registry of base
magnitudes (`Pmax`/`Snom`/`Qmax`/`Qmin`/`Udim`/`Unom=1.0`, powers in s_nref pu, voltage in Unom pu);
`resolve_value_definition(defn, chars, sign, origin)` evaluates `[±mult*]Name`|numeric against it;
`origin=(section, key)` makes a rejected definition name its config file+line
(`config.describe_option`). Every
non-GFM value read pulls from that one registry: `_get_pdr` + `_complete_loads` (`model_setup.py`; loads
resolve voltage against a kV variant then ÷u_nom), `ProducerCurves.get_unit_characteristics`/`obtain_value`
(`curves.py`, backing `setpoint_step_value` and the `{{step_event_*}}` TSO placeholders), and the report
`reference_step_size` scaling (`figure.py`; `report.py` overrides `Unom`→kV). Adding a base = adding a
registry entry. `obtain_value` only resolves definitions that reference a magnitude (a `*`, or a
possibly signed registry name); anything else is a Dynawo parameter value passed through verbatim.
A rejected definition aborts the run — `obtain_simulated_curve` turns only `SimulationOutcomeError`
(the bisection outcomes, `model/parameters.py`) into a failed `SimulationResult`.
Out of scope: GFM (own grammar `mult*(Xeff+Xgrid)`, `extract_defined_value` for p0/q0)
and `line_XPu` (DTR reactance-table base `a`/`b`).

## Numerical layer (mutated many times, persisted to disk)

- **Retry** (`runtime/retry_strategy.py`): `run()` walks the remedies `_remedies()` yields —
  `_reduce_min_step` → `_increase_accuracy` → `_add_parameters_small_networks` → `_flip_solver`
  (SIM↔IDA) — and each one applies its change **and returns what it changed**, which `run()` quotes in
  the retry warning along with the attempt number and why the previous attempt failed. Persists via
  `replace_placeholders.modify_par_file` / `add_parameters` (`solvers.par`) and `modify_jobs_file` (`TSOModel.jobs`).
  The `SolverParams` dataclass (`runtime/run_types.py`) is **the** solver state, not a copy of it:
  `__reset_solver` builds it per OC and `__execute_simulation` hands that same object to `run()`, so
  what the retries leave is what `get_solver()` reports. Its `added_parameters` holds what
  `_add_parameters_small_networks` wrote into the set of the solver in use, cleared on a flip because
  the job then reads the other set.
- **Bisection** (`orchestrator/bisection.py`): `find_hiz_fault`, `find_bolted_fault`, `find_cct`.
  Per-iteration isolated working dir via `_isolated_copy` (temp dir). Mutates fault R/X/duration in
  `TSOModel.par` via `replace_placeholders.fault_par_file` / `fault_time`. CCT reads `curves/curves.csv` directly.
  Bolted: searches by bisection for a "sufficient" fault impedance X — one that both converges and
  leaves the residual PDR voltage under an SNom-interpolated threshold (`bolted_fault_*` config keys).
  Starts at `bolted_fault_min_impedance`, resolving the common case in one simulation, and raises X only
  when the simulation fails to converge.

`replace_placeholders.*` (XML/placeholder writers): `src/dycov/files/replace_placeholders.py`.

## Curve post-processing (`runtime/_curves.py`)

`create_curves(variable_translations, input_file, generators, s_nom, s_nref, f_nom)`: reads `;`-separated
`curves.csv` (`time` first col), combines complex `_re`/`_im` pairs, applies sign conventions + unit scaling.
Core PCC signals come from the `Measurements` pseudo-model columns (`Measurements_BUS_*`).
Dynawo drops a request for a variable its model does not have without failing, so
`report_unserved_requests` warns for every `.crv` request absent from `curves.csv`, naming the tool
curves that request feeds.

## Working directory layout

Inputs sit **flat** in the working dir (base-case + producer files are copied in). Dynawo
writes results under the subdir named by `<outputs directory>` in `TSOModel.jobs` (`outputs`),
resolved by `find_output_dir` (`files/simulation_files.py`).

```
working_oc_dir/          TSOModel.{jobs,par,dyd,crv}, solvers.par, Producer.*, Omega.*, CurvesFiles.ini
working_oc_dir/outputs/  logs/ (dynawo.log)  curves/ (curves.csv)  timeLine/  compilation/  finalState/
```

`simulation_inputs.ini` (`files/simulation_files.SIMULATION_INPUTS_FILE`) is written next to the curves
of each test after it runs, by `DynawoCurves.__record_simulation_inputs`: a `[Simulation]` section with the
event, the initial operating point and the solver the run ended with. `dycov anonymize` rebuilds the
`[Curves-Metadata]` of the dictionaries it generates from it (`curves/anonymizer/sources.py`, which also
accepts the `dycov.log` older results carry); without it every generated curve set declares its event at
t = 0.

The Results tree (`-o` output dir: `<Results>/…/Producer/<PCS>/<benchmark>/<oc>/`) **is** the working dir:
`validation.py` moves it there whole at the end, so nothing is selected or copied. Alongside the inputs
it holds the post-processed `curves_calculated.csv`, `curves_reference.csv` and `results.json`, and at its
root the `dycov_run.log` of the execution.

Output naming (`curves/naming.py`): internals use `BusPDR_BUS_*` everywhere, but Zone 1
outputs (saved CSVs, report/figure labels) rename the bus to `InternalNode1` — PDR is
reserved for the real connection point (issue #275). The importer accepts both namings
in Zone 1 reference-curve dictionaries.

## Logging (`logging/`)

`dycov_logging` is one process-wide `DycovLogger`. `init_handlers` (from `core/initialization.py`) keeps
the arguments it was called with, so a pool worker that did not inherit the handlers rebuilds the same
ones through `worker_initializer` — which is what happens from Python 3.14, where `forkserver` is the
default start method on Linux. Its handlers: the console; the shared, rotating
`~/.config/dycov/log/dycov.log`, which accumulates every run of the user; and the execution log,
`dycov_run.log`, added by `add_run_handler` once the working dir exists and closed by
`close_run_handler` right before that dir is moved to the `-o`. The execution log is a plain
`FileHandler` on purpose: several processes append to it, and a rotation they could interleave would
corrupt it.

Every record names the test it belongs to — `set_test_context(pcs, benchmark, oc, producer)`
(`logging/test_context.py`, thread-local) and the `_ContextAdapter` that prefixes it.
`warn_once(logger, message)` reports something that holds for the whole test however many times the
check that spots it runs, forgetting it when the context changes. `Benchmark.validate` opens each
operating condition with `Start (n/N)` and closes it with `Done in Xs -> <compliance>`.

## Shell completion (CLI)

`cli/cli_parsers.py` is the single source: `shtab.add_argument_to()` adds `--print-completion
<shell>`, and every path argument declares `completion=shtab.FILE|DIRECTORY` through `_add_argument`,
so a new command or option is completed without writing any completion code.
`installers/install_bash_completion.sh` generates the bash script into
`<venv>/share/bash-completion/completions/dycov` and sources it from the venv's `activate`; it is
called by `build_and_install.sh` and `installers/linux_install.sh`. The distribution image generates
it in its `Dockerfile` and loads it from `/etc/profile.d/dycov.sh`.
