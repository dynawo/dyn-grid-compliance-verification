# pypowsybl-vs-native

Small demos to answer: **can DyCoV's Dynawo cases be executed through PyPowsybl
(so the Dynawo CLI backend could be replaced)?**

## Why this exists

DyCoV drives Dynawo through its command-line interface, writing native input files
and launching `dynawo jobs` as a subprocess. Adopting PyPowsybl instead was
considered attractive for three reasons: it would let DyCoV accept **arbitrary input
topologies** (rather than its fixed catalogue), run Dynawo through a **Python-native
backend** in place of the CLI subprocess, and **generate each test's network
programmatically**. The last two only pay off if Dynawo can actually be executed
through PyPowsybl, so that had to be established first — which is exactly what these
demos test. (The initialization-only fallback, explored once this turned out
infeasible, lives in `../olf_init_check/`.)

PyPowsybl runs the *same Dynawo backend* underneath, but it does **not** ingest
native DYD/JOBS/CRV files. Those are generated programmatically by powsybl-dynawo
from an IIDM network + a `ModelMapping`. So a case can only be executed if every
one of its dynamic models exists in the **powsybl-dynawo catalog**.

## Findings (pypowsybl 1.15.0, Dynawo 1.8.0)

1. **The base catalog is a gate — but a runtime-extensible one.**
   `ModelMapping.add_*(model_name=…)` does not validate the name; powsybl-dynawo
   validates it when it **generates the DYD**. By default a non-catalog model is
   dropped (`Model WTG3WeccCurrentSource1 not found for WECC`). BUT the catalog can be
   extended at runtime with **`additionalModelsFile`** (a JSON registering libs within
   *existing* categories), passed as a provider parameter:
   `dyn.Parameters(provider_parameters={"additionalModelsFile": ".../additional_models.json"})`
   (config.yaml was **not** picked up for this key). With it, `WTG3WeccCurrentSource1`
   → **`instantiation OK`**. Constraint: cannot overload existing models nor use a
   **non-existent category** — and there is **no `IEC` category**.
2. **Coverage:** WECC-family models (WT4, WTG3, PV, BESS) map to the `WECC` category;
   the custom SM to `SynchronousGenerator`. IEC is uncertain (no category). The
   `Measurements` pseudo-model and Omega/SetPoint/Ramp helpers have no category.
3. **A run needs more than instantiation:**
   - WECC forbids default network models → *every* equipment must be mapped dynamically.
   - `create_empty` networks have an empty `sourceFormat`; Dynawo rejects the
     exported IIDM (workaround here: round-trip through XIIDM injecting a format).
   - The frequency reference (`omegaRefPu`) and PCC sensing must be wired the
     powsybl-dynawo way; DyCoV's explicit `Measurements` / `OmegaRef` wiring and the
     `USetPointStep` event (`Step → WTG3_URefPu`) have no direct equivalent. In these
     demos the run reaches instantiation but not a completed run (omegaRef not wired).

**Conclusion:** feasibility is **OPEN**, not blocked by catalog membership. The catalog
is runtime-extensible via `additionalModelsFile`; what remains is reproducing DyCoV's
explicit wiring (omegaRef/PCC/`Measurements`), the lack of an `IEC` category, and
unproven numerical parity. Full write-up:
[`docs/design/Dynawo_PyPowsybl_feasibility.md`](../../docs/design/Dynawo_PyPowsybl_feasibility.md).

## What a "category" is, and why WECC ≠ IEC

A category is **not** a device type — it is a **connection/wiring contract** (a
"builder") describing how a model plugs into the network and to helper models, plus its
role in frequency. `get_categories_information()` makes this explicit: `Wecc` = *"Grid
following WECC"*, `GridFormingConverter` = grid forming, `SynchronousGenerator` =
*"participating in network frequency"*, `SimplifiedGenerator` = *"not synchronized … fixed
frequency"*, etc. Each category has its own **builder** because each interface wires
differently (which terminals, whether it needs `omegaRefPu`, how it senses the PCC, …).

So WECC wind/PV/BESS all share the single `Wecc` (grid-following) builder — powsybl-dynawo
does *not* split them by device. IEC models are absent not because they are "different
devices" but because **no IEC builder/category has been implemented** (IEC 61400-27 models
expose a different interface, so they would need their own builder). It is coverage +
interface, not physics.

## Can a new *category* be added too?

No. `additionalModelsFile` only adds **models** to **existing** categories. Category
keys are a fixed set (`WECC`, `BASE_LINE`, `SYNCHRONOUS_GENERATOR`, …); a new key such
as `IEC` is rejected — `add_dynamic_model('IEC', ...)` → `No category named IEC`. New
categories require extending powsybl-dynawo via `ModelConfigLoader` services (a Java SPI,
i.e. an upstream/classpath change), which is not reachable from PyPowsybl at runtime.

