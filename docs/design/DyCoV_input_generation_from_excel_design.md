## DyCoV Input Generation from Excel (WECC first) — Design

### 1. Purpose

Describe a tool that reads an RTE Excel model specification (model selection, network topology,
electrical data and control parameters — the revision that describes the full plant) and
generates a **complete DyCoV `Model` input set**:

```
<output>/Dynawo/Zone1/Producer.ini
<output>/Dynawo/Zone1/Producer.dyd
<output>/Dynawo/Zone1/Producer.par
<output>/Dynawo/Zone3/Producer.ini
<output>/Dynawo/Zone3/Producer.dyd
<output>/Dynawo/Zone3/Producer.par
```

This supersedes the earlier "PAR fragments" utility
([Dynawo_par_generation_from_excel_design.md](Dynawo_par_generation_from_excel_design.md)),
which only produced a handful of `<par>` lines. That document is kept as history.

The generation **core is standard-agnostic**: the family (WECC / IEC) is confined to a thin
front-end whose only job is to parse the family's Excel and resolve the selected variants to a
concrete Dynawo model class; everything after that depends only on the resolved model, the
Excel-provided values and the ddb (§3, §6). **WECC is the first — and today only — front-end.**

**The tool does NOT validate the Excel parameters.** RTE is responsible for shipping a
template that already contains every parameter needed. The tool's only checking role is at
the **submodel** level: report which control submodels (`RE?C`, `WTG*`) the selection
contains and which are missing, and show the **observed** submodel→model map (§7.2, §8).

---

### 2. Status at a glance — what we can do today vs. what we know is missing

Written up front on purpose. It captures **what is already clear** (much of it verified
against a real Dynawo install, `/opt/Dynawo_v1.8.0_20260714`); more will surface during
implementation and be added here.

#### 2.1 What we can generate today (given a correctly-filled Excel)

| Output | Status | Source / note |
| :--- | :--- | :--- |
| `Producer.ini` (Zone1 & Zone3) | **Ready** | `Zone1<x>` / `Zone3`: p/q/u at PDR, `topology`, P/Q sharing (§9). |
| `Producer.par` — network part (transformers), topology `S` | **Ready** | Mapping fixed (§7.4): `Zone1a`→`LvTr`, `Zone3`→`StepUp_Xfmr`; pu-base conversion settled (`SnRef=100`, §9). (`M` needs an extra generator-transformer table — §7.4.) |
| `Producer.par` — control-block values | **Ready** | Type/value from the Excel; **name = model prefix + Excel (bare) name** (§7.1) — this fixes a `dynawo_par` gap (it omits the prefix); empty cells omitted (Dynawo defaults). |
| `Producer.dyd` — blocks & connections, topology `S` | **Ready once the model is resolved** | From `examples/Model/**` templates + the resolved converter `lib` (§7.2). |
| **Submodel report + observed map** | **Ready** | §8. |

#### 2.2 What we already know is missing / to close

| Item | Kind | Ref |
| :--- | :--- | :--- |
| **[Done]** 3 variant columns — `REGC_B`, `REEC_B`, `WTGP_B` — were missing (verified vs the ddb; all blocks present, nothing extra). AIA added the empty columns (track changes); **RTE** adds the parameter names, the **end user** the values | Template change (AIA done) | §7.2, §11 |
| Confirm the observed submodel→model map is **complete** for all WECC models RTE cares about | Needs RTE review | §7.2 |
| For **`M`**: the per-generator **step-up transformer** is not in the Excel (`Zone1a` = internal `LvTr`) — a generator-transformer table must be added | Template-design gap (`M` only) | §7.4, §11 |
| **How to resolve `lib` + prefix** — against a Dynawo install or defined in the Excel — is **RTE's call (Q1)**. If against an install: read the **compiled descriptors** (`<lib>.desc.xml`/`.extvar`), not the `.mo` sources (`tools/wecc_model_map` parses `.mo`, names differ), pairing by variant tuple | Needs RTE decision (Q1) | §7.1, §7.2 |

