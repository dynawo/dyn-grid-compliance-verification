# olf_init_check — is OpenLoadFlow worth it for initialization?

Evidence tool for a single decision: **should DyCoV add PyPowsybl / OpenLoadFlow (OLF)
as a dependency to initialize the equivalent network?** If DyCoV's own internal
(closed-form, ad-hoc) initialization is already as good as an independent AC load flow,
the dependency is not worth the maintenance cost.

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
| `M_main_2gen_infbus` | M+Aux+Main | InfiniteBus | 2 generators, plant transformer |
| `Splus_aux_table_bess` | S+Aux | InfiniteBusFromTable | grid U from `TableInfiniteBus.txt` (t=0) |
| `linefault_bess` | S(+Aux) | LineFault | fault grid line (pre-fault steady state) |
| `weakgrid_permbolted_pv` | S | InfiniteBus (weak) | very low SCR — needs the tight Newton tolerance |
| `islanding_inertialgrid` | S+Aux | InertialGrid | islanding test — the divergence case |

## Finding (why the verdict reads as it does)

Across the full DyCoV catalogue (`Model/{BESS,Photovoltaics,Wind}`), OLF reproduces DyCoV's
internal init — node V/angle, generator reactive power, and PDR P/Q flow — to numerical
precision (≤ ~1e-4, typically 1e-7 or tighter) on every non-islanding, non-Not-Applicable
case. So OLF adds no initialization accuracy there. The **islanding** cases are the
exception: a local load sits electrically at the PDR, but DyCoV's recorded angles correspond
to that power flowing through the line to the grid, so its closed-form init is not
AC-consistent; OLF returns the physically consistent operating point. That single family is
the only correctness argument for the dependency (beyond robustness / generality).

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
