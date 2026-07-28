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
`Dynawo/Zone3` trees are written. `.xlsx` is parsed with the standard-library reader reused from
`tools/dynawo_par`.

**Sheets used**

| Sheet | Role |
| :--- | :--- |
| `Général` | Block selection (`REPC/REEC/REGC/WTGT/WTGP/WTGA/WTGQ` → variant or `Aucun`) and the `Model Map` lookup cells. |
| `Model Map` | Variant tuple → Dynawo `lib` + prefix, per zone (§6). |
| `Zone1<x>` (`Zone1a`, …) | One sheet per generator. Zone-1 data: `SnZone1`, `N_Zone1`, `ConverterLVControl`, `Un1`, `Un2`, internal `LvTr` (`Z_cc_LvTr`, `R_cc_LvTr / X_cc_LvTr`), external step-up (`r_TG`, `Z_cc_TG`, `R_cc_TG / X_cc_TG`), `Pmax_injection_z1`, `Pmax_soutirage_z1`, `Qmax_z1`, `Qmin_z1`, `P_share`, `Q_share`. |
| `Zone3` | Exactly one. `Topologie`, `SnZone3`, `Un_PDR`, `Pmax_PDR`, `Qmax_PDR`, `Qmin_PDR`, main transformer (`Z_cc_TP`, `R/X`, `N_prises`, `r_max`, `r_min`), aux load (`+Aux`), collector (`+i`). |
| `REPC` / `REEC` / `REGC` / `Mechanical Part` | Control-block parameters, one column group per variant (`Parameter | Type | Value`, optional `Base unit` / `Comment`). |
| `Signaux zone 1/3`, separator sheets | Ignored. |

**Layout.** The two zone sheets use different column layouts, so the parser locates the header row
and the *Valeurs* column per sheet rather than hardcoding a column:
- **`Zone1a`** — header `Paramètres | Descriptions | Valeurs | Unités | Commentaires`; name in col A,
  value in col C.
- **`Zone3`** — header `Catégorie | Paramètres | Descriptions | Valeurs | …`; name in col B, value in
  col D (col A is a category label).

Semantics: `Un1` = HTA/primary (node-1 nominal), `Un2` = BT/secondary (converter side);
`ConverterLVControl` is text `"True"`/`"False"`; `R_cc_* / X_cc_*` rows are the **R/X ratio** `k`
(§7), not impedances.

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
  Excel bare name) + network element parameters (computed, §7). Empty Excel cells are omitted
  (Dynawo defaults). Initialization / power-flow parameters (`i0Pu`, `u0Pu`, `PInj0Pu`, …) are not
  in the Excel and are injected by DyCoV at simulation setup.

Each `<par>` carries the Excel-derived origin comments of the `dynawo_par` format
([design §8.3](Dynawo_par_generation_from_excel_design.md)); files are laid out (blank-line groups)
like the `examples/Model/**` references so they read/diff cleanly.

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

**The model is resolved in the Excel.** A `Model Map` sheet maps the variant selection to the exact
Dynawo `lib` and its **prefix**, per zone (Zone3 plant + Zone1 turbine); the tool reads those cells,
so **no Dynawo install is needed at generation time**. AIA builds/maintains the `Model Map` from the
Dynawo `ddb` offline, in sync with the simulation Dynawo version.

**Parameter names carry the model prefix.** The Excel holds bare names (`Kqp`); each WECC model is a
compiled composite whose descriptor flattens every parameter to `<prefix>_<Param>`
(`photovoltaics_Kqp`) and the AC port to `<prefix>_terminal`. Dynawo binds by the exact flattened
name, so the tool **prepends the resolved prefix** to every converter parameter — in both the PAR
(`photovoltaics_Kqp`) and the DYD (`photovoltaics_terminal`). Parameter **type and value** are the
only data taken verbatim from the Excel (`type` mapped to the Dynawo convention, `double → DOUBLE`).

**Resolution is unambiguous (injective).** The variant tuple `(REPC, REGC, REEC, WTGT, WTGP, WTGA,
WTGQ)` determines one model, so no separate model field is needed and technology (PV/BESS/Wind) is
derived. Observed Zone3 (plant-control) map:

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