**Resolved (no longer gaps).** The exact model is a **deterministic, injective** function of
the selected submodel variants — proven against the ddb (§7.2), so **no separate model
selector is needed** once the vocabulary is complete. Technology (PV/BESS/Wind) is likewise
**derived** from the variant tuple. The variant→model map **and the model prefix** are **read
directly from the Dynawo install** (`ddb`, §7.2, §7.1), not hand-maintained — fixed the moment
the model is resolved. Parameter **types and values** come from the Excel; the **name is the
Excel (bare) name with that prefix prepended** (§7.1). Only Excel cells that carry a value are
written; an empty/absent parameter is omitted and Dynawo applies its default.

---

### 3. Scope

**Topology codes.** The `Topologie` field of `Zone3` is `{S | M}` optionally followed by
`+Aux` and/or `+i`. The first letter is the generator count: **`S` = Single** (one `Zone1`
sheet), **`M` = Multi** (two or more `Zone1<x>` sheets, one per generator). The suffixes are
orthogonal network additions: **`+Aux`** = auxiliary load + its transformer; **`+i`** =
aggregated HV collector network (PI model). Family: `{S|M} × (+Aux?) × (+i?)`.

**In scope (first iteration):**
- Generate `Producer.{ini,dyd,par}` for **Zone1 and Zone3**.
- **Topology `S`** only — a single `Zone1a` + main transformer, no `+Aux`, no `+i`.
- A **submodel report** (§8): observed submodel→model map + which submodels are present/missing.

**Standard-agnostic by construction.** The family (WECC / IEC) is needed **only in the
front-end**, to (a) parse its Excel and (b) resolve the selected variants to a concrete Dynawo
model class. From the resolved model onward — mapping the Excel-provided values to their Dynawo
names/prefix via the ddb, the electrical computations (§9), the network templates (§7.4) and
emitting `ini/dyd/par` — the pipeline sees only *a model name + the Excel values + the
topology*, and is **identical for WECC and IEC**. The **WECC front-end is implemented first**
because its Excel is the only one that exists today; IEC attaches to the same core when its
Excel arrives (§6).

**Out of scope (for now):**
- Validating Excel parameter values/completeness — **RTE guarantees the template is complete**.
- The **`.crv` curves file**, `ReferenceCurves/`, `CurvesFiles.ini`. DyCoV generates the `.crv`
  itself at simulation setup (it also uses the model prefix, but it is **not one of our
  inputs**). The `Signaux zone 1/3` sheets are **informative only** — DyCoV defines the PCS and
  curves internally.
- The `+Aux` and `+i` additions.
- **`M` (Multi)**: one `Zone3` aggregating several `Zone1<x>` sheets → several `Producer_G*`
  units in DyCoV's `Zone1` folder (cf. `examples/Model/Wind/WECC4`), plus `+Aux`/`+i`.
- The **IEC front-end** (its Excel schema + variant→model resolver). The agnostic core is built
  once and needs **no change** when IEC arrives — only a new front-end adapter.
- Integration into DyCoV as a subcommand — starts as an external standalone tool (like
  `tools/dynawo_par`); DyCoV integration may come later.

---

### 4. Input

#### 4.1 CLI

```bash
python generate_inputs.py --excel model.xlsx --outdir <path> \
    [--dynawo-ddb <path>] [--standard wecc]
```

- `--excel` — the WECC Excel workbook (single source of truth).
- `--outdir` — where the `Dynawo/Zone1` and `Dynawo/Zone3` trees are written. The
  model/case name is part of this path (chosen by the user), not read from Excel.
- `--dynawo-ddb` — path to the Dynawo `ddb` used to resolve the model (the submodel→model map
  and plant/turbine pairing, §7.2–7.3) and its **prefix**, which is prepended to parameter names
  in the PAR and DYD (§7.1). Not used for PAR parameter types/values. Default: the most recent
  `/opt/Dynawo_*/dynawo/ddb`. **Version-matched** to the install used for simulation.
- `--standard` — `wecc` (default). Reserved for `iec`.

