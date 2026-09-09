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
   for table grids) — building it in IIDM with `PypowsyblNetworkBuilder`. Every branch,
   line or transformer, enters as its **pi-equivalent**, so an off-nominal tap is modelled
   (`_branch_pimodel`, the same algebra as `dycov.electrical.pimodel_parameters.xfmr_pimodel`)
   rather than skipped; at ratio 1.0 it degenerates to the plain series branch.
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
surface with one novelty per case, so a failure points somewhere. Each folder holds only
the minimal files (`TSOModel.{dyd,par}`, `Producer*.{dyd,par}`, and the table file where the
grid needs one).

| folder | zone | topology | grid family | why this case |
|---|---|---|---|---|
| `z1_S_infbus_bess` | 1 | S | InfiniteBus | simplest case: one unit behind its group transformer |
| `z1_S_weakgrid_pv` | 1 | S | InfiniteBus (weak) | grid X = 133 pu — needs the tight Newton tolerance |
| `z3_Saux_infbus_wind` | 3 | S+Aux | InfiniteBus | the commonest Zone-3 shape |
| `z3_Saux_table_bess` | 3 | S+Aux | InfiniteBusFromTable | grid U from `TableInfiniteBus.txt` (t=0) |
| `z3_Saux_islanding_pv` | 3 | S+Aux | InertialGrid | islanding: TSO `Main_load` sits on the PDR |
| `z3_Saux_linefault_bess` | 3 | S+Aux | InfiniteBus+LineFault | fault grid line (pre-fault steady state) |
| `z3_Maux_2gen_wind` | 3 | M+Aux | InfiniteBus | two units on the internal bus, no per-unit transformer |
| `z3_Si_offnominal_tap_wind` | 3 | S+i | InfiniteBus | internal line + `Main_Xfmr` at tap 1.05 |
| `z3_Sauxi_infbus_sm` | 3 | S+Aux+i | InfiniteBus | fullest topology; synchronous machine |
| `z3_S_equivmachine_sm` | 3 | S | EquivMachine | Pcs I8: the TSO's own machine is the grid |

The `topology` column is DyCoV's official naming — `S`/`M` (single/multiple units), `+Aux`
(producer auxiliary load), `+i` (equivalent internal line) — which only Zone 3 declares;
Zone 1 is always a single unit behind its group transformer, so it is reported as `S`. The
tool prints the zone in its own column, inferred from the producer's internal bus (`Int_Bus`,
present only in Zone 3). `+Aux` counts only producer-side loads: TSO loads such as the
islanding `Main_load` do not change the topology.

The cases were frozen from a `Results` tree generated with the RTE topology catalog in place
(issue #479 / PR #480) over all 33 bundled examples — the 17 model validations under
`examples/Model/{BESS,Photovoltaics,Wind}` and the 16 performance runs under
`examples/Performance/{Single,SingleI,SingleAux,SingleAuxI}` — with Dynawo v1.8.0. All ten
MATCH.

## Finding (why the verdict reads as it does)

Over that whole tree — **564 cases, of which 505 comparable** — OLF reproduces DyCoV's
internal init (node V/angle, generator reactive power, PDR P/Q flow) on **every** case:
**0 DIVERGE**. The median node-voltage deviation is `4e-16`; the largest is `4.5e-07`, on
the table-driven grids, where `TableInfiniteBus.txt` writes the grid voltage with six
decimals (`1.044444`) while the PDR setpoint keeps full precision (`1.0444444444444445`)
— the deviation is that truncation. So OLF adds no initialization accuracy, and the
dependency can only be justified by robustness or generality (e.g. future meshed or
asymmetric topologies).

| | max deviation |
|---|---|
| node voltage | `4.5e-07` pu (`2.8e-05` on Pcs I8 — see below) |
| node angle | `4.8e-08` rad |
| generator reactive power | `4.5e-07` pu |
| PDR active / reactive flow | `8.0e-09` / `8.0e-08` pu |

Coverage of the 505: by zone, 209 Zone 1 and 296 Zone 3; by topology, `S` 238, `S+Aux` 199,
`S+i` 29, `S+Aux+i` 29, `M+Aux` 10; by grid family, `InfiniteBus` 297,
`InfiniteBusFromTable` 140, `InfiniteBus+LineFault` 34, `InertialGrid` 30, `EquivMachine` 4.
The bundled examples declare five of the eight official topologies — `M`, `M+i` and
`M+Aux+i` are not represented, so those remain unexercised.

The 59 remaining cases are skipped for two structural reasons, neither a failure:

* **55x Not-Applicable template** — `TSOModel.par` still holds un-substituted `{{...}}`
  placeholders because the test does not apply to that producer, so there is nothing to
  compare. This count has been stable across catalogue regenerations.
* **4x islanded (no grid source)** — the synchronous-machine `PCS_RTE-I10` islanding test has
  no external source at all: only `BusPDR`, the TSO `Main_load` and the unit itself. The
  tool's posing (grid source = slack) does not apply. Comparing these would need a different
  posing, with the unit as the slack.

Historical note: the **islanding** family (grid=`InertialGrid`) diverged before PR #358 —
the `Main_load` sits electrically at the PDR but the recorded angles assumed its power
flowed through the line to the grid. The comparison against OLF pinpointed that bug (and
this tool's PDR-flow check needed the same load-side split, since the PCC setpoint includes
the local load while the OLF line flow does not). A divergence on freshly generated results
now means a regression.

## Modelling notes & caveats

* **Weak grids:** OLF's default Newton tolerance stops too early when the grid reactance is
  large (a tiny reactive residual becomes a visible voltage error); the tool uses a single
  non-distributed slack and `newtonRaphsonConvEpsPerEq=1e-10` so those cases converge to the
  true solution. `z1_S_weakgrid_pv` demonstrates it: at OLF's default epsilon it stops after
  2 iterations and DIVERGEs at `1.5e-04` rad.
* **Off-nominal taps** are modelled, not skipped: the ratio is the terminal-1-to-terminal-2
  voltage gain, entered as the pi-equivalent's asymmetric shunts. `test_compare_init.py`
  pins that encoding against pypowsybl's own two-windings transformer. A *phase-shifting*
  tap (`AlphaTfo0` non-zero) is still skipped with an explicit reason; no bundled case has one.
* **Pcs I8** replaces the infinite bus with an equivalent synchronous machine on the TSO side,
  reported as grid family `EquivMachine`: a generator the TSO model owns is the grid (slack at
  its recorded voltage), one the producer owns is a plant unit. Its two grid-side loads carry
  a `load_U0Pu` written with four decimals (`1.0453`) where the machine on the same node has
  `1.0453281096051348`; that rounding is the `2.8e-05` above, and every computed quantity in
  those cases still agrees to `1e-12` or better.
* **Multi-generator plants:** the units now hang directly off the internal bus, with no
  per-unit transformer between them, so the reactive split is not fixed by any impedance. When
  several generators regulate the same PDR, OLF distributes reactive power by its own rule,
  which need not equal DyCoV's configured per-unit share for an *asymmetric* plant. The only
  multi-generator case in the catalogue shares 0.5/0.5, so both splits are equal and match; an
  asymmetric plant could differ — and that difference would itself be a finding to examine,
  not a tool error.
* **The PDR bus** is identified by the parameter set DyCoV names `PDR`, not by position: a
  Zone-3 producer contributes its own `Int_Bus`, and Pcs I8 adds a third bus on the grid side.
