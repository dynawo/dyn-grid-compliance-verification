## DyCoV Input Generation from Excel (WECC first) — Design

### 1. Purpose

A tool that reads an RTE Excel model specification (model selection, network topology, electrical
data, control parameters, reference-curve description) and generates a complete DyCoV `Model` input
set:

```
<output>/Dynawo/Zone1/Producer.{ini,dyd,par}
<output>/Dynawo/Zone3/Producer.{ini,dyd,par}
<output>/ReferenceCurves/Producer/CurvesFiles.ini + one .dict per test + the .csv files
```

The generation **core is standard-agnostic**: the family (WECC / IEC) is confined to a thin
front-end that parses the family's Excel and resolves the selected variants to a concrete Dynawo
model class; everything downstream depends only on the resolved model, the Excel values and the
topology. WECC is the first — and today only — front-end.

The tool does **not** validate Excel parameter values or completeness — RTE ships a complete
template. Its only checking role is at the **submodel** level (§9).

---

### 2. Scope

**Topology codes.** `Zone3`'s `Topologie` is `{S | M}`, optionally followed by `+Aux` and/or `+i`.
`S` = one `Zone1` sheet (single generator); `M` = one `Zone1<x>` sheet per generator. `+Aux` =
auxiliary load + its transformer; `+i` = the plant's collector network, aggregated as a PI line.

**In scope:** the single-`Zone1` topologies (`S`, `S+Aux`, `S+i`, `S+Aux+i`), both zones' input
files, and the reference-curve tree (§8). A topology outside that list — the `M` family included —
is refused by name rather than truncated to one generator.

**Out of scope:** parameter-value validation, and the initialization / power-flow parameters
(`P0Pu`, `Q0Pu`, `U0Pu`, `UPhase0`, `*Pcc0Pu`, …), which are not in the Excel and which DyCoV
injects at simulation setup.

---

### 3. Input

**CLI**
```bash
python generate_inputs.py --excel model.xlsx --outdir <path>
```
`--excel` is the WECC workbook (single source of truth); `--outdir` is where the trees are written.
`.xlsx` is parsed with the tool's own standard-library engine (`workbook.py`), which the legacy
`tools/dynawo_par` also imports until its retirement.

**Sheets used**