`.xlsx` is parsed with the standard library, reusing the reader from `tools/dynawo_par`.

#### 4.2 Excel sheets used

| Sheet | Role |
| :--- | :--- |
| `Général` | Block selection (`REPC/REEC/REGC/WTGT/WTGP/WTGA/WTGQ` → variant or `Aucun`). |
| `Zone1<x>` (`Zone1a`, …) | **One sheet per generator.** Zone-1 electrical data: `SnZone1`, `N_Zone1`, `ConverterLVControl`, `Un1`, `Un2`, group transformer (`r_TG`, `Z_cc_TG`, `R_cc_TG/X_cc_TG`), `Pmax_injection_z1`, `Pmax_soutirage_z1`, `Qmax_z1`, `Qmin_z1`, `P_share`, `Q_share`. |
| `Zone3` | **Exactly one.** `Topologie`, `SnZone3`, `Un_PDR`, `Pmax_PDR`, `Qmax_PDR`, `Qmin_PDR`, main transformer (`Z_cc_TP`, `R/X`, `N_prises`, `r_max`, `r_min`), aux load (`+Aux`), collector (`+i`). |
| `REPC` / `REEC` / `REGC` / `Mechanical Part` | Control-block parameters, one column group per variant, plus a "Bases pour les pu" column. Values read from `Valeurs`. |
| `Signaux zone 1/3`, `Infos générales ->`, `Paramétrage modèle ->` | **Ignored** (informative / separators). |

---

### 5. Output

For each zone, three files. The resolved model class (§7.2) drives the `lib` ids and the
parameter-name prefix; parameter type/value come from the Excel (§7.1):

- **Producer.ini** — DTR envelope + topology: `p_max_injection_at_PDR`, `u_nom_at_PDR`,
  `q_max_at_PDR`, `q_min_at_PDR`, `topology`, `P_sharing_*`, `Q_sharing_*` (from `Zone3` /
  `Zone1<x>`).
- **Producer.dyd** — one `blackBoxModel` for the converter (resolved `lib`), the topology
  network blocks (`StepUp_Xfmr`; `+Aux`/`+i` later), and the `connect` lines. The converter's
  terminal in the `connect` uses the **model prefix** (`<prefix>terminal`, §7.1). Zone3 uses the
  **plant** lib and Zone1 its **turbine** sibling — the matched pair (§7.3).
- **Producer.par** — one `set` per id: the converter parameters the Excel provides (type/value
  from the Excel, **name = model prefix + Excel bare name**, §7.1) + network element parameters
  (computed from the Excel, §9). Empty Excel cells are **omitted** (Dynawo applies defaults).
  Initialization / power-flow parameters (e.g. `i0Pu`, `u0Pu`, `PInj0Pu`) are not in the Excel
  and so never appear — DyCoV fills them at simulation setup.

Per-zone block list, `lib` ids and connections are reproduced from the reference examples
under `examples/Model/**/Dynawo/**`.

---

### 6. Architecture

```
generate_inputs.py                       CLI + orchestration

┌─ FRONT-END (per standard: wecc/, later iec/) ─────────────────────────────┐
│  read_workbook()                 (reused xlsx reader, stdlib)              │
│  parse_general()                 block selection (variant per block, Aucun)│
│  parse_zone1s() / parse_zone3()  electrical/topology data; finds Zone1<x>  │
│  parse_control_params()          REPC/REEC/REGC/Mechanical                 │
│  resolve_model()                 variant tuple -> exact model + prefix (§7.2)│
└───────────────────────────────────────────────────────────────────────────┘
        │  normalized ResolvedCase: { model class, prefix, plant/turbine pair,
        ▼                            Excel params (bare name/type/value), topology + electrical }
┌─ CORE (standard-agnostic) ────────────────────────────────────────────────┐
│  submodel_report()               present/missing RE?C & WTG*; the map (§8) │
│  electrical helpers              transformer/base conversions (§9)         │
│  build_ini()/build_dyd()/build_par()   per zone; prefix + Excel name (§7.1),│
│                                        blocks/connects from templates      │
└───────────────────────────────────────────────────────────────────────────┘
```

