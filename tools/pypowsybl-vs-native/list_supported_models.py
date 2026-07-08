#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""
Show the powsybl-dynawo dynamic-model catalog and how it is EXTENDED with
`additionalModelsFile`.

Two layers decide what PyPowsybl can run:
  * the built-in base catalog  -> `ModelMapping.get_supported_models()`
  * runtime additions          -> the `additionalModelsFile` provider parameter,
                                  which registers extra libs into EXISTING categories.

Important: `get_supported_models()` returns only the BASE catalog; additional models
do NOT appear there — they are resolved at simulation time (see
`run_native_vs_pypowsybl.py`, which shows the registered model reaching
"instantiation OK"). New CATEGORIES cannot be created this way (only new models inside
existing categories); e.g. `add_dynamic_model('IEC', ...)` -> "No category named IEC".

Only requires `pypowsybl` (no Dynawo / itools config needed).

    python list_supported_models.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pypowsybl as pp
import pypowsybl.dynamic as dyn

HERE = Path(__file__).resolve().parent
ADDITIONAL = HERE / "additional_models.json"


def main() -> None:
    mm = dyn.ModelMapping()
    base = sorted(mm.get_supported_models())
    categories = sorted(mm.get_categories_names())

    print(f"pypowsybl {pp.__version__}")
    print(f"BASE catalog: {len(base)} models across {len(categories)} categories")
    print(f"categories: {', '.join(categories)}")
    print(f"  'IEC' present as a category? {'IEC' in categories}  "
          f"(new categories cannot be added at runtime)")

    base_wecc = [m for m in base if "Wecc" in m]
    print(f"\n== BASE 'WECC' family ({len(base_wecc)}) ==")
    for m in base_wecc:
        print(f"    {m}")

    # ---- extend with additionalModelsFile -----------------------------------
    spec = json.loads(ADDITIONAL.read_text())
    added = {cat: [e["lib"] for e in body["libs"]] for cat, body in spec.items()}
    print(f"\n== ADD via additionalModelsFile ({ADDITIONAL.name}) ==")
    print("  (models.json category keys are a fixed set; a NEW key such as 'IEC'"
          " is rejected with 'No category named IEC')")
    for cat, libs in added.items():
        print(f"  category '{cat}':")
        for lib in libs:
            print(f"    + {lib}")

    print("\n== EFFECTIVE 'WECC' family (base + additional) ==")
    effective = sorted(set(base_wecc) | set(added.get("WECC", [])))
    for m in effective:
        tag = "" if m in base_wecc else "   <- added at runtime"
        print(f"    {m}{tag}")

    print("\nNote: get_supported_models() lists only the base catalog; the '+ added'"
          "\nmodels register at simulation time. Run run_native_vs_pypowsybl.py to see"
          "\na registered non-catalog model reach 'instantiation OK'.")


if __name__ == "__main__":
    main()
