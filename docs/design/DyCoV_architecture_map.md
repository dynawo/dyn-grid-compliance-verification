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

`DynawoResult(succeeded, log, has_timeline_error, curves, sim_time)` is the namedtuple returned by the seam
(defined in `runtime/dynawo_simulator.py`). `run_simple()` is the retry-less variant used by CCT bisection.

## Input file generation (io/)

All extend `FileVariables` (`io/file_variables.py`); fill template placeholders then dump to disk:
- `JobsFile` (`io/jobs.py`) — solver_lib/solver_id/producer_dyd → `TSOModel.jobs`
- `ParFile` (`io/par.py`) — line/gen init + event params → `TSOModel.par`
- `DydFile` (`io/dyd.py`) — dynamic model → `TSOModel.dyd`
- `SolversFile` (`io/solvers.py`) — solver tuning → `solvers.par`
- `TableFile` (`io/table.py`)
- `crv.create_curves_file()` (`io/crv.py`) — builds `TSOModel.crv` + returns `curves_dict` (tool var ↔ Dynawo curve id)

Templates live in `src/dycov/model_lib/`; DyCoV **copies templates and fills placeholders** — it does NOT
build network structure dynamically. Custom Modelica in `src/dycov/model_lib/modelica_models/`.

## Numerical layer (mutated many times, persisted to disk)

- **Retry** (`runtime/retry_strategy.py`): `_reduce_min_step` → `_increase_accuracy` →
  `_add_parameters_small_networks` → `_flip_solver` (SIM↔IDA). Persists via
  `replace_placeholders.modify_par_file` / `add_parameters` (`solvers.par`) and `modify_jobs_file` (`TSOModel.jobs`).
  In-memory state carried in the `SolverParams` dataclass (`runtime/run_types.py`).
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

## Working directory layout

Inputs sit **flat** in the working dir (base-case + producer files are copied in). Dynawo
writes results under the subdir named by `<outputs directory>` in `TSOModel.jobs` (`outputs`),
resolved by `find_output_dir` (`files/model_parameters.py`).

```
working_oc_dir/          TSOModel.{jobs,par,dyd,crv}, solvers.par, Producer.*, Omega.*, CurvesFiles.ini
working_oc_dir/outputs/  logs/ (dynawo.log)  curves/ (curves.csv)  timeLine/  compilation/  finalState/
```

The Results tree (`-o` output dir: `<Results>/…/Producer/<PCS>/<benchmark>/<oc>/`) mirrors
this layout — DyCoV copies selected files/dirs from the working dir into it, then adds its
post-processed `curves_calculated.csv`, `curves_reference.csv` and `results.json`.