- **Front-end = the only standard-specific layer** (`wecc/`, later `iec/`): the Excel schema
  and the variant→model resolver. It emits a normalized `ResolvedCase`.
- **Core is standard-agnostic** — everything below the seam consumes `ResolvedCase` and never
  branches on WECC vs IEC. Adding IEC = a new front-end adapter, nothing in the core.
- **Model map is data, not code** — the variant→model map and prefix are read from the Dynawo
  install (§7.2), so adding models/versions is automatic. Parameter types/values come from the
  Excel; the name is the Excel bare name with the prefix prepended (§7.1).

---

### 7. Model resolution and parameter handling

The ddb is consulted for **model resolution** — turning the selected variants into the exact
Dynawo model class (§7.2) and its plant/turbine sibling (§7.3) — and for that model's **prefix**
(`photovoltaics_`, `BESS_`, `WTG3_`/`WT3_`, …). **The Excel parameter names have no prefix**, so
the tool must **prepend the resolved model's prefix** to every converter parameter — needed for
**both** the PAR (`photovoltaics_Kqp`) and the DYD (`photovoltaics_terminal`) (§7.1). Parameter
**types and values** are the only data taken verbatim from the Excel.

#### 7.1 Where each artifact gets its parameter data

**PAR — value/type from the Excel, name = model prefix + Excel name.** Type and value come from
the Excel (`type=` the Excel *Type* mapped `double`→`DOUBLE`, `value=` the Excel *Value*); the
parameter **name is the Excel *Parameter* cell with the resolved model's prefix prepended** — the
Excel carries the bare name (`Kqp`), the PAR needs `photovoltaics_Kqp`.
- **What gets written = exactly the Excel cells that carry a value**; an empty cell is omitted
  (Dynawo applies its default). No classification, no `mandatoryParam`.
- **This is where the new tool differs from `dynawo_par`.** `dynawo_par` writes the names
  verbatim (`_render_variant`), i.e. **without** the prefix, so its fragments do not bind to the
  Dynawo model as-is — a known limitation the new tool fixes by prepending the prefix. (The
  reference `Producer.par` under `examples/Model/**` are correct because they were written by
  hand with the prefix, not produced by `dynawo_par`.)
- **Initialization / power-flow parameters** (`i0Pu`, `u0Pu`, `PInj0Pu`, …) are simply **not in
  the Excel**, so they never appear here — DyCoV computes and injects them at simulation setup.

**DYD — same prefix, in the `connect` terminal.** The `connect` lines reference the converter's
terminal as `<prefix>terminal` (verified: `photovoltaics_terminal`, `WT3_terminal`), so the tool
builds it from the same resolved-model prefix. The transformer/bus terminals are fixed,
model-independent (`transformer_terminal1/2`, `bus_terminal`).

**Why the prefix exists (and why it is mandatory).** Each WECC model is a **compiled composite
model**: its descriptor (`<lib>.desc.xml` + `<lib>.extvar`, at the ddb root) wraps the whole WECC
model under a single component instance — `photovoltaics`, `BESS`, `WT3`, `WTG3`, … Dynawo
flattens that instance, exposing every parameter as `<instance>_<Param>` (e.g. 732
`photovoltaics_*` params) and the AC port as `<instance>_terminal`. Binding in Dynawo is by the
**exact flattened name**: the PAR matches `<par name=…>` and the DYD matches `connect var=…`
literally, so a missing prefix means *parameter/port not found* — hence it is a must-have, not a
convention we could drop.

