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

**Dynawo version coupling** (DyCoV targets 2.0.0): DyCoV writes model names Dynawo owns in two
places — the dictionaries (`curves/dynawo/dictionary/*.ini`, every parameter and variable DyCoV
reads or writes; `tests/dycov/curves/dynawo/dictionary` checks that each names a variable or a
parameter that is not read-only, which Dynawo ignores in a PAR, in the model descriptors of the
installation `DYNAWOPATH` or the `dynawo.sh` on the PATH points to, and is skipped without one; a
tap changer's starting ratio is derived from its starting tap, as Dynawo does) and
`files/omega_file.py` (the `DYNModelOmegaRef` connectors, `omega_grp_<n>_` /
`omegaRef_grp_<n>_` / `running_grp_<n>_`: 2.0.0 drops the `_value` suffix and keeps the `_` that
marks the array index, as Dynawo's own examples spell them). The rest of the names are the
producer's, in its DYD and PAR, and a model written for an older Dynawo is migrated with the
scripts Dynawo ships (`sbin/updateXML`), which are also the authoritative list of what a build
changed. The WECC voltage ride-through protection is producer data like any other: Dynawo gives
its eight `lhvrt_*` parameters no default, so the unit's set declares them, from the
`Protection de tension` block of the workbook. Dynawo keeps that protection in a submodel of its
own, so its parameters take the `lhvrt_` prefix and not the model's — which is what
`[Block-Prefixes]` of `excel/dictionary/excel_names.ini` says and `excel/par/control.py` applies.
Its two capability curves are points of that same sheet: `excel/protection.py` writes them as the
table file `lhvrt_TablesFile` names, next to the PAR, and `manage_files._copy_producer_tables`
copies the producer's table files into the working directory with its DYD and PAR.

**Config value definitions** (any multiplier-based `PCSDescription.ini` value): resolved data-driven,
not per-key. `value_registry.unit_characteristics(producer, u_dim)` is the single registry of base
magnitudes (`Pmax`/`PmaxInjection`/`PmaxConsumption`/`Qmax`/`Qmin`/`Snom`/`Udim`/`Unom=1.0`/`line_XPu`,
powers in s_nref pu, voltage in Unom pu; plus `Xeff` (`[GFM Parameters]` of the producer) and
`Xgrid` (the `1/SCR` of the OC or its line's reactance), in the unit's Snom pu, only when known);
`resolve_value_definition(defn, chars, sign, origin)` evaluates `[±mult*]Name`|`[±mult*](Name+Name)`
|numeric against it; `origin=(section, key)` makes a rejected definition name its config file+line
(`config.describe_option`). Every
non-GFM value read pulls from that one registry: `_get_pdr` + `_complete_loads` (`model_setup.py`; loads
resolve voltage against a kV variant then ÷u_nom), `ProducerCurves.get_unit_characteristics`/`obtain_value`
(`curves.py`, backing `setpoint_step_value` and the `{{step_event_*}}` TSO placeholders), and the report
`reference_step_size` scaling (`figure.py`; `report.py` overrides `Unom`→kV). Adding a base = adding a
registry entry. `obtain_value` only resolves definitions that reference a magnitude (a `*`, or a
possibly signed registry name); anything else is a Dynawo parameter value passed through verbatim.
A definition rejected while a test is simulated ends that test as `Invalid test`, since
`obtain_simulated_curve` turns only `SimulationOutcomeError` (the bisection outcomes,
`model/parameters.py`) into a failed `SimulationResult` and the rest reaches `Benchmark.validate`.
Out of scope: GFM (own parsing of `mult*(Xeff+Xgrid)`, `extract_defined_value` for p0/q0)
and `line_XPu` (DTR reactance-table base `a`/`b`).

**Storage of types C and D (I16.2)**: the revision `20260723` splits the Fiche I16 of a storage
installation into I16.1 for type B, the base fiche with what its delta writes (in Zone 3 alone), and
I16.2 for types C and D, a version `Type<categories>.ini` in the directory of the delta of each PCS
(`revisions/20260723/PCS/model/BESS/PCS_RTE-I16z{1,3}/TypeCD.ini`, its templates in the mirrored
`reports/`); the base revision has none, I18 not existing. `Pcs` picks it by the category of the
installation (`ModelProducer.get_installation_category`: `get_generator_category` on the Zone 3 INI,
whatever zone runs; `_version_for_category`), and `load_pcs_config` reads it into the delta layer
after the delta, which it patches key by key. Zone 1 of TypeCD runs the setpoint steps on SCR 2 and
the tests of the Fiche I18 under their scenario names (`S_VolAngStep*`, `S_VolAmpStep*`,
`S_SCRup1/down1`, `S_Rocof*`, `S_Fault4-6`), whose shared settings are the `I18*` aliases of the
`config_aliases.ini` of the delta, and compares the curves of InternalNode1 alone, where the fiche
observes the results of I18 (`[GridCode] zone1_compared_at_node1`, which turns
`compared_curves.for_zone(1)` into V, P, Q, Ip and Iq of `BusPDR`). Their events: the default
`TableInfiniteBus.txt` of `GridVWDisturbance_1Line_InfBusFromTab` (`TableFile`: `grid_phase_jump`,
`grid_voltage_step`, `grid_frequency0`/`grid_rocof` on the `OmegaRefPu` of the bus, which the
`InfiniteBus` Omega model hands the units, after a pre-event ramp to the initial frequency), and
`SCRStepUp/Down_2Lines_InfBus`, a parallel line sized by `switched_SCR`
(`ModelSetup._get_switched_line`) that a `BooleanTable` (`TableSwitchedLine.txt`) holds open until
it closes (`line_SwitchOffSignal20 = true`, skipped by `get_line_values`) or an event opens. An OC
marked `only_with_reference` runs only when its reference curve is there (`Benchmark.__is_run`,
`manage_files.has_curves`): every I18 test but OC2/OC3. Criterion 5 tracks the `tracked_magnitude`
an OC names (`ModelValidator.__tracked_magnitude`, `compared_curves.setpoint_label` taking a label)
when its event steps no setpoint. Every page of the TypeCD Zone 1 report is the shared
`report.I16z1.TypeCD.Test.tex`, which prints the conditions of the test from its description
(`report/tables/conditions.py`). The Grid Forming converters of Dynawo the tool supports
(`GridFormingConverterDroopControl`, `GridFormingEpri`, family `GFM` in `Storage.ini`) state in the
dictionary flags no parameter holds (`ConverterLVControl = false`,
`SetpointsBehindTransformer = true` for the droop one, `translator.get_stated_flag`): the start
value of a stepped setpoint is then the one behind its transformer (`GenParams.reference_impedance`,
`ModelSetup._reference_operating_point`). The droop one keeps that transformer inside and gives the
power on its converter side in the base of the unit, so its Node2 curves are read at its terminal,
as those of the IEC plants of zone 3. The EPRI one has no `NetworkFrequencyReference`, which
`omega_file` then leaves unconnected: for a unit without it, `TableFile` turns the `TableUPhase` of
the infinite bus with the frequency of `TableOmegaRefPu` (the I16.2 RoCoF), while the Omega-model
events (Zone 3 frequency ramp, islanding) do not reach it. The I18 OCs are in pu of the unit's
`Snom`, the converter rating the Fiche I18 takes as base. The examples `BESS/GridFormingDroop` and
`BESS/GridFormingEpri` are type C installations: a Dynawo GFM converter in Zone 1 and a WECC plant
of 40 MW at 225 kV in Zone 3, because neither GFM model rides through every test of Zone 3 (the
droop one loses synchronism in the dips); `BESS/WECC`, of 15 MW, is a type B one.

**Declared tests (F16)**: the DTR Fiche F16 fixes no test and applies to Zone 3 only, so
`PCS_RTE-F16z3` ships with an empty `[PCS-Benchmarks]` and, next to it, the `F16Description.ini`
template of the declaration, which `core/initialization.py` copies under that same name into the
user's templates (`_copy_pcs_to_declare`, never over a copy already there); a PCS that declares no benchmark is skipped by `_validate_pcs`. The producer declares
the recorded tests in `<ReferenceCurves>/F16Description.ini`, which `Pcs` takes as the user PCS
description of the PCS the file names in its `[PCS-Benchmarks]` (`_description_declaring`, in place
of the one in the configuration directory), so `cfg.py` keeps its six layers. Every
declared test is rendered with the shared `report.F16z3.DeclaredTest.tex`: `_pcs_replace` writes
one `report.<pcs>.<bm>.<oc>.tex` per operating condition and hands the template its maps without the
`PCS…` suffix (`rm`, `thm`, `tem`…) plus `benchmark`/`operatingcondition`. The F16 error
thresholds are the `thr_FT_reftrack_*` family of `[GridCode]`: a PCS names the family it applies
with `setpoint_tracking_thresholds = FT` in its section, and `get_setpoint_tracking_threshold_values`
reads `thr_<family>_reftrack_*`, the I16 table when the PCS names none. The `is_field_measurements`
flag of the curves plays no part here: I16 keeps its single table whatever the reference is.
A PCS section may also declare `recorded_tests_only = true` (F16 does): `Benchmark` then keeps
only the operating conditions whose reference `.dict` exists under `<reference>/<producer>/`,
because the fiche fixes no test and a record is what makes one exist. The Zone 1 model is
what the PCS of zone 1 validate: `ValidationParameters` tells `ModelProducer` whether it is
required (`_requires_zone1`: any run not limited by `-p` to one zone-3 PCS), and
`check_validation_model` / `check_validation_curves` demand `Zone1/` only then, so a producer
in FON delivers `Zone3/` alone for F16. The declaration may be
of any Zone 3 kind of test; a dip or a swell needs the voltage table the simulation copies from
the shipped PCS directory (`curves_factory.py`), so `PCS_RTE-F16z3` ships the
`GridVoltageDip/` and `GridVoltageSwell/` tables of I16z3 and those two benchmarks keep their
names.

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
  Per-iteration isolated working dir via `_isolated_copy`: a subdirectory of the OC working dir, cloned
  without its curves like the CCT's (`manage_files.clone_as_subdirectory`), never the system temp dir.
  Mutates fault R/X/duration in `TSOModel.par` via `replace_placeholders.fault_par_file` / `fault_time`.
  CCT reads `curves/curves.csv` directly.
  Bolted: searches by bisection for a "sufficient" fault impedance X — one that both converges and
  leaves the residual PDR voltage under an SNom-interpolated threshold (`bolted_fault_*` config keys).
  Starts at `bolted_fault_min_impedance`, resolving the common case in one simulation, and raises X only
  when the simulation fails to converge.

`replace_placeholders.*` (XML/placeholder writers): `src/dycov/files/replace_placeholders.py`.

## Curve post-processing (`runtime/_curves.py`)

`create_curves(variable_translations, input_file, generators, s_nom, s_nref)`: reads `;`-separated
`curves.csv` (`time` first col), combines complex `_re`/`_im` pairs, applies sign conventions + unit scaling.
Frequencies stay in pu of `f_nom`, the unit producer curves arrive in and the checks (`freq_1`, the
I16 ramp) are written in; only a figure declared `in_hz` (`fig_W`, `fig_WRef`) draws them in Hz.
The network frequency is `NetworkFrequencyPu` on both sides: `create_curves` and `ImportedCurves`
copy the first `*_NetworkFrequencyPu` under that name unless the curves already carry it
(`naming.get_network_frequency_curve`), and `fig_WRef` reads that name and nothing else.
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
`validation.py` moves it there whole at the end, so nothing is selected or copied. It is created next to
the `-o` (`Parameters`: `<temporal_path>_<user>_*` in its parent, the current dir without one), so that
move is a rename within one filesystem. Alongside the inputs
it holds the post-processed `curves_calculated.csv`, `curves_reference.csv` and `results.json`, and at its
root the `dycov_run.log` of the execution. Between the validation of a test and its report, the
curves the report draws (the filtered ones, not those CSVs) wait in its `curves_set_aside.pkl`
(`manage_files.set_curves_aside`, called by `Benchmark.validate`, which also has the curves
manager let go of its last test), so a PCS holds the curves of no test in memory; the report takes
each back as it draws it (`take_curves_back`), and `_validate_pcs` discards the rest
(`discard_curves_set_aside`) before the tree moves to the `-o`.

`--curves-only` (`validate`, `performance`; `Parameters.is_curves_only`) stops each test once
`has_required_curves` has written its curves: `Benchmark` gives it the outcome of the simulation
(`Compliance.Simulated` or a failure) without running the checks, and `Validation` logs the summary
(`report.log_summary`) without the figures or the PDF. The tree is the same minus `results.json` and the
report, which is all the anonymizer needs; the curve regeneration of the examples runs this way.

Output naming (`curves/naming.py`): internals use `BusPDR_BUS_*` everywhere, but Zone 1
outputs (saved CSVs, report/figure labels) rename the bus to `InternalNode1` — PDR is
reserved for the real connection point (issue #275). The importer accepts both namings
in Zone 1 reference-curve dictionaries. The curves of a unit are named after the DTR nodes
(`*_GEN_VoltageNode2`, `*_GEN_ActiveCurrentNode2`, `*_GEN_ActivePowerControlledNode`…), and
`naming.from_legacy_name` lets the importer read, in any zone, the names they had before
(`InjTerminal`, `ControlledPu`).

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
operating condition with `Start (n/N)` and closes it with `Done in Xs -> <compliance>`; in between,
the simulation the curves come from logs `Dynawo ran in Xs`, Dynawo's own time, while every attempt
of the retry strategy, bisection runs included, logs its time at DEBUG.

## Shell completion (CLI)

`cli/cli_parsers.py` is the single source: `shtab.add_argument_to()` adds `--print-completion
<shell>`, and every path argument declares `completion=shtab.FILE|DIRECTORY` through `_add_argument`,
so a new command or option is completed without writing any completion code.
`installers/install_bash_completion.sh` generates the bash script into
`<venv>/share/bash-completion/completions/dycov` and sources it from the venv's `activate`; it is
called by `build_and_install.sh` and `installers/linux_install.sh`. The distribution image generates
it in its `Dockerfile` and loads it from `/etc/profile.d/dycov.sh`.