## Probe: registering a model under a *chosen* existing category

Since categories are wiring contracts, you can try to register a model under a category
that *seems* to match. `probe_iec_under_wecc.json` puts an IEC model under `WECC`:

```bash
python run_native_vs_pypowsybl.py IECWT4BCurrentSource2020 probe_iec_under_wecc.json
```

Result: it reaches **`instantiation OK`** (model registration is just a name + prefix
lookup — it does not check the interface). The mismatch only bites **later**, at the
connection-generation / Dynawo model-build stage, where the `WECC` builder wires the
grid-following interface (`<prefix>_terminal`, `_omegaRefPu`, `_PPccPu`, `_uPccPu`, …)
against a model that may not expose those exact variables. In this minimal setup that
stage fails with a `NullPointerException` (also reached — but not passed — by legitimate
WECC-family additions such as WTG3, partly because the `SYNCHRONIZED` template needs an
`omegaRef`/frequency model this demo does not set up). **Takeaway:** instantiation is not
proof of compatibility; the category's *wiring* is the real contract, and confirming an
IEC-under-WECC fit requires completing the wiring and comparing curves.

## Scripts

### `list_supported_models.py`
Shows the **base** catalog, then the **additions** declared in `additional_models.json`,
then the **effective** WECC family (base + added). Also reports that `IEC` is not a
category. Only needs `pypowsybl` (no Dynawo / itools config).

```bash
python list_supported_models.py
```
Note: `get_supported_models()` returns only the base catalog — additional models
register at *simulation* time (proven by the run below), not in that list.

### `run_native_vs_pypowsybl.py`
Rebuilds an equivalent of the WECC case in `inputs/` and runs it through PyPowsybl
against your local Dynawo **twice** — without and with `additionalModelsFile` — printing
the model-supplier lines so the effect is visible:

```
1) WITHOUT -> Model WTG3WeccCurrentSource1 not found for WECC
2) WITH    -> Model WTG3WeccCurrentSource1 Wind_Turbine instantiation OK
```

Auto-detects `/opt/Dynawo_v*/dynawo` (override with `DYNAWO_HOME`) and writes its own
config/`models.par` under `_run/`. The run then fails later on unconnected omegaRef/PCC
wiring — completing that is the next step; the demo only shows model *registration*.

```bash
python run_native_vs_pypowsybl.py                        # WTG3 (non-catalog, registered)
python run_native_vs_pypowsybl.py WT4BWeccCurrentSource  # a base-catalog model
```

Requires the optional extra: `uv pip install -e ".[dynawo-pypowsybl]"`.

## Configuring your Dynawo location

All scripts locate Dynawo automatically: they honor **`$DYNAWO_HOME`** (the directory that
contains `dynawo.sh`) and otherwise glob `/opt/Dynawo_v*/dynawo` and pick the newest. So on
another machine just run, e.g.:

```bash
DYNAWO_HOME=/path/to/your/dynawo  python e2e/run_pypowsybl.py
```

`e2e/config.yml` is **generated at runtime** from that path (and is git-ignored); a
documented template is in `e2e/config.yml.example`. `run_native_vs_pypowsybl.py` likewise
writes its config under `_run/`. Nothing machine-specific is committed. (`list_supported_models.py`
needs no Dynawo at all.)

## `e2e/` — attempt at a complete run + Dynawo-version-drift finding

`e2e/run_pypowsybl.py` runs pypowsybl's own canonical dynamic example (IEEE-14 +
synchronous generators, from `integration_tests/test_dynawo.py`, which upstream asserts
`SUCCESS`). Against the installed **Dynawo 1.8.0-master** it **fails** with connection
variable-name mismatches (`step_step_value`, `load_switchOffSignal1`, `omega_grp_0_value`
/ `generator_omegaPu`) — a systematic **interface drift** between powsybl-dynawo 1.15 and
this Dynawo build. So no dynamic simulation completes here, not even the official example.
Fundamental tension: DyCoV uses Dynawo *master* builds (for its custom Modelica), while
pypowsybl 1.15 targets a Dynawo *release* interface. See
[`docs/design/Dynawo_PyPowsybl_feasibility.md`](../../docs/design/Dynawo_PyPowsybl_feasibility.md).

## Files
- `additional_models.json` — legitimate WECC-family additions (WTG3, WeccWT3) (editable).
- `probe_iec_under_wecc.json` — the IEC-under-WECC probe (see section above).
- `e2e/` — complete-run attempt (IEEE-14) that surfaces the Dynawo version-drift blocker.
- `inputs/` — the DyCoV case files (DYD/PAR/CRV/solvers) this demo is built from.
- `_run/` — generated at runtime (config.yml, models.par, network.par, net.xiidm); disposable.

The full case (with reference/calculated curves and the DyCoV result) lives in
`WECC_Test/` at the repo root.