**Where the prefix and `lib` name come from — an open RTE decision (Q1).** The prefix is
mandatory regardless; *how the tool obtains it* depends on how RTE decides to resolve the model
(§7.2, RTE questions Q1): either **(a) against a Dynawo install** — then prefix + `lib` are read
from the compiled descriptor `<lib>.desc.xml`/`.extvar` in the ddb root, whose filename **is** the
DYD `lib` (`PhotovoltaicsWeccCurrentSource`, `WeccWT3CurrentSource2`, `WTG3WeccCurrentSource2`, …);
or **(b) defined in the Excel, self-computing** — a cell auto-derives the `lib` from the variant
selection (a lookup encoding the injective map) and a second derives the `prefix` from the `lib`,
per zone; the tool reads the cells, no install needed, at the cost of maintaining the mapping
table in the template in sync with the Dynawo version (RTE Q1). **A working prototype of (b)
exists** — a `Model Map` sheet (verified 10-row variant→`lib`+`prefix` table, both zones) plus
four self-computing cells in `Général` — as a visual reference for RTE. Observed prefixes (from
the descriptors):
`photovoltaics_` (all PV), `BESS_`, and per wind model/zone `WTG3_`/`WTG4A_`/`WTG4B_` (Zone3) and
`WT3_`/`WT4A_`/`WT4B_` (Zone1). **Note for path (a):** the compiled `lib` names differ from the
`.mo` class names (`PVCurrentSource`, …) that `tools/wecc_model_map` currently parses, so a
descriptor-based resolution would key off the descriptors, not the `.mo` sources — see §7.2.

**CRV — not our output.** The `.crv` also uses the prefix, but DyCoV generates it at simulation
setup; the tool does not emit it (§3).

#### 7.2 Submodel → model map (observed, injective)

**Conclusion (verified): the selected variant tuple determines the exact WECC model
unambiguously** — the map below is *injective*, so the model is **deduced** from the
per-block variants and need not be entered separately. This was checked against the Dynawo
install with the `tools/` generator (§10), which resolves `extends` by full path and fails
if any `extends` is unresolved or any two models share a tuple.

> **Contingent on the Q1 decision — resolve against a Dynawo install, or define it in the
> Excel? (RTE decides.)** The map below (built by `tools/wecc_model_map` from the **`.mo`
> sources**) proves the variant tuple is injective, i.e. the model *can* be deduced. But whether
> the tool actually resolves against an install is Q1. **If** it does, note that the DYD `lib`,
> the prefix and the parameter set live in the **compiled descriptors** (`<lib>.desc.xml`/
> `.extvar` at the ddb root, §7.1), whose names differ from the current install's `.mo` classes
> (`PVCurrentSource` vs the `lib` `PhotovoltaicsWeccCurrentSource`); the 10 `lib` names in the
> table below match the compiled descriptors. A descriptor-based resolver would pair
> plant↔turbine **by variant tuple**, not by string transform — the wind names are irregular
> (`WTG3Wecc…`↔`WeccWT3…`, `WTG4AWecc…`↔`WT4A…`). Realigning `build_model_map` to the
> descriptors would only be needed under that path.

Every WECC producer model is a fixed composition of named submodel variants, read from the
Modelica sources (`ddb/Dynawo/Electrical/{Photovoltaics,Wind,BESS}/WECC/*.mo`, resolving
`extends`). The available variants in this install: **REGC** ∈ {a,b,c}, **REEC** ∈ {a,b,c},
**REPC** single (presence = plant control), mechanical **WTGT** {a,b}, **WTGP** {a,b},
**WTGA** {a}, **WTGQ** {a}. Observed map for the Zone3 (plant-control) models:

| Model (Zone3 `lib`) | tech | REPC | REGC | REEC | WTGT/WTGP/WTGA/WTGQ |
| :--- | :-- | :-- | :-- | :-- | :-- |
| PhotovoltaicsWeccCurrentSource | PV | A | a | b | – / – / – / – |
| PhotovoltaicsWeccVoltageSource1 | PV | A | b | a | – / – / – / – |
| PhotovoltaicsWeccVoltageSource2 | PV | A | b | b | – / – / – / – |
| PhotovoltaicsWeccVoltageSource3 | PV | A | c | a | – / – / – / – |
| PhotovoltaicsWeccVoltageSource4 | PV | A | c | b | – / – / – / – |
| BESSWeccCurrentSource | BESS | A | a | c | – / – / – / – |
| WTG3WeccCurrentSource1 | Wind | A | a | a | a / a / a / a |
| WTG3WeccCurrentSource2 | Wind | A | a | a | a / b / a / a |
| WTG4AWeccCurrentSource | Wind | A | a | a | b / – / – / – |
| WTG4BWeccCurrentSource | Wind | A | a | a | – / – / – / – |

