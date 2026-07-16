# olf_init_check — is OpenLoadFlow worth it for initialization?

Evidence tool for a single decision: **should DyCoV add PyPowsybl / OpenLoadFlow (OLF)
as a dependency to initialize the equivalent network?** If DyCoV's own internal
(closed-form, ad-hoc) initialization is already as good as an independent AC load flow,
the dependency is not worth the maintenance cost.

## Why this exists

This tool is the narrowed remainder of a broader investigation. The original goal was to
run Dynawo *through* PyPowsybl as an alternative backend (see `../pypowsybl-vs-native/`),
which turned out to be infeasible against DyCoV's Dynawo build. That left one part of
PyPowsybl still potentially useful on its own: **OpenLoadFlow**, a static AC load flow
native to `powsybl-core` that does not involve Dynawo at all. So the question shrank from
"replace the whole backend" to "is PyPowsybl worth adopting *just* to initialize the
tests?" — and this tool collects the evidence to answer it. It reuses `network_builder.py`
(co-located here, moved out of the `dycov` package), which was originally written for the
backend attempt.

## What it does

For each bundled reference case, `compare_init.py`:

1. Reconstructs the **equivalent electrical network** from the *completed* per-test model
   that DyCoV wrote (`TSOModel.{dyd,par}`, `Producer*.{dyd,par}`, and `TableInfiniteBus.txt`
   for table grids) — building it in IIDM with `PypowsyblNetworkBuilder`.
2. Runs **OpenLoadFlow** (`pypowsybl.loadflow.run_ac`) with the grid source as the slack
   (held at DyCoV's grid voltage) and the generators modelled the way these plants behave:
   **PV regulating the PDR node remotely** (plant voltage control at the PCC) when a line
   separates the grid from the PDR — so OLF *solves* each generator's reactive power — or
   **PQ** (injecting the recorded reactive) when the grid sits directly on the PDR and its
   voltage is therefore stiff/unregulable.
3. Compares OLF's resulting **bus voltages and angles**, each **generator's reactive power**
   (an output when it is PV — checked against DyCoV's Q0), and the **active/reactive flow at
   the PDR** against DyCoV's recorded values. Prints a per-case table + an overall **VERDICT**.

It reads only the handful of `.dyd`/`.par` (+ optional table) files each comparison needs
— not the full simulation outputs.

## Run

```bash
python compare_init.py                                 # bundled reference cases (default)
python compare_init.py -v                              # + per-node DyCoV-vs-OLF detail
python compare_init.py /home/dycov/Results             # EVERY case under a whole Results tree
python compare_init.py /home/dycov/Results/Model/BESS  # just the BESS subtree
python compare_init.py --all /path/to/tree             # list every case row (see below)
```

The positional argument is any directory: every folder containing a `TSOModel.par` under it
is treated as a case, **searched recursively**. With no argument it runs the bundled `cases/`.
For large trees the per-case table hides `MATCH`/`SKIP` rows (showing only divergences and
failures) and reports the rest in the aggregate verdict; pass `--all` to print every row.

Requires the optional `dynawo-pypowsybl` extra (`pypowsybl>=1.7,<2.0`).

## Reference cases (`cases/`)

One completed case per topology / grid family, chosen to exercise the whole modelling
surface. Each folder holds only the minimal files:

| folder | topology | grid family | note |
|---|---|---|---|
| `S_setpoint_bess` | S | InfiniteBus | single BESS, setpoint step |
| `Splus_aux_infbus_wtg4b` | S+Aux | InfiniteBus | single WTG4B + aux load |
| `M_main_2gen_infbus` | M+Aux (Main) | InfiniteBus | 2 generators, plant transformer |
| `Splus_aux_table_bess` | S | InfiniteBusFromTable | grid U from `TableInfiniteBus.txt` (t=0); folder name is historical, the producer has no aux load |
| `linefault_bess` | S+Aux | LineFault | fault grid line (pre-fault steady state) |
| `weakgrid_permbolted_pv` | S | InfiniteBus (weak) | very low SCR — needs the tight Newton tolerance |
| `islanding_inertialgrid` | S+Aux | InertialGrid | islanding test — historically divergent, MATCH since PR #358 |

The `topo` column follows DyCoV's official naming — `S`/`M` (single/multiple units),
`+Aux` (producer auxiliary load), `+i` (equivalent internal line) — with ` (Main)` appended
when the producer has a plant transformer (`Main_Xfmr`), which is orthogonal to the eight
official topologies. `+Aux` counts only producer-side loads (TSO loads, e.g. the islanding
`Main_Load`, don't change the topology). No case in the current catalogue uses `+i`.

The cases were frozen from a `Results` tree generated after the initialization fixes
(#354, #355/#358, #360); all seven MATCH.

## Finding (why the verdict reads as it does)

Across the full DyCoV catalogue (`Model/{BESS,Photovoltaics,Wind}`, 389 comparable cases +
55 Not-Applicable skips), OLF reproduces DyCoV's internal init — node V/angle, generator
reactive power, and PDR P/Q flow — to numerical precision (≤ ~1e-4, typically 1e-7 or
tighter) on **every** case, islanding included. So OLF adds no initialization accuracy, and
the dependency can only be justified by robustness or generality (e.g. future meshed or
asymmetric topologies).

Historical note: the **islanding** family (grid=`InertialGrid`) diverged before PR #358 —
the `Main_Load` sits electrically at the PDR but the recorded angles assumed its power
flowed through the line to the grid. The comparison against OLF pinpointed that bug (and
this tool's PDR-flow check needed the same load-side split, since the PCC setpoint includes
the local load while the OLF line flow does not). A divergence on freshly generated results
now means a regression.

## Modelling notes & caveats

* **Weak grids:** OLF's default Newton tolerance stops too early when the grid reactance is
  large; the tool uses a single non-distributed slack and `newtonRaphsonConvEpsPerEq=1e-10`
  so those cases converge to the true solution.
* **Multi-generator plants:** when several generators regulate the same PDR, OLF distributes
  the reactive power by its own rule, which need not equal DyCoV's configured per-unit share
  for an *asymmetric* plant. The only multi-generator case in the current catalogue has two
  identical units, so the split is equal and matches; an asymmetric plant could differ — and
  that difference would itself be a finding to examine, not a tool error.
* **Transformers** are taken at nominal tap (ratio 1.0), true for these completed models; a
  case with an off-nominal tap is skipped with an explicit reason.
