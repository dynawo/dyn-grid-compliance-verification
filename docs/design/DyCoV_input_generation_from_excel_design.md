## DyCoV Input Generation from Excel (WECC first) — Design

### 1. Purpose

A tool that reads an RTE Excel model specification (model selection, network topology, electrical
data, control parameters) and generates a complete DyCoV `Model` input set:

```
<output>/Dynawo/Zone1/Producer.{ini,dyd,par}
<output>/Dynawo/Zone3/Producer.{ini,dyd,par}
```

The generation **core is standard-agnostic**: the family (WECC / IEC) is confined to a thin
front-end that parses the family's Excel and resolves the selected variants to a concrete Dynawo
model class; everything downstream depends only on the resolved model, the Excel values and the
topology. WECC is the first — and today only — front-end.

The tool does **not** validate Excel parameter values or completeness — RTE ships a complete
template. Its only checking role is at the **submodel** level (§8).

---

### 2. Scope

**Topology codes.** `Zone3`'s `Topologie` is `{S | M}`, optionally followed by `+Aux` and/or `+i`.
`S` = one `Zone1` sheet (single generator); `M` = one `Zone1<x>` sheet per generator. `+Aux` =
auxiliary load + its transformer; `+i` = aggregated HV collector line (PI model).

**In scope:** `Producer.{ini,dyd,par}` for Zone1 and Zone3, single-`Zone1` topologies
(`S`, `S+Aux`, `S+i`, `S+Aux+i`), plus the submodel report (§8).

**Deferred / out of scope:**
- **`M` (multi-generator):** N `Zone1<x>` sheets → N `Producer_G{i}` in Zone1 + one `Zone3` with the
  `M` topology (N `StepUp_Xfmr_i` grouped by `Main_Xfmr` = `Z_cc_TP`). The builders are parametrized
  to N; open are the tool's `M` orchestration and how each `Zone1<x>`'s model is selected (§10).
- The `.crv`, `ReferenceCurves/`, `CurvesFiles.ini` — DyCoV generates these at simulation setup.
  The `Signaux zone 1/3` sheets are informative only.
- The **IEC front-end** — a new adapter on the same core, no core change.
- Integration into DyCoV as a subcommand — starts standalone (like `tools/dynawo_par`).

---

### 3. Input

**CLI**
```bash
python generate_inputs.py --excel model.xlsx --outdir <path>
```
`--excel` is the WECC workbook (single source of truth); `--outdir` is where the `Dynawo/Zone1` and
`Dynawo/Zone3` trees are written. `.xlsx` is parsed with the tool's own standard-library engine
(`workbook.py`), which the legacy `tools/dynawo_par` also imports until its retirement.

**Sheets used**