| Sheet | Role |
| :--- | :--- |
| `Général` | Block selection (`Type de bloc \| Choix \| Zone`: block → variant or `Aucun`, plus the `;`-separated zones the block's parameters go to) and the Excel-computed `Model Map` lookup key (derived table; the tool reads the cached key cell verbatim). |
| `Model Map` | Variant tuple → Dynawo `lib` + prefix, per zone (§6). |
| `Zone1<x>` (`Zone1a`, …) | One sheet per generator. Zone-1 data: `SnZone1`, `N_Zone1`, `ConverterLVControl`, `Un1`, `Un2`, the group transformer (`Z_cc_TG`, `R_cc_TG / X_cc_TG`, `r_TG`), `Pmax_injection_z1`, `Pmax_soutirage_z1`, `Qmax_z1`, `Qmin_z1`, `P_share`, `Q_share`. |
| `Zone3` | Exactly one. `Topologie`, `SnZone3` (computed as `N_Zone1 · SnZone1`), `Un_PDR`, `Pmax_injection_PDR`, `Pmax_soutirage_PDR`, `Qmax_PDR`, `Qmin_PDR`, main transformer (`Z_cc_TP`, `R/X`, `N_prises`, `r_max`, `r_min`, and the starting tap `Tap_0` or `r_0`), aux load (`+Aux`), collector (`+i`). |
| `Signaux zone 1` / `Signaux zone 3` | Per zone: the quantities to provide with the `.csv` column holding each, the DTR cases to run with the `.csv` file of each, and the folder those files live in (§8). |
| Control sheets (`REPC`, `REEC`, `REGC`, `Mechanical Part`, …) | Control-block parameters, one column group per variant. Any sheet with a parameter table is one; how many there are, and their names, are the workbook's business. |
| Descriptive sheets | Ignored: without a parameter table they yield nothing. |

**Names live in a configuration file.** Every sheet, row, header and marker the tool looks for is an
entry of `excel_names.ini`, so a renamed sheet or row is a change there and not in the code:

| Section | Holds |
| :--- | :--- |
| `[Sheets]` | The fixed sheet names, and the `Zone1` prefix for the day a plant describes several. |
| `[Anchors]` | The header texts tables are located by, as comma-separated alternatives. |
| `[Markers]` | The `/` sentinel, the `Choix` values meaning "no block", the empty annotations, and the `Un1 ou Un2` base. |
| `[Zone1-Rows]`, `[Zone3-Rows]` | Row name of every electrical concept (`main_impedance = Z_cc_TP`). |
| `[Zone1-Curves]`, `[Zone3-Curves]` | Row label → DyCoV curve, `{gen}` standing for the generator block. |
| `[Zone1-Tests]`, `[Zone3-Tests]` | DTR case → `PCS.Benchmark.OperatingCondition` (§8). |

Names are matched without accents and case-insensitively, and headers by substring, so
`Paramètres (Dynawo)` still reads as `Paramètres`.

**Layout.** Nothing is addressed by a fixed column. In a control sheet, the header row is the first
one naming parameters, values and types — requiring all three keeps the zone sheets' `Paramètres |
Descriptions | Valeurs` tables out — and each variant's value and type columns are the nearest such
headers to the right of its `Paramètres` column, inside its table block. That resolves both layouts
in use: `Paramètres | Types | Valeurs` per variant, and `Paramètres | Valeurs` repeated with a
single `Types` column shared by the variants of the block. The two zone sheets differ as well
(`Zone1a` has name/value in cols A/C, `Zone3` in B/D behind a category column), so the parser
locates the header row and the value column per sheet.

Semantics: `Un1` = HTA/primary (node-1 nominal), `Un2` = BT/secondary (converter side);
`ConverterLVControl` is text `"True"`/`"False"`; `R_cc_* / X_cc_*` rows are the **R/X ratio** `k`
(§7), not impedances.

**A row that is read has a value.** A required row that is absent, empty, marked `/` or not a
number is refused naming the sheet, the row and what was found, instead of failing further
downstream: an unfilled workbook must say so, not produce half a model.

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

Three files per zone, plus the reference-curve tree (§8). The resolved model class (§6) drives the
`lib` ids and the parameter-name prefix; parameter type and value come from the Excel:

- **Producer.ini** — DTR envelope + topology: `p_max_injection_at_PDR`, `u_nom_at_PDR`,
  `q_max_at_PDR`, `q_min_at_PDR`, `topology`, `P_sharing_*`, `Q_sharing_*`, and
  `p_max_consumption_at_PDR` for storage, which DyCoV requires in both zones. Each zone declares
  the node it connects at, so `u_nom_at_PDR` is `Un1` in Zone1 and `Un_PDR` in Zone3, and Zone1's
  `topology` is always `S`: one unit connected to its internal node, whatever the plant's.
- **Producer.dyd** — a `blackBoxModel` for the converter (resolved `lib`), the topology network
  blocks and the `connect` lines. The converter terminal is `<prefix>terminal`. Zone3 uses the
  **plant** lib, Zone1 its **turbine** sibling (§6).
- **Producer.par** — one `set` per id: the converter parameters from the Excel (name = prefix +
  Excel bare name) + network element parameters (computed, §7). Each zone's PAR carries the blocks
  that declare that zone in `Général`'s `Zone` column, in the **workbook's own order** (sheet →
  table → parameter) — the Excel alone determines the PAR order, so diffs stay stable; a selection
  where no block declares `Zone1` is refused (never a silently incomplete `Zone1`). Empty Excel
  cells are omitted (Dynawo defaults).

A variant's first parameter opens its section with a comment naming the variant, and a parameter
carrying a base unit or a comment in the workbook gets one too, with the `Un1 ou Un2` base resolved
to the side in force. The template's placeholder annotations (`-`, `/`) are dropped rather than
copied. A `DOUBLE` is re-rendered as the shortest text that round-trips to the same number, so the
17 digits Excel stores for `1e-5` do not reach the PAR. Files are laid out (blank-line groups) like
the `examples/Model/**` references so they read and diff cleanly.

The base name of every file, and the `ReferenceCurves` subdirectory, come from one constant
(`PRODUCER_NAME`), since DyCoV derives both from the same producer name.

---

### 5. Organization

One module per generated file, and the readers behind them:

```
generate_inputs.py        CLI: what to build, in what order, and the run report
  excel_names.py / .ini   every sheet, row, header and marker name the workbook uses
  workbook.py             stdlib .xlsx reader: sheets as grids, variant tables
  parse.py                model resolution (Model Map), the electrical sheets, control params
  signals.py              the signal sheets: curves, tests and their .csv files
  electrical.py           pure conversions: impedances, tap positions, per-unit bases
  producer_dyd.py         DYD: topology, libs, terminals, the group transformer's absence
  producer_ini.py         INI: each zone's limits, nominal voltage and power sharing
  par/                    PAR, one module per kind of equipment
    converter.py            the generating unit's model
    transformers.py         group, main and auxiliary
    loads.py                auxiliary load
    lines.py                collector
    control.py              the control sheets turned into parameters, split per zone
  reference_curves/       the reference-curve tree
    curves_files.py         CurvesFiles.ini
    dicts.py                one .dict per test
```

- **The front-end is the only standard-specific layer** — the Excel schema (`excel_names.ini` +
  `parse.py` + `signals.py`) and the variant→model resolver. The emitters never branch on WECC vs
  IEC, and never spell a workbook name: they read rows by concept
  (`P.numbers("Zone3", zone3)("main_impedance")`).
- The DYD, INI and PAR structure comes from DyCoV's own builders (`dycov.files.producer_*`), so the
  topology catalog has a single home; the tool supplies the concrete libs, prefixed names and
  computed values.
- Every PAR builder is pure — rows in, `(set id, parameters)` out — which is what makes them
  testable without a workbook.

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

The map's rows are the combinations Dynawo has a model for, and the template lets the user select
others — `REGC_B|REEC_C`, say, a BESS behind a voltage source. Choosing a valid combination is the
user's job: a key the map does not hold is refused, naming the key and listing the known ones.

**Parameter names carry the model prefix.** The Excel holds bare names (`Kqp`); each WECC model is a
compiled composite whose descriptor flattens every parameter to `<prefix>_<Param>`
(`photovoltaics_Kqp`) and the AC port to `<prefix>_terminal`. Dynawo binds by the exact flattened
name, so the tool **prepends the resolved prefix** to every converter parameter — in both the PAR
(`photovoltaics_Kqp`) and the DYD (`photovoltaics_terminal`). Beyond the name, the Excel supplies
only the type, mapped to the Dynawo convention (`double → DOUBLE`), and the value.

**Resolution is unambiguous (injective).** The variant selection determines one model, so no
separate model field is needed and technology (PV/BESS/Wind) is derived from the resolved `lib`,
which also fixes the generator block's id (`PV_Array`, `Wind_Turbine`, `Bess`) and hence the names
of its curves. The Zone3 (plant) side of the map, which lives in the Excel and not in the tool:

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

**Two model parameters come from outside the control sheets.** `ConverterLVControl` is read from
the zone sheet, where it also decides the network (§7); `PPCLocal` has no row anywhere: it is
always `false`, and emitted only among the `Zone3` parameters, since it exists in the plant `lib`s
and in none of the turbine ones.

---

### 7. Transformers and electrical computations

Dynawo **network elements** (transformers, lines) take per-unit values on `SnRef = 100 MVA`, so a
`Z_cc` (pu on `SnZone`) with `k = R_cc/X_cc` becomes:
```
X_cc = Z_cc / sqrt(1 + k²);  R_cc = k · X_cc;   XPu = X_cc · 100 / SnZone;   RPu = R_cc · 100 / SnZone
```
The **WECC model's own** impedances are instead per-unit on its `SNom`, so `Z_cc_TG` (pu on
`SnZone1`) is split into `R_cc`/`X_cc` and written unrebased. The same number serves both zones:
Zone1's `SNom` is `SnZone1` already, and in Zone3 aggregating the `N` generator transformers in
parallel onto `SnZone3 = N · SnZone1` cancels out.

**The group transformer is one transformer described once**, and where it acts depends on the zone
and on `ConverterLVControl`, which the models enforce (`Controls/WECC/Parameters/ParamsLvTfo.mo`
and `ParamsPCS.mo`):

- **Zone1.** `True` zeroes the model's own branch, so an external `Group_Xfmr`
  (`TransformerFixedRatio` from `Z_cc_TG` + `r_TG`) carries it; `False` puts `Z_cc_TG` inside the
  model, and the block is dropped with the generator wired to its downstream node — modelling both
  would put two transformers in series.
- **Zone3.** The unit's transformer lives inside the plant model, whatever the flag: with
  `PPCLocal = false` the plant applies `RLvTrPu` on one side of its internal network or the other,
  never twice and never nowhere. So `Zone3`'s only external transformer is the main one.

`ConverterLVControl` also states the side the converter control measures on, hence the converter's
own nominal voltage (`Un2` when `True`, `Un1` when `False`), which the values the user types are
per-unit of.

The **main HTB/HTA transformer** (`Main_Xfmr`) is always present in `Zone3`, as a
`TransformerRatioTapChanger` from `Z_cc_TP` on base `SnZone3` with `NbTap = N_prises + 1` and
`RatioTfoMin/Max = r_min/r_max`. Its **starting tap** comes from `Tap_0`, or from `r_0` when only
the ratio is given, and defaults to the middle tap. Dynawo derives the starting ratio from the tap,
so when both rows are filled in they must agree, and a ratio that falls between two taps is
refused. A quasi-ideal transformer is expressed as any other: `r_min = r_max = 1` and a negligible
`Z_cc_TP`.

The remaining blocks:

- **collector line** (`+i`) — `IntNetwork_Line`, the plant's collector aggregated as a PI model,
  from `R_rc`/`X_rc` in ohms and `B_rc`/`G_rc` in siemens with `Zbase = Un_PDR²/100`. Those rows
  carry no voltage of their own, and the block connects to the PDR with no transformer in between,
  so that is its base whatever level the ohms were measured at.
- **auxiliary load** (`+Aux`) — `Aux_Load`, a `LoadAlphaBeta` from `P_A`/`Q_A` (MW/MVAr on
  `SnRef`) and `alpha`/`beta`, behind `AuxLoad_Xfmr` from `Z_cc_TA` + `r_TA` on base `Sn_A`.

The converter's `SNom` is the zone's own: `SnZone1` in Zone1, `SnZone3` in Zone3.

---

### 8. Reference curves

The signal sheets describe the curves the user provides, and the tool turns that into the tree
DyCoV reads. The sheets carry only what the user knows — the `.csv` column of each quantity, the
`.csv` file of each DTR case, and the folder holding them; what each row *means* to DyCoV is in
`excel_names.ini`, keyed by the row's own label and by the case number (`Cas`) or DTR sheet plus its
position among the rows of that same sheet (`I2/1`, `I2/2`, …), since a sheet covers several
operating conditions.

- **`CurvesFiles.ini`** — the `.csv` of every described test, and one curve dictionary per zone.
- **One `.dict` per test** — its zone's dictionary, plus the `[Curves-Metadata]` keys.
- **The `.csv` files** — copied from the folder the sheet names; the ones not found are reported so
  the user can drop them in.

**The metadata is left empty on purpose.** `sim_t_event_start`, `fault_duration`,
`frequency_sampling` and `is_field_measurements` describe the user's own files, not the model: the
tool writes the keys with their meaning and no value. Filling them with the simulation's own event
instant would silently compare curves that are not aligned in time, which reads as a
non-compliant model rather than as an unfilled input (`dycov#481`).

A row with no curve of its own — the setpoint rows, say — is informative: DyCoV reads no such curve.
Likewise, a DTR case the sheets do not list gets no reference file; today the frequency ramp is in
that position, listed by neither signal sheet.

The signal sheets are optional as a whole: an untouched one describes no test, and the model inputs
are generated all the same.

---

### 9. Run report (no parameter validation)

The tool does not police parameter values. Per run it reports, at the submodel level: the resolved
model per zone and, for every block listed in `Général` (no fixed family list), whether its
parameter sheet contributed a selected variant with values (present/missing). The reference-curve
side reports how many tests the sheets described, how many `.csv` were copied, and which are still
missing.

---

### 10. Testing

Tests live under `tests/tools/`, one module per module of the tool (`_par`, `_dyd`, `_ini`,
`_reference_curves`, `_parse`, `_workbook`, `_electrical`), plus `_golden` and the synthetic
workbook they share (`workbooks.py`, exposed through `conftest.py`):

- **Map/pairing**: the variant→model map is injective and every plant model has its 1:1 turbine
  sibling.
- **Golden**: for a committed AIA-authored fixture (`WECCSample_full.xlsx`, invented values), the
  generated `dyd` matches `examples/Model/**` structurally — the `connect` wiring and the block
  libs, with the generator id normalized.
- **Electrical**: transformer/base conversions and tap positions against known values.
- **Parsing / report**: layouts, unknown-combo detection, present/missing blocks, and the refusals
  (absent, empty or non-numeric rows; unsupported topology).
- **Reference curves**: labels and cases mapped through the names file, and the files written.

Replicating a shipped `examples/Model/**` case is the end-to-end check: fill a workbook with the
values the example's files imply, generate, and diff. What the diff cannot close tells whether a
parameter is missing from the template, dead in the example, or simply not expressible.

Template parameter names are audited separately against a Dynawo `ddb`, matching every row of the
control sheets to the `.desc.xml` of both `lib`s of every `Model Map` row (exact → case-insensitive
→ normalized, dropping a trailing `pu`), and classifying what does not match: capitalization-only,
unit-suffix, Excel-only, model-only (a defect only where the descriptor has no `defaultValue`),
`readOnly` offered for editing, type disagreement, or two rows targeting one parameter. Names go
verbatim into the PAR and Dynawo ignores what it does not recognize, so a mis-named row binds
nothing and raises no error.

---

### 11. Pending, roughly

- **IEC front-end.** A second Excel family on the same core. The plant models share the WECC seam
  (`ConverterLVControl` / `PPCLocal` with the same four combinations), so the electrical rules
  carry over; the unit models expose no `R/XLvTrPu`, so in Zone1 the group transformer can only be
  the external block. If the IEC template keeps the shared sheets' names, nothing else is needed;
  if it renames them, the names file becomes one profile per family.
- **`M` topologies.** `Général` holds one block selection, so it resolves one plant/turbine pair,
  while an `M` plant needs a model per generator in both zones — `examples/Model/Wind/WECC4` has
  two different ones. Duplicating a `Zone1<x>` sheet copies electrical data only, so nothing in the
  workbook says which model each generator is. It needs a design before it can be asked of RTE.
- **Packaging.** The tool runs standalone from `tools/`, and the intent is to reach the user as a
  DyCoV subcommand (with an alias so it can also be called on its own), which keeps the topology
  catalog in one place at the price of requiring DyCoV. Becoming a self-contained installable would
  instead mean vendoring DyCoV's producer-file builders, and with them a second copy of that
  catalog.
