## Excel → DyCoV Input Generation (WECC) — Points for RTE

Open points from designing the WECC Excel → DyCoV input generator. Full context and
section refs are in
[`DyCoV_input_generation_from_excel_design.md`](DyCoV_input_generation_from_excel_design.md).
Verified against the Dynawo install `/opt/Dynawo_v1.8.0_20260714/dynawo/ddb`.

Two blocks: **§1** an action on AIA's side, **§2** questions/decisions for RTE.

---

### 1. Action on AIA's side (shared SharePoint Excel)

**A1 — Add the missing variant columns.** (design §7.2)
The Excel is missing exactly **three variant columns — `REGC_B`, `REEC_B`, `WTGP_B`**; without
them some valid models cannot be represented (PV `VoltageSource1/2` need `REGC_B`; PV-current
and `VoltageSource2/4` need `REEC_B`; wind `WT3/WTG3` type-2 needs `WTGP_B`). All submodel
blocks are present and nothing is extra. The Excel label **is** the Modelica letter
(`A`=`a`, `B`=`b`, `C`=`c`), so these are exactly the `_B` variants.

Responsibility split: **AIA adds the columns**; **RTE adds the parameter names (rows)** in
each new column; the **end user fills the values** when they complete the template.
**Done (AIA):** `REGC_B`, `REEC_B`, `WTGP_B` columns are present in the working version
(change tracking on); their parameter rows are empty, pending RTE.

---

### 2. Questions / decisions for RTE

**Reference (attach the topology diagrams).** DyCoV's electrical model
(`src/dycov/electrical/initialization_calcs.py`, `init_calcs`): per generator, a `gen`
(WECC model, carrying the internal `LvTr`) behind an explicit **`gen_xfmr`** (one per
generator), joined at an internal bus, then an optional **`ppm_xfmr`** grouping all → PDR.
This matches RTE's diagrams: `gen → StepUp_Xfmr(=gen_xfmr) → Int_Bus → [PPM_Xfmr(=ppm_xfmr)] →
[IntNetwork_Line] → PDR`; `PPM_Xfmr` appears only in `M`.

**Q1 — Deduce the model from the variants, or state it explicitly in the Excel?** (§7.2)
Two viable options; RTE decides:
- **(a) Deduce from a Dynawo install** — the model follows from the per-block variants.
  Verified: the tuple `(REPC, REGC, REEC, WTGT, WTGP, WTGA, WTGQ)` maps **injectively** to the
  exact model (**no two models are identical**), and the technology is derived too, so no extra
  field is needed. The model's **`lib` name and prefix** are then read from the install's
  compiled descriptors (`<lib>.desc.xml`/`.extvar`). Requires a version-matched install at
  generation time. (Parameter values/types still come from the Excel; the prefix is prepended to
  the names — see §7.1 of the design.)
- **(b) Define it in the Excel — self-computing.** No manual field: a cell **auto-derives the
  `lib` from the variant selection** (an Excel lookup/formula encoding the injective
  variant→model map), and a cell **derives the `prefix` from that `lib`**. The tool then just
  reads those cells — **install-independent** (no ddb needed at generation time). It is **per
  zone** — the two `lib`/`prefix` pairs (Zone3 plant + Zone1 turbine, e.g.
  `WTG3WeccCurrentSource2`/`WTG3_` vs `WeccWT3CurrentSource2`/`WT3_`) come from the one variant
  selection. Cost: the mapping table lives in the template and must be **kept in sync with the
  simulation Dynawo version** (a rename/prefix change would stale it). AIA can generate the
  table once from the ddb; RTE reviews.

  > **A working example already exists (for visual reference).** We have a version of the
  > workbook with this implemented — a `Model Map` sheet (the 10-row variant→`lib`+`prefix`
  > table, both zones) and four self-computing cells in `Général` (Zone3 `lib`/`prefix`, Zone1
  > `lib`/`prefix`) that update from the variant dropdowns. It shows concretely how path (b)
  > would look, for RTE to judge the two options side by side.

Underlying question either way: **do we resolve against a Dynawo installation (always
version-matched, path a), or bake the mapping into the Excel (install-independent but
template-maintained, path b — prototype available)?** The choice governs the `lib` name and the
mandatory prefix.

**Q2 — Confirm that the `Zone1a` transformer is the model's internal `LvTr`.** (§7.4)
AIA concludes — `Zone1a` is the model's **internal `LvTr`**, not the `gen_xfmr`. Basis:
(i) the `Zone1a` diagram; (ii) `Zone1a` carries **`ConverterLVControl`** — the WECC parameter
that governs the `LvTr` — with a fixed ratio `r_TG` (no OLTC). → **Please confirm.**

**Q3 — For `M`, the per-generator `gen_xfmr` is missing — how to add it?** (§7.4)
DyCoV requires, per generator, an explicit `gen_xfmr` (the `init_calcs` `gen_xfmrs` tuple).
With `Zone1a` = the internal `LvTr` (Q2) and `Zone3` = `ppm_xfmr` (the plant/principal), the
**per-generator `gen_xfmr` has no Excel table**. In `S` (one generator, no separate plant
transformer) the single `Zone3` transformer covers it; but in `M` the N per-generator
`gen_xfmr` are missing. → **How should the per-generator `gen_xfmr` be added** (a transformer
table per `Zone1x`?). (`M` is out of first-iteration scope.)

**Q4 — Confirm three working assumptions.**
- **No parameter validation** — the tool does not check parameter values/completeness (RTE
  ships a complete template). Empty control cells are **omitted** from the PAR (Dynawo applies
  its default); the tool only reports which **submodels** are present/missing.
- **`Signaux zone 1/3` are not used to generate** — the PCS/tests and the compared curves are
  defined internally by DyCoV. (They may still inform conventions — e.g. the `Un1` point below.)
- **Zone 1 `u_nom_at_PDR` = `Un1`**: `Signaux zone 1` references every Zone-1 condition to node
  1 (`Unode1 = Un1`) and its signals to base `Un1`/`Un2`. (Zone 3 uses `Un_PDR`.)
