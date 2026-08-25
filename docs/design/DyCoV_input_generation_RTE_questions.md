## Excel → DyCoV Input Generation (WECC) — Points for RTE

Points from designing the WECC Excel → DyCoV input generator. Design detail:
[`DyCoV_input_generation_from_excel_design.md`](DyCoV_input_generation_from_excel_design.md).

### Decided (RTE, 2026-07-27)

- **Model resolution → in the Excel.** A `Model Map` sheet maps the variant selection to the Dynawo
  `lib` + prefix per zone, so the tool needs no Dynawo install at generation time. The variant tuple
  is injective (one model per tuple; technology derived).
- **Transformers.** `Zone1a` defines the converter's internal `LvTr` (`Z_cc_LvTr`) and the external
  `StepUp_Xfmr` (`Z_cc_TG`, fixed ratio); `Zone3`'s transformer groups all generators (`M` only).
  `ConverterLVControl` sets the converter's nominal voltage in the INI (`Un2` if `True`, else `Un1`).
- **No parameter validation** by the tool (RTE ships a complete template); empty cells are omitted
  (Dynawo defaults). `Signaux zone 1/3` are informative only.

### Still needed from RTE

- **Parameter names** for the three added variant columns `REGC_B`, `REEC_B`, `WTGP_B` (AIA added
  the empty columns; RTE adds the parameter rows; the end user fills the values).
- **Review** the variant→model map for completeness across the WECC models RTE supports.
- **`M`: how each `Zone1<x>`'s model is selected.** The single `Général` selection resolves one
  model, and duplicating a `Zone1<x>` copies only electrical data — so the Excel cannot yet say which
  model each generator is (they may differ, e.g. `WECC4` mixes `WTG4A`+`WTG4B`). This **blocks `M`**.
- **Possible new scope:** electrical validations of the user-entered values (RTE is open to it).

### Template fixes (found 2026-08-25, filling the template with a WECC4B case and checking the Dynawo descriptors)

- **REGC parameter names:** the rows `Iqrmax`, `Iqrmin`, `Rrpwr` don't match the Dynawo names
  `IqrMaxPu`, `IqrMinPu`, `RrpwrPu`. Names are written verbatim to the PAR, so these rows would
  never bind (Dynawo ignores them).
- **REGC_A missing rows:** `KpPLL`, `KiPLL`, `OmegaMaxPu`, `OmegaMinPu` exist only in the `REGC_C`
  column, but the `REGC_A`-based models define them too.
- **`PPCLocal` has no row.** It is a parameter of the plant-side model only (e.g. `WTG4B` has it,
  the `WT4B` turbine doesn't). To decide: a template row (in `REPC`, `Zone3`-only) or a value the
  tool derives, like `ConverterLVControl`.