- **Zone1** uses the `…NoPlantControl` sibling (`WT*` for wind) — same tuple with REPC absent.
- **PV and BESS have NO `WTG*` mechanical submodels** (verified). The only `WTG` trace in PV
  is `omegaRefWTGQPu0`, a `readOnly` reference scalar in REECa variants — not a block.
- **Collision check: injective** — the 10 Zone3 models map to 10 distinct
  `(tech, src, REPC, REGC, REEC, WTGT, WTGP, WTGA, WTGQ)` tuples (no model name used).
  Dropping `tech` is still injective ⇒ technology is derivable, no explicit field needed.
- Wind type-4 mechanical: WT4A carries only the drive-train variant (`WTGTb`), WT4B none —
  simpler than WT3, which carries all four blocks. All WT4/WTG4 are REGCa/REECa.
- `extends` are resolved by **full Modelica path**, not basename, to avoid the IEC/WECC
  name collision (both define a `BaseWT4`).

The generator for this map + the collision check lives in `tools/` (§10); RTE reviews the
map for completeness.

#### 7.3 Plant (Zone3) ↔ turbine (Zone1) pairing — output constraint

The two zones use a **matched pair** of models: the Zone3 **plant** model (with REPC) and
its Zone1 **turbine** model (same variant tuple, REPC removed). The pairing is **1:1** and
verified against the ddb (each Zone3 model has exactly one Zone1 sibling, no orphans):

- PV / BESS: `X` ↔ `X`**`NoPlantControl`** (e.g. `PhotovoltaicsWeccCurrentSource` ↔
  `PhotovoltaicsWeccCurrentSourceNoPlantControl`).
- Wind: **`WTG`**`*` ↔ **`WT`**`*` (e.g. `WTG3WeccCurrentSource1` ↔ `WT3CurrentSource1`,
  `WTG4A…` ↔ `WT4A…`); here `WTG` = plant, `WT` = turbine — a naming change, not a suffix.

The generator **must emit the pair**: whatever plant model Zone3 resolves to, Zone1 gets its
turbine sibling. In the multi-generator case (`M`, later) this is per generator: **each
Zone3 plant generator has its corresponding Zone1 turbine generator** (`Producer_G*`), so
the sets must line up one-to-one. The `tools/` generator (§10) checks the pairing and fails
if any plant model lacks a turbine sibling.

#### 7.4 Network templates

**DyCoV's electrical model** (authoritative — `src/dycov/electrical/initialization_calcs.py`,
`init_calcs`): per generator, a `gen` (WECC model, carrying the internal `LvTr`) behind an
explicit **`gen_xfmr`** (step-up, **one per generator** — the `gen_xfmrs` tuple; `init_calcs`
`zip`s each `gen` with its `gen_xfmr`); all `gen_xfmr` outputs join at an internal bus; then an
optional **`ppm_xfmr`** (plant transformer that **groups all generators**) → optional
`int_line` → PDR. This is exactly the RTE diagram — `StepUp_Xfmr` = `gen_xfmr`,
`PPM_Xfmr` = `ppm_xfmr`, `Int_Bus` = the internal bus:

```
gen (incl. LvTr) → gen_xfmr → Int_Bus → [ppm_xfmr] → [int_line] → PDR      (×N gens in M)
                                Aux:  Int_Bus → AuxLoad_Xfmr → Aux_Load
```

Libs: `gen_xfmr`/`ppm_xfmr` → `TransformerRatioTapChanger`/`TransformerFixedRatio`;
`AuxLoad_Xfmr` → `TransformerFixedRatio`; `Aux_Load` → `LoadAlphaBeta`; `int_line` → `Line`.

##### Transformer levels — mapping to the Excel

