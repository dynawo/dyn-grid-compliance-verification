# `test_tool.sh` — Integration Runner for **dycov**

This script orchestrates automated runs of **dycov** to **validate models**, **verify performance**, and **generate envelopes** across the project’s examples. It supports filtering by **IEC** and **WECC** families, controls input/output locations, and runs tasks **in parallel** to speed up execution. At the end of the run, it also **summarizes Overall Result counts** and produces CSV and optional charts.

> **Path:** `tests_integration/test_tool.sh`  
> **Phases:**
>
> *   **Validation** — `dycov validate` for Wind / Photovoltaics / BESS
> *   **Performance** — `dycov performance` for selected topologies and models
> *   **Envelope Generation** — `dycov generateEnvelopes` for GFM (Overdamped / Underdamped)

***

## 1) Prerequisites

*   **Dynawo** installed and accessible; pass the launcher with `-l` (default: `dynawo.sh`).
*   Examples tree (default: `./examples`).
*   Write permissions on the results directory (default: `../Results`).

> **Tip:**
>
> ```bash
> export DYNAWOPATH=/opt/dynawo/bin
> tests_integration/test_tool.sh --launcher "$DYNAWOPATH/dynawo.sh"
> ```

***

## 2) Quick Start

```bash
tests_integration/test_tool.sh
```

Running with **no options** will:

*   Include both **IEC** and **WECC** models (defaults).
*   Run **Validation + Performance + Envelope Generation** (all enabled by default).
*   Use `./examples` as input and `../Results` as output.
*   Write the run log to `../Results/test_tool.log`.
*   Execute each validation in **parallel** with up to **4 processes**.
*   Produce an **Overall Result summary** (CSV + optional PNG + HTML) at the end.

***

## 3) Command-Line Options

```text
-l, --launcher <path>   Dynawo launcher script (default: dynawo.sh)
-e, --examples <path>   Examples root path (default: ./examples)
-o, --output <path>     Output/results path (default: ../Results)
-r, --remove            Remove the output path if it exists (clean run)

--iec                   Include only IEC families (disables WECC)
--wecc                  Include only WECC families (disables IEC)

-v, --validate          Run only the Model Validation
-p, --performance       Run only the Electrical Performance Verification
-g, --generate          Run only the Envelope Generation (GFM)

-h, --help              Show help
```

### Defaults & interactions

*   Defaults: `iec_models=true`, `wecc_models=true`, `validate=true`, `performance=true`, `generate=true`.
*   `--iec` disables WECC; `--wecc` disables IEC.
*   Phase selectors are **exclusive**: choosing one sets the other two to `false`.
*   `--remove` cleans the output dir before the run.

***

## 4) What runs in each validation

### A) Validation — `dycov validate`

*   **IEC Wind**: `IECA2015`, `IECA2020`, `IECA2020WithProtections`, `IECB2015`, `IECB2020`, `IECB2020WithProtections`
*   **WECC Wind**: `WECCA`, `WECCB`, `WECC`
*   **WECC PV**: `WECCCurrentSource`, `WECCVoltageSource1`, `WECCVoltageSource2`
*   **WECC BESS**: `WECC`
*   Paths per model:
    *   Input: `${examples_path}/Model/<Family>/<Model>/Dynawo`
    *   References: `${examples_path}/Model/<Family>/<Model>/ReferenceCurves`
    *   Output: `${results_path}/Model/<Family>/<Model>`
*   Runs up to **4 validations in parallel**.

### B) Performance — `dycov performance`

*   **Topologies**: `Single`, `SingleAux`, `SingleAuxI`, `SingleI`
*   **Models**: always `GeneratorSynchronousFourWindingsTGov1SexsPss2a`; adds IEC and WECC models if enabled
*   Paths per (topology, model):
    *   Input: `${examples_path}/Performance/<Topology>/<Model>/Dynawo`
    *   Output: `${results_path}/Performance/<Topology>/<Model>`
*   Runs up to **4 jobs in parallel**.

### C) Envelope Generation — `dycov generateEnvelopes`

*   **GFM**: `GFM_Overdamped`, `GFM_Underdamped`, `GFM_Fusion`
*   Paths per model:
    *   Input: `${examples_path}/<Model>/Producer.ini`
    *   Output: `${results_path}/Envelopes/<Model>`
*   Runs up to **4 generators in parallel**.

***

## 5) Logging & Overall Result summary

*   Log file: `../Results/test_tool.log`
*   The script redirects stdout/stderr to the log but prints green INFO lines to the console.
*   **Overall Result summary**:
    *   Parses the log to count labels:  
        `Compliant`, `Non-compliant`, `Invalid test`, `Failed simulation`,  
        `Undefined validations`, `Test without curves`,  
        `Test without reference curves`, `Test without producer curves`,  
        `Fault simulation fails`, `Fault dip unachievable`, `Simulation time out`
    *   Outputs:
        *   **CSV**: `../Results/test_tool.log.overall_result_counts.csv`
        *   **PNG**: `../Results/overall_result_counts.png` (if Matplotlib available)
        *   **HTML**: `../Results/overall_result_counts.html` (if Plotly available)
    *   Prints totals and percentages to the log and announces file paths on the console.

***

## 6) Examples

```bash
# Full run (IEC + WECC; all validations; default paths)
tests_integration/test_tool.sh

# Clean run (remove previous results, then run everything)
tests_integration/test_tool.sh --remove

# Only Validation on IEC, custom launcher & output
tests_integration/test_tool.sh --iec --validate \
  --launcher /opt/dynawo/bin/dynawo.sh \
  --output ./Results_Validate_IEC

# Performance only on WECC
tests_integration/test_tool.sh --wecc --performance --output ./Results_Perf_WECC

# Envelope generation only (GFM)
tests_integration/test_tool.sh --generate

# Custom examples path
tests_integration/test_tool.sh --examples /home/marcos/project/examples
```

***

## 7) Troubleshooting & best practices

*   The script uses `set -o errexit -o pipefail`; any failure causes a non-zero exit. Check `../Results/test_tool.log`.
*   Provide a full path to `dynawo.sh` via `--launcher` if not on PATH.
*   Keep Validation and Performance runs separate for clean logs; use `--remove` for reproducibility and version outputs via `--output`.

***

## 8) Maintainers’ notes

*   Parallelism: commands are dispatched via `xargs -P 4 -I { } bash -c "{ }"`. Adjust `-P` for concurrency.
*   Function exports: `run_dycov_validate`, `run_dycov_performance`, `run_dycov_generate` are `export -f` so `xargs` can invoke them in subshells.
*   Timing: each sub-command prints elapsed seconds; the total time is reported at the end.