| Sheet | Role |
| :--- | :--- |
| `Général` | Block selection (`Type de bloc \| Choix \| Zone`: block → variant or `Aucun`, plus the `;`-separated zones the block's parameters go to) and the Excel-computed `Model Map` lookup key (derived table; the tool reads the cached key cell verbatim). |
| `Model Map` | Variant tuple → Dynawo `lib` + prefix, per zone (§6). |
| `Zone1<x>` (`Zone1a`, …) | One sheet per generator. Zone-1 data: `SnZone1`, `N_Zone1`, `ConverterLVControl`, `Un1`, `Un2`, internal `LvTr` (`Z_cc_LvTr`, `R_cc_LvTr / X_cc_LvTr`), external step-up (`r_TG`, `Z_cc_TG`, `R_cc_TG / X_cc_TG`), `Pmax_injection_z1`, `Pmax_soutirage_z1`, `Qmax_z1`, `Qmin_z1`, `P_share`, `Q_share`. |
| `Zone3` | Exactly one. `Topologie`, `SnZone3`, `Un_PDR`, `Pmax_PDR`, `Qmax_PDR`, `Qmin_PDR`, main transformer (`Z_cc_TP`, `R/X`, `N_prises`, `r_max`, `r_min`), aux load (`+Aux`), collector (`+i`). |
| `REPC` / `REEC` / `REGC` / `Mechanical Part` | Control-block parameters, one column group per variant, headed by `Paramètres` (French or English, accent-insensitive, and any parenthetical such as `Paramètres (Dynawo)`); optional `Bases…`/`Base unit`, `Commentaires`/`Comment` columns. |
| `Signaux zone 1/3`, separator sheets | Ignored. |

**Layout.** Nothing is addressed by a fixed column. In a control sheet, the header row is the first
one naming parameters, values and types — requiring all three keeps the zone sheets' `Paramètres |
Descriptions | Valeurs` tables out — and each variant's value and type columns are the nearest such
headers to the right of its `Paramètres` column, inside its table block. That resolves both layouts
in use: `Paramètres | Types | Valeurs` per variant, and `Paramètres | Valeurs` repeated with a
single `Types` column shared by the variants of the block.

The two zone sheets use different column layouts, so the parser locates the header row and the
*Valeurs* column per sheet rather than hardcoding a column:
- **`Zone1a`** — header `Paramètres | Descriptions | Valeurs | Unités | Commentaires`; name in col A,
  value in col C.
- **`Zone3`** — header `Catégorie | Paramètres | Descriptions | Valeurs | …`; name in col B, value in
  col D (col A is a category label).

Semantics: `Un1` = HTA/primary (node-1 nominal), `Un2` = BT/secondary (converter side);
`ConverterLVControl` is text `"True"`/`"False"`; `R_cc_* / X_cc_*` rows are the **R/X ratio** `k`
(§7), not impedances.

Every zone field reaches the output except three, which are informative:

- `N_Zone1`, the converter count: the workbook itself multiplies it by `SnZone1` to obtain
  `SnZone3`, and the tool reads that result.
- `Un2`, the converter side's nominal: it tells whoever fills the workbook which voltage base the
  control per-unit values are on (`Un2` when `ConverterLVControl = True`, `Un1` otherwise), and
  names the base the impedance rows refer to. The WECC models take no nominal-voltage parameter,
  and the network blocks take ratios (`r_TG`, `r_TA`), not levels.
- `Un_A`, the auxiliary load's nominal: no Dynawo parameter of the auxiliary transformer or load
  takes it (the ratio comes from `r_TA`, the impedance base from `Sn_A`).

---

### 4. Output

Three files per zone. The resolved model class (§6) drives the `lib` ids and the parameter-name
prefix; parameter type/value come from the Excel (§6):

- **Producer.ini** — DTR envelope + topology: `p_max_injection_at_PDR`, `u_nom_at_PDR`,
  `q_max_at_PDR`, `q_min_at_PDR`, `topology`, `P_sharing_*`, `Q_sharing_*`.
- **Producer.dyd** — a `blackBoxModel` for the converter (resolved `lib`), the topology network
  blocks and the `connect` lines. The converter terminal is `<prefix>terminal`. Zone3 uses the
  **plant** lib, Zone1 its **turbine** sibling (§6).
- **Producer.par** — one `set` per id: the converter parameters from the Excel (name = prefix +
  Excel bare name) + network element parameters (computed, §7). Each zone's PAR carries the blocks
  that declare that zone in `Général`'s `Zone` column, in the **workbook's own order** (sheet →
  table → parameter) — the Excel alone determines the PAR order, so diffs stay stable; a selection
  where no block declares `Zone1` is refused (never a silently incomplete `Zone1`). Empty Excel
  cells are omitted (Dynawo defaults). Initialization / power-flow parameters (`i0Pu`, `u0Pu`,
  `PInj0Pu`, …) are not in the Excel and are injected by DyCoV at simulation setup.

A variant's first parameter opens its section with a comment naming the variant, and a parameter
carrying a base unit or a comment in the workbook gets one too, with the `Un1 ou Un2` base resolved
to the side in force. The template's placeholder annotations (`-`, `/`) are dropped rather than
copied. Files are laid out (blank-line groups) like the `examples/Model/**` references so they
read and diff cleanly.

---

### 5. Architecture

```
generate_inputs.py                       CLI + orchestration

┌─ FRONT-END (per standard: wecc, later iec) ───────────────────────────────┐
│  read_workbook / parse Général / parse Zone1<x> & Zone3 / parse controls   │
│  resolve_models()   variant tuple -> exact model class + prefix (§6)       │
└────────────────────────────────────────────────────────────────────────────┘
        │  normalized case: { model class, prefix, plant/turbine pair,
        ▼                     Excel params (bare name/type/value), topology + electrical }
┌─ CORE (standard-agnostic) ─────────────────────────────────────────────────┐
│  submodel_report (§8) · electrical helpers (§7) · build ini/dyd/par per zone│
└────────────────────────────────────────────────────────────────────────────┘
```

- **The front-end is the only standard-specific layer** — the Excel schema and the variant→model
  resolver. It emits a normalized case; the core never branches on WECC vs IEC. Adding IEC = a new
  front-end adapter.

---

### 6. Model resolution and parameters

**The model is resolved in the Excel.** `Général` carries a derived table where Excel itself
computes the `Model Map` lookup key from the block selection; the tool reads that cached cell
verbatim (locating it as the column left of the `Zone3 lib` header) and **never reconstructs it**,
so it has no knowledge of which blocks form the key. A `Model Map` sheet then maps the key to the
exact Dynawo `lib` and its **prefix**, per zone (Zone3 plant + Zone1 turbine); its key column is
located the same way, so the key header's name is free. The tool reads those cells, so **no Dynawo
install is needed at generation time**. AIA builds/maintains the `Model Map` from the Dynawo `ddb`
offline, in sync with the simulation Dynawo version. A workbook whose key cell is empty (saved by a
non-Excel writer, hence without cached formula values) is rejected with a message asking to open
and save it in Excel.

**Parameter names carry the model prefix.** The Excel holds bare names (`Kqp`); each WECC model is a
compiled composite whose descriptor flattens every parameter to `<prefix>_<Param>`
(`photovoltaics_Kqp`) and the AC port to `<prefix>_terminal`. Dynawo binds by the exact flattened
name, so the tool **prepends the resolved prefix** to every converter parameter — in both the PAR
(`photovoltaics_Kqp`) and the DYD (`photovoltaics_terminal`). Parameter **type and value** are the
only data taken verbatim from the Excel (`type` mapped to the Dynawo convention, `double → DOUBLE`).

**Resolution is unambiguous (injective).** The variant selection determines one model, so no
separate model field is needed and technology (PV/BESS/Wind) is derived from the resolved `lib`.
Observed Zone3 (plant-control) map (maintained in the Excel, not in the tool):

| Model (Zone3 `lib`) | tech | REGC | REEC | WTGT/WTGP/WTGA/WTGQ |
| :--- | :-- | :-- | :-- | :-- |
| PhotovoltaicsWeccCurrentSource | PV | a | b | – / – / – / – |
| PhotovoltaicsWeccVoltageSource1 | PV | b | a | – / – / – / – |
| PhotovoltaicsWeccVoltageSource2 | PV | b | b | – / – / – / – |
| PhotovoltaicsWeccVoltageSource3 | PV | c | a | – / – / – / – |
| PhotovoltaicsWeccVoltageSource4 | PV | c | b | – / – / – / – |
| BESSWeccCurrentSource | BESS | a | c | – / – / – / – |
| WTG3WeccCurrentSource1 | Wind | a | a | a / a / a / a |
| WTG3WeccCurrentSource2 | Wind | a | a | a / b / a / a |
| WTG4AWeccCurrentSource | Wind | a | a | b / – / – / – |
| WTG4BWeccCurrentSource | Wind | a | a | – / – / – / – |

**Plant ↔ turbine pairing (1:1).** Zone3 is the plant model (with REPC); Zone1 is its turbine
sibling (same tuple, REPC removed): PV/BESS `X` ↔ `X`**`NoPlantControl`**; wind **`WTG`**`*` ↔
**`WT`**`*`. The generator emits the matched pair.

**`/` means "does not apply to this variant".** In the parameter name cell it drops the row for that
variant; in the value cell the parameter still belongs to the variant but counts as unfilled, as
the final template will leave that cell empty. Either way nothing reaches the PAR — written
verbatim, `/` would, as a value or even as a parameter name. An unfilled parameter falls back to the
descriptor's `defaultValue`; those without one must be filled for Dynawo to run.

**Two parameters are derived, not read.** `ConverterLVControl` comes from the zone sheet (§7), and
`PPCLocal` has no template row: it is always `false`, and emitted only among the `Zone3`
parameters, since it exists in the plant `lib`s and in none of the turbine ones.

**Values are written verbatim, shortened.** A `DOUBLE` is re-rendered as the shortest text that
round-trips to the same number, so the 17 digits Excel stores for `1e-5` do not reach the PAR.
Other types are copied as they are.

---

### 7. Transformers and electrical computations

Dynawo **network elements** (transformers, lines) take per-unit values on `SnRef = 100 MVA`, so a
`Z_cc` (pu on `SnZone`) with `k = R_cc/X_cc` becomes:
```
X_cc = Z_cc / sqrt(1 + k²);  R_cc = k · X_cc;   XPu = X_cc · 100 / SnZone;   RPu = R_cc · 100 / SnZone
```
The **WECC model's own** impedances are instead per-unit on its `SNom`, so `Z_cc_LvTr` (pu on
`SnZone1`) is split into `R_cc`/`X_cc` and written unrebased. The same number serves both zones:
Zone1's `SNom` is `SnZone1` already, and in Zone3 aggregating the `N` generator transformers in
parallel onto `SnZone3 = N · SnZone1` cancels out.

A `Zone1<x>` block describes two transformers, and each lands on a different side of the seam
between the **Dynawo model** and the **network** DyCoV builds around it:

- the converter's internal `LvTr` — `RLvTrPu`/`XLvTrPu` (no `B`/`G`) from `Z_cc_LvTr` +
  `R_cc_LvTr / X_cc_LvTr` — is a *model* parameter;
- the generator transformer — `TransformerFixedRatio` from `Z_cc_TG` + `r_TG` +
  `R_cc_TG / X_cc_TG` — is a *network* block, `StepUp_Xfmr`, in both zones.

`ConverterLVControl` decides which of the two carries the step-up, and the model enforces it
(`Controls/WECC/Parameters/ParamsLvTfo.mo`): `True` zeroes the model's own branch, so the network
block must be there; `False` puts `RLvTrPu` in it, so the block is dropped and the generator wired
to its downstream node. It also states the side the converter control measures on, hence the
converter's own nominal voltage (`Un2` when `True`, `Un1` when `False`), which the values the user
types are per-unit of.

The INI's `u_nom_at_PDR` is a different thing: the nominal voltage of the node each zone connects
at. `Zone3` connects at the real PDR and carries `Un_PDR`, which the DTR requires to be one of its
normalized levels; `Zone1` connects at its internal node and carries `Un1`, typically an HTA level,
which the DTR leaves free (§10).

The **main HTB/HTA transformer** (`Main_Xfmr`, `TransformerRatioTapChanger` from `Z_cc_TP` + taps
`NbTap = N_prises + 1`, `RatioTfoMin/Max = r_min/r_max`, base `SnZone3`) belongs to the `M`
topologies only, where each `Zone1<x>` also keeps its own `StepUp_Xfmr_<i>`. In the
single-generator topologies `Zone3` is one `Zone1` seen at plant scale, so its only external
transformer is the generator one and `Zone3`'s tap rows stay unused.

Other elements: **collector line** (`+i`), the aggregated network as a PI model in
`IntNetwork_Line`, from `R_rc/X_rc/B_rc/G_rc` in ohms and siemens with `Zbase = Un_PDR²/100` — the
block connects to the PDR with no transformer in between, so that is its voltage base, whatever
level the ohms were measured at; **aux load** (`+Aux`)
`LoadAlphaBeta` from `P_A/Q_A/alpha/beta` + `AuxLoad_Xfmr` from `Z_cc_TA/r_TA/Sn_A`. Converter
`SNom` = `SnZone`.

---

### 8. Submodel report (no parameter validation)

The tool does not police parameter values. Per run it reports, at the submodel level: the resolved
model (or "unresolved" if the key matches no `Model Map` row) and, for every block listed in
`Général` (no fixed family list), whether its parameter sheet contributed a selected variant with
values (present/missing).

---

### 9. Testing

Tests live under `tests/tools/` (standard `pytest`):
- **Map/pairing**: the variant→model map is injective and every plant model has its 1:1 turbine
  sibling.
- **Golden**: for a committed AIA-authored fixture (`WECCSample_full.xlsx`, invented values), the
  generated `dyd`/`par` match `examples/Model/**` structurally (connects + block libs).
- **Electrical**: transformer/base conversions against known values.
- **Parsing / submodel report**: layouts, unknown-combo detection, present/missing blocks.

Template parameter names are audited separately against a Dynawo `ddb`, matching every row of the
control sheets to the `.desc.xml` of both `lib`s of every `Model Map` row (exact → case-insensitive
→ normalized, dropping a trailing `pu`), and classifying what does not match: capitalization-only,
unit-suffix, Excel-only, model-only (a defect only where the descriptor has no `defaultValue`),
`readOnly` offered for editing, type disagreement, or two rows targeting one parameter. Names go
verbatim into the PAR and Dynawo ignores what it does not recognize, so a mis-named row binds
nothing and raises no error.

---

### 10. Open points

- **A regulated generator transformer.** The step-up is emitted as a `TransformerFixedRatio`
  because `Zone1<x>` gives it a ratio (`r_TG`) and no tap data, while every `examples/Model/**`
  case uses `TransformerRatioTapChanger`. Proposal for RTE: add `N_prises`, `r_max` and `r_min` to
  `Zone1<x>`, next to `r_TG` and named as in `Zone3`, and let the lib follow the data — tap data
  present ⇒ regulated, `N_prises = 0` or empty ⇒ fixed ratio, with a template comment saying so.
  The rule then reads the same for the three transformers. It also asks a little of the tool:
  `RatioTfo0Pu` becomes the given ratio rather than `1.0`, and `Tap0` the tap that matches it,
  `round((r − r_min) / (r_max − r_min) · N_prises)`.
- **`M`: how each `Zone1<x>`'s model is selected.** The single `Général` selection resolves one
  model and duplicating a `Zone1<x>` copies only electrical data, so the Excel cannot say which
  model each generator is when they differ (e.g. `WECC4` mixes `WTG4A`+`WTG4B`). Blocks `M`, and
  needs a design before it can be asked as a question.
- **[dycov#477](https://github.com/dynawo/dyn-grid-compliance-verification/issues/477).** DyCoV
  applies the PDR level check to both zones, so a `Zone1` whose `Un1` is not a normalized level is
  rejected outright ("Unexpected nominal voltage at the PDR bus"). The shipped examples repeat
  `Un_PDR` in both zones and will want regenerating with the zone-1 node's real voltage.
- **Awaiting RTE:** a review of the variant→model map for completeness across the WECC models they
  support. Electrical validation of the user-entered values is possible extra scope.
- **`WTG3WeccCurrentSource2` is mis-packaged in `Dynawo_v1.8.0_20260822`.** Its
  descriptor is parameter-for-parameter identical to `WTG3WeccCurrentSource1` (the `WTGPa` pitch),
  while its `.mo` extends `ParamsWTGPb` and its `.mandatoryParam` lists `Theta{C,W}{Max,Min}`,
  which only the turbine-side `WeccWT3CurrentSource2` exposes. The `WTGP_B` rows therefore cannot
  bind in `Zone3` with that build; the template is correct.
