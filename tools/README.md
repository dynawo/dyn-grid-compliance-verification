# Developer Tools

This directory contains **developer-oriented tooling** for the `dycov` project.
The tools here are **not part of the runtime package** and are intended for
development, analysis, auditing, and post-processing tasks.

They are typically run manually by developers or from CI pipelines.

---

## Directory overview

```

tools/
├── analysis/
│   ├── analyze_complexity.py
│   ├── compare_PDR.py
│   └── code_quality/
│       ├── audit_public_api.py
│       ├── ast_inventory.py
│       ├── run_mypy.py
│       ├── run_pydocstyle.py
│       ├── cross_check.py
│       └── README.md
│
├── dynawo_par/
│   ├── generate_par.py
│   ├── README.md
│   └── examples/
│       ├── WECCSample.xlsx
│       └── fill_wecc_example.py
│       (tests live in tests/tools/test_dynawo_par.py)
│
├── pypowsybl-vs-native/
│   ├── list_supported_models.py
│   ├── run_native_vs_pypowsybl.py
│   ├── additional_models.json
│   ├── probe_iec_under_wecc.json
│   ├── inputs/
│   ├── e2e/
│   └── README.md
│
├── olf_init_check/
│   ├── compare_init.py
│   ├── network_builder.py
│   ├── test_network_builder.py
│   ├── cases/
│   └── README.md
│
├── profiling/
│   ├── *.png
│   └── README.md
│
├── scripts/
│   ├── extract_curves.sh
│   └── run_complexity_analysis.sh
│
└── README.md

```

---

## analysis/

Python-based analysis and audit tooling.

### `analyze_complexity.py`
Audits cyclomatic complexity in the `src/` tree using **Radon**.
It produces:
- a CSV report
- visualizations (PNG or HTML)

This script is typically executed via the wrapper in
`tools/scripts/run_complexity_analysis.sh`.

---

### `compare_PDR.py`
Runs DyCoV simulations twice (with and without the `PPCLocal` flag) and compares
their outputs:
- computes RMSE / MAE / maximum absolute error per signal
- generates interactive Plotly HTML reports
- produces a global CSV summary

This tool is intended for **diagnostic and result-comparison analysis**.

---

### analysis/code_quality/

Tooling to audit the **public Python API** of the project.

It detects:
- public functions and methods missing type hints (`mypy`)
- public functions and methods missing docstrings (`pydocstyle`)

The main entry point is:

```bash
uv run python tools/analysis/code_quality/audit_public_api.py
```

This generates a single actionable report listing what needs to be fixed.
See `tools/analysis/code_quality/README.md` for details.

---

## dynawo_par/

Standalone preprocessing utility that reads an Excel model specification and
generates two Dynawo PAR fragments (`zone1.par` and `zone3.par`) ready to paste
into Dynawo models.

```bash
python tools/dynawo_par/generate_par.py --excel input.xlsx [--outdir DIR]
```

It only extracts and formats parameters — no validation or model
interpretation. Uses the standard library only (no third-party dependency).
See `tools/dynawo_par/README.md` and
`docs/design/Dynawo_par_generation_from_excel_design.md` for details.

---

## PyPowsybl integration study

The next two tools were **not** created as general-purpose utilities: they are the
working instruments of a specific investigation into whether DyCoV should adopt
[PyPowsybl](https://pypowsybl.readthedocs.io). Adopting it was attractive for three
reasons — accepting arbitrary input topologies (instead of DyCoV's fixed catalogue),
executing Dynawo through PyPowsybl as an alternative backend to the CLI subprocess,
and generating each test's network programmatically. The study split into two
questions, one per tool, and both are documented in the developer manual
(`docs/manual_dev/`, chapters *Running Dynawo through PyPowsybl* and *Using
OpenLoadFlow to initialize the tests*) and in `docs/design/Dynawo_PyPowsybl_*.md`.

### pypowsybl-vs-native/

Answers the first question: **can DyCoV's Dynawo cases be executed through PyPowsybl,
so the CLI backend could be replaced?** PyPowsybl does not ingest DyCoV's native
DYD/PAR/JOBS/CRV files — `powsybl-dynawo` generates them from an IIDM network plus a
programmatic `ModelMapping`. These demos probe the model catalogue, its runtime
extensibility (`additionalModelsFile`), and a complete-run attempt.

Outcome: **not feasible today**, blocked by a Dynawo release-cycle mismatch —
`powsybl-dynawo` targets official Dynawo *releases* while DyCoV runs a Dynawo
development build, so the generated connections reference renamed variables and no
dynamic simulation completes. See `tools/pypowsybl-vs-native/README.md`.

### olf_init_check/

Because running Dynawo through PyPowsybl proved infeasible, the question narrowed to
whether PyPowsybl is worth adopting *just for initialization*: PyPowsybl also ships
**OpenLoadFlow (OLF)**, a static AC load flow that does not use Dynawo at all. This
tool gathers the evidence by comparing DyCoV's internal, closed-form initialization
(`src/dycov/electrical/initialization_calcs.py`) against OLF over the whole case
catalogue.

Outcome: the internal initialization already matches OLF to numerical precision
(389/389 comparable cases), so the dependency cannot be justified by accuracy alone —
only by robustness or generality. The comparison did, however, surface and fix three
real initialization bugs along the way. See `tools/olf_init_check/README.md`.

---

## profiling/

Static profiling artifacts (charts, images) generated by analysis tools.

This directory contains **outputs only**, not executable code, and is meant to be
inspected by developers.

---

## scripts/

Shell scripts used as **helpers and wrappers** around analysis tools.

### `extract_curves.sh`

Collects all `curves_calculated.csv` files under a DyCoV results directory and
copies them into a flat output directory, renaming files to preserve scenario
context.

---

### `run_complexity_analysis.sh`

Convenience wrapper to:

*   ensure a Python environment exists
*   install dependencies for complexity analysis
*   run `analyze_complexity.py`

This script is intentionally standalone and shell-based.

---

## Environment and execution model

Python-based tools are expected to be run using **uv**:

```bash
uv pip install -e .[dev]
uv run python <tool>
```

Each tool is designed to be:

*   deterministic
*   safe to run repeatedly
*   independent from the others

---

## Scope and non-goals

The `tools/` directory is intentionally **not**:

*   a reusable Python library
*   part of the DyCoV runtime API
*   automatically executed during normal program execution

Its sole purpose is to support **development, analysis, and auditing workflows**.