There are **three** transformer positions: (1) the model's internal **`LvTr`**; (2) the
per-generator explicit **`gen_xfmr`**; (3) the plant **`ppm_xfmr`**. The Excel offers **two**
transformer tables: `Zone1a` (per generator) and `Zone3` (single).

The mapping, confirmed from the Excel itself: `Zone1a` carries `ConverterLVControl` — the
WECC parameter that governs the internal `LvTr` — with a fixed ratio `r_TG`, so **`Zone1a` =
the internal `LvTr`** (1). `Zone3` (*"transformateur principal HTB/HTA"*, with OLTC) = the
plant **`ppm_xfmr`** (3).

Consequence — the explicit per-generator **`gen_xfmr` (2) has no Excel table**:
- **`S`** (one generator; no separate plant transformer, per the S examples): the single
  `Zone3` transformer serves as the one explicit step-up → `S` is complete
  (`LvTr` from `Zone1a` + one transformer from `Zone3`). Network part of `S` **not blocked**.
- **`M`** (N generators): DyCoV needs **N per-generator `gen_xfmr`** *and* the plant
  `ppm_xfmr`, but the Excel gives only `Zone1a`=`LvTr` + one `Zone3` transformer → the
  **per-generator `gen_xfmr` is missing** and a per-generator transformer table must be added.
  (This is the original *"the Excel does not contemplate the M case"* observation.)

Both `gen_xfmr` and `ppm_xfmr` are **general** transformers — each may carry real impedance
and an OLTC. The near-ideal `Main_Xfmr` in the `WECC4` example is that case's choice, **not a
rule**; there is no forced OLTC/impedance placement. So the Excel's OLTC/impedance on the
`Zone3` transformer is valid, and the per-generator `gen_xfmr` table (to be added) can carry
its own impedance/OLTC. RTE owns the formal definition of this mapping and of the missing
`M` transformer's structure.

---

### 8. Submodel reporting (no parameter validation)

**The tool does not validate Excel parameter values or completeness** — RTE ships a complete
template. What the tool reports, per run, is at the **submodel** level:

1. **Resolved model** — from the selected variant tuple via the observed map (§7.2). If the
   tuple matches no known model (e.g. an incomplete vocabulary in the template), that is
   reported as unresolved.
2. **Submodel composition** — for the resolution, which control submodels are present and
   which are **missing**: `REPC`, `REEC`, `REGC`, and `WTGT/WTGP/WTGA/WTGQ`. A block set to
   `Aucun` (or absent) is listed as missing so RTE/the user sees the full picture.
3. **The observed map** (§7.2) is emitted alongside, so it is clear how a submodel
   combination maps to a WECC model — and, conversely, which combinations are not covered.

Output: a structured report (console + optional file). It is informative; it does not police
individual parameter values.

---

### 9. Electrical computations

Confirmed: **Dynawo transformer/line impedances are pu on `SnRef = 100 MVA`.**

