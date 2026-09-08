#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Excel -> DyCoV input generator: orchestration.

    read workbook -> resolve model (Model Map) -> parse Zone1/Zone3 + control params
    -> DYD (producer_dyd) -> PAR (par.*) -> INI (producer_ini) -> reference curves

Each output has its own module: this one only decides what to build and reports the outcome.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent.parent / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import par  # noqa: E402
import parse as P  # noqa: E402
import producer_dyd as dyd  # noqa: E402
import producer_ini as ini  # noqa: E402
import reference_curves as rc  # noqa: E402
import signals as sig  # noqa: E402
import workbook as wb  # noqa: E402  (the stdlib xlsx reader)

from dycov.files.producer_dyd_file import (  # noqa: E402
    BESS_ID,
    GROUP_XFMR_ID,
    MAIN_XFMR_ID,
    PPM_ID,
)
from dycov.files.producer_par_file import write_producer_par_file  # noqa: E402

# Base name of the Dynawo input files and of the reference-curve directory: DyCoV derives both
# from the same producer name, so a rename travels through this one constant.
PRODUCER_NAME = "Producer"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _submodel_report(resolved: dict, selections: list, control_params: list) -> str:
    """Report the blocks declared in ``Général`` and whether their parameter sheet contributed
    a selected variant with values (``present``) or not (``missing``)."""
    present = {p["block"] for p in control_params}
    lines = [
        "Submodel report",
        f"  Zone3 (plant)   : {resolved['zone3_lib']}  (prefix {resolved['zone3_prefix']})",
        f"  Zone1 (turbine) : {resolved['zone1_lib']}  (prefix {resolved['zone1_prefix']})",
        "  Control submodels:",
    ]
    for block, _choice in selections:
        lines.append(f"    {block:5} : {'present' if block in present else 'missing'}")
    return "\n".join(lines)


def _reference_curves_report(curves: dict) -> str:
    """Report what the signal sheets produced, and which .csv files are still to be provided."""
    if not curves["tests"]:
        return ("Reference curves\n  the signal sheets describe no test: nothing written under "
                "ReferenceCurves/")
    lines = [
        "Reference curves",
        "  %s" % curves["target"],
        "  tests described : %d" % curves["tests"],
        "  .csv copied     : %d" % curves["copied"],
    ]
    if curves["missing"]:
        lines.append("  .csv missing    : %d (copy them next to the .dict files: %s)"
                     % (len(curves["missing"]), ", ".join(curves["missing"][:4])))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PAR sets per zone
# ---------------------------------------------------------------------------


def _zone1_par_sets(
    root: Path, zone1: dict, control: list, resolved: dict, gen_id: str, lv_control: bool
) -> list:
    """The unit and, unless its own transformer reaches the internal node, the group one."""
    s_nom = P.zone_number(zone1, "SnZone1")
    sets = [par.converter_par_set(gen_id, resolved["zone1_prefix"], control, zone1, s_nom)]
    if lv_control:
        sets.append(par.group_transformer_par_set(GROUP_XFMR_ID, zone1, s_nom))
    else:
        dyd.drop_group_transformer(
            root / "Zone1" / f"{PRODUCER_NAME}.dyd", gen_id,
            f"{resolved['zone1_prefix']}terminal",
        )
    return sets


def _zone3_par_sets(
    zone1: dict, zone3: dict, control: list, resolved: dict, gen_id: str, topology: str
) -> list:
    """The plant, its main transformer, and the equipment the topology adds."""
    sets = [
        par.converter_par_set(
            gen_id, resolved["zone3_prefix"], control, zone1,
            P.zone_number(zone3, "SnZone3"),
            plant_model=True,
        ),
        par.main_transformer_par_set(MAIN_XFMR_ID, zone3),
    ]
    if "aux" in topology.casefold():
        sets += [par.aux_transformer_par_set("AuxLoad_Xfmr", zone3),
                 par.aux_load_par_set("Aux_Load", zone3)]
    if topology.casefold().endswith("i"):
        sets.append(par.collector_line_par_set("IntNetwork_Line", zone3))
    return sets


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def generate(excel: Path, outdir: Path) -> str:
    """Generate the ``Dynawo/Zone1`` + ``Dynawo/Zone3`` Producer input trees from *excel*."""
    workbook = wb.read_workbook(excel)
    resolved = P.resolve_models(workbook)
    template = P.template_for(resolved["zone3_lib"])
    builder_gen_id = BESS_ID if template == "model_BESS" else PPM_ID
    gen_id = dyd.GEN_ID_BY_TECH[P.technology(resolved["zone3_lib"])]
    rename = {builder_gen_id: gen_id} if gen_id != builder_gen_id else {}

    zone3 = P.parse_zone(workbook, "Zone3")
    zone1 = P.parse_zone(workbook, "Zone1a")
    lv_control = P.is_true(zone1.get("ConverterLVControl", "True"))
    control = par.control_params(workbook, lv_control)
    topology = dyd.checked_topology(zone3)

    config = wb.parse_config(workbook)
    z1_control = par.control_params_for_zone(control, config.zones, "Zone1")
    z3_control = par.control_params_for_zone(control, config.zones, "Zone3")
    if not z1_control:
        raise ValueError(par.empty_zone1_reason(config))

    root = outdir / "Dynawo"
    for zone in ("Zone1", "Zone3"):
        (root / zone).mkdir(parents=True, exist_ok=True)

    dyd.write_dyd(root, PRODUCER_NAME, topology, template, resolved, gen_id, rename)

    write_producer_par_file(
        root / "Zone1", f"{PRODUCER_NAME}.par",
        _zone1_par_sets(root, zone1, z1_control, resolved, gen_id, lv_control),
    )
    write_producer_par_file(
        root / "Zone3", f"{PRODUCER_NAME}.par",
        _zone3_par_sets(zone1, zone3, z3_control, resolved, gen_id, topology),
    )

    ini.write_ini(
        root, PRODUCER_NAME, topology, zone1, zone3, gen_id,
        include_consumption=template == "model_BESS",
    )

    curves = rc.write_reference_curves(outdir, PRODUCER_NAME, sig.parse_signals(workbook))

    return "\n".join([_submodel_report(resolved, config.selections, control),
                      "", _reference_curves_report(curves)])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate DyCoV Producer inputs from a WECC Excel.")
    ap.add_argument("--excel", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args(argv)
    if not args.excel.is_file():
        ap.error(f"Excel not found: {args.excel}")
    try:
        report = generate(args.excel, args.outdir)
    except zipfile.BadZipFile:
        print(
            f"ERROR: {args.excel} is not a readable .xlsx workbook (a legacy .xls file has to be "
            f"saved as .xlsx first).",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(report)
    print(f"\nWrote input tree under: {args.outdir / 'Dynawo'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