---

### 7. Transformers and electrical computations

Dynawo transformer/line impedances are per-unit on `SnRef = 100 MVA`. Transformer `(RPu, XPu)` on
`SnRef` from `Z_cc` (pu on `SnZone`) and `k = R_cc/X_cc`:
```
X_cc = Z_cc / sqrt(1 + k²);  R_cc = k · X_cc;   XPu = X_cc · 100 / SnZone;   RPu = R_cc · 100 / SnZone
```

Per `Zone1` unit the tool writes **two distinct transformers**, from **separate** `Zone1a` fields:

- **Internal `LvTr`** — `RLvTrPu`/`XLvTrPu` (required by the model; no `B`/`G`) from `Z_cc_LvTr` +
  `R_cc_LvTr / X_cc_LvTr` (base `SnZone1`). The template ships a neutral `1E-4` to replace.
- **External `StepUp_Xfmr`** — `TransformerFixedRatio` (fixed ratio, no OLTC) from `Z_cc_TG` +
  `r_TG` + `R_cc_TG / X_cc_TG` (base the zone's `Sn`), present **only when `ConverterLVControl =
  True`** (below).

`ConverterLVControl` states the side the converter control measures on and drives two things:
(i) its per-unit nominal voltage in the INI — **`u_nom_at_PDR` = `Un2` (BT) if `True`, `Un1` (HTA)
if `False`** (same `Un1` across `Zone1`s); (ii) whether the external `StepUp_Xfmr` exists —
**`True` ⇒ present; `False` ⇒ absent** (the internal `LvTr` alone carries the step-up).

Other elements: **`Main_Xfmr`** (`TransformerRatioTapChanger` from `Zone3`'s `Z_cc_TP` + taps
`NbTap = N_prises + 1`, `RatioTfoMin/Max = r_min/r_max`) groups all generators — **`M` only**;
**collector line** (`+i`) from `R_rc/X_rc/B_rc/G_rc` with `Zbase = Un1²/100`; **aux load** (`+Aux`)
`LoadAlphaBeta` from `P_A/Q_A/alpha/beta` + `AuxLoad_Xfmr` from `Z_cc_TA/r_TA/Sn_A`. Converter
`SNom` = `SnZone`.

> The tool honors `ConverterLVControl` (it is Excel data). When `False` it drops the `StepUp_Xfmr`
> block. Making DyCoV's core **accept** a no-`StepUp` `S` model (`topology_checks` / `init_calcs`)
> is a separate, Excel-agnostic change; the tool does not wait for it.

---

### 8. Submodel report (no parameter validation)

The tool does not police parameter values. Per run it reports, at the submodel level: the resolved
model (or "unresolved" if the variant tuple matches none); which control submodels (`REPC`, `REEC`,
`REGC`, `WTGT/WTGP/WTGA/WTGQ`) are present or missing; and the observed variant→model map.

---

### 9. Testing

Tests live under `tests/tools/` (standard `pytest`):
- **Map/pairing**: the variant→model map is injective and every plant model has its 1:1 turbine
  sibling.
- **Golden**: for a committed AIA-authored fixture (`WECCSample_full.xlsx`, invented values), the
  generated `dyd`/`par` match `examples/Model/**` structurally (connects + block libs).
- **Electrical**: transformer/base conversions against known values.
- **Parsing / submodel report**: layouts, unknown-combo detection, present/missing blocks.

---

### 10. Open with RTE

Sent to and largely answered by RTE; the standing note is
[`DyCoV_input_generation_RTE_questions.md`](DyCoV_input_generation_RTE_questions.md). Still needed:
- **Parameter names** for the added variant columns `REGC_B`, `REEC_B`, `WTGP_B` (RTE fills names,
  the end user the values).
- **Review of the variant→model map** for completeness across the WECC models RTE supports.
- **`M`: how each `Zone1<x>`'s model is selected** — the single `Général` selection resolves one
  model, so the Excel cannot yet say which model each duplicated `Zone1<x>` is. Blocks `M`.
- **Possible new scope:** electrical validations of the user-entered values.