- **Transformer impedance** (each zone's `StepUp_Xfmr`) from that zone's `Z_cc` (pu on
  `SnZone`) and `k = R_cc/X_cc`:
  ```
  X_cc(base SnZone) = Z_cc / sqrt(1 + k²);  R_cc = k · X_cc
  XPu(base 100) = X_cc · 100 / SnZone;       RPu(base 100) = R_cc · 100 / SnZone
  ```
  Assignment (per §7.4): `Zone3` `Z_cc_TP` → the single `Zone3` transformer
  (the plant `ppm_xfmr`; in `S`, the one explicit step-up), base `SnZone3`; `Zone1a` `Z_cc_TG`
  → the converter's `LvTr`, base `SnZone1`. Voltage base = the transformer's own nominal, so
  only the power base changes. (The per-generator `gen_xfmr` needed in `M` has no Excel source
  yet — §7.4.)
- **`Zone3` transformer taps**: `RatioTfoMinPu = r_min`, `RatioTfoMaxPu = r_max`,
  `RatioTfo0Pu = 1`, `NbTap = N_prises + 1`, `Tap0 = (NbTap − 1)/2`.
- **Internal transformer** (`LvTr`): `…_RLvTrPu/…_XLvTrPu` from `Zone1a`
  `Z_cc_TG` (base `SnZone1`), `…_ConverterLVControl` from `Zone1a` — filled from the Excel,
  not defaults.
- **Collector line** (`+i`, later): `R_rc/X_rc/B_rc/G_rc` (Ω,1/Ω) → pu with `Zbase = Un1²/100`.
- **Aux load** (`+Aux`, later): `LoadAlphaBeta` from `P_A/Q_A/alpha/beta`; `AuxLoad_Xfmr`
  from `Z_cc_TA/r_TA/Sn_A`.
- **Converter `SNom`** = `SnZone1` (Zone1) / `SnZone3` (Zone3).
- **Producer.ini** — Zone 3: `p_max_injection_at_PDR = Pmax_PDR`, `u_nom_at_PDR = Un_PDR`,
  `q_max_at_PDR = Qmax_PDR`, `q_min_at_PDR = Qmin_PDR`, `topology = Topologie`,
  `P/Q_sharing = P_share/Q_share`. Zone 1 uses its Zone-1 counterparts: `p_max` from
  `Pmax_injection_z1`, `q_max/q_min` from `Qmax_z1/Qmin_z1`, and **`u_nom_at_PDR = Un1`** (node
  1, per `Signaux zone 1`), **not** `Un_PDR`.

---

### 10. Testing strategy

- Reuse the stdlib xlsx reader and its tests.
- **Catalog/map tests**: rebuild the submodel→model map from the ddb and assert it is
  injective, has no unresolved `extends`, and that every Zone3 plant model has its 1:1
  Zone1 turbine sibling (the `tools/` generator, §7.2–7.3).
- **Golden tests**: for a filled WECC example, assert the generated `ini/dyd/par` match the
  `examples/Model/**` reference files (structure-level). The filled workbook is an
  **AIA-authored test fixture with invented (representative) contents** — columns, parameter
  names *and* values — used only to exercise the tool (cf. `tools/dynawo_par` `WECCSample.xlsx`).
  This is a testing artifact and is independent of the production responsibility split
  (AIA=columns / RTE=names / end user=values).
- **Submodel-report tests**: a selection with blocks on `Aucun` reports them as missing and
  resolves (or fails to resolve) the model as expected.
- **Electrical-unit tests**: transformer/base conversions against known values.
- Tests live under `tests/tools/` so they run in the standard `pytest` suite.

---

### 11. Open points to confirm with RTE

> Consolidated as a sendable list in
> [`DyCoV_input_generation_RTE_questions.md`](DyCoV_input_generation_RTE_questions.md).

- **Complete the template's variant vocabulary** so every model is reachable. Structural
  comparison against the ddb (all seven submodel blocks present; nothing extra) shows
  **exactly three variant columns missing — `REGC_B`, `REEC_B`, `WTGP_B`**. Every other block
  is complete: REPC (single), WTGT (A+B present), WTGA, WTGQ. The Excel label **is** the
  Modelica letter by design (`A`=`a`, `B`=`b`, `C`=`c`), so these are the exact variants.
  Split: **AIA** adds the columns; **RTE** adds the parameter names (rows); the **end user**
  fills the values. (Done: `REGC_B`, `REEC_B`, `WTGP_B` columns are present in the working
  version; parameter rows pending RTE.)
- **Review the observed submodel→model map** (§7.2) for completeness across all WECC models
  RTE intends to support.
- **Transformer levels** (§7.4): DyCoV's model (`init_calcs`) uses per-generator `gen_xfmr` +
  a grouping `ppm_xfmr`, plus the internal `LvTr`. `Zone1a` = internal `LvTr` (confirmed by
  `ConverterLVControl` being a `Zone1a` field), `Zone3` = the plant `ppm_xfmr`. Confirm with
  RTE. Follow-up: for **`M`**, the per-generator
  **`gen_xfmr`** has no Excel table → add a per-generator transformer table. (`gen_xfmr` and
  `ppm_xfmr` are both general transformers — real impedance/OLTC allowed on either.)
