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

    read workbook -> resolve multi models -> parse Zone1(s)/Zone3 + control params
    -> DYD (producer_dyd) -> PAR (par.*) -> INI (producer_ini) -> reference curves

Each output has its own module: this one only decides what to build and reports the outcome.
"""

from __future__ import annotations

import configparser
from pathlib import Path

from dycov.excel import names, par
from dycov.excel import parse as P
from dycov.excel import producer_dyd as dyd
from dycov.excel import producer_ini as ini
from dycov.excel import reference_curves as rc
from dycov.excel import signals as sig
from dycov.excel import workbook as wb
from dycov.excel.reference_curves import dicts
from dycov.files.producer_dyd_file import (
    BESS_ID,
    GROUP_XFMR_ID,
    MAIN_XFMR_ID,
    PPM_ID,
)
from dycov.files.producer_par_file import write_producer_par_file

# Base name of the Dynawo input files and of the reference-curve directory: DyCoV derives both
# from the same producer name, so a rename travels through this one constant.
PRODUCER_NAME = "Producer"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _submodel_report(resolved: dict, selections: list, control_params: list) -> str:
    """Report the blocks declared in ``Général`` and whether their parameter sheet
    contributed a selected variant with values (``present``) or not (``missing``)."""
    present = {p["block"] for p in control_params}

    zone3_info = resolved.get("zone3", {})

    lib = zone3_info.get("zone3_lib", "")
    prefix = zone3_info.get("zone3_prefix", "")

    zone3_line = f"  Zone3 (plant)   : {lib}  (prefix {prefix})"

    lines = [
        "Submodel report",
        zone3_line,
        "  Zone1 (turbines):",
    ]

    for sheet, gen_info in resolved.get("zone1", {}).items():
        lines.append(
            f"    {sheet:10} : {gen_info.get('zone1_lib')} (prefix {gen_info.get('zone1_prefix')})"
        )

    lines.append("  Control submodels:")
    for block, _choice in selections:
        lines.append(f"    {block:5} : {'present' if block in present else 'missing'}")

    return "\n".join(lines)


def _reference_curves_report(curves: dict) -> str:
    """Report what the signal sheets produced, and which .csv files are still to be provided."""
    if not curves["tests"]:
        return (
            "Reference curves\n  the signal sheets describe no test: nothing written under "
            "ReferenceCurves/"
        )
    lines = [
        "Reference curves",
        "  %s" % curves["target"],
        "  tests described : %d" % curves["tests"],
        "  .csv copied     : %d" % curves["copied"],
    ]
    if curves["missing"]:
        lines.append(
            "  .csv missing    : %d (copy them next to the .dict files: %s)"
            % (len(curves["missing"]), ", ".join(curves["missing"][:4]))
        )
    if curves["unfilled"]:
        lines.append(
            "  metadata to fill: %d (the workbook leaves some column empty for: %s)"
            % (len(curves["unfilled"]), ", ".join(curves["unfilled"][:4]))
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PAR sets per zone
# ---------------------------------------------------------------------------


def _zone1_par_sets(
    root: Path,
    zone1: dict,
    control: list,
    resolved: dict,
    gen_id: str,
    lv_control: bool,
    xfmr_id: str,
) -> list:
    """The unit and, unless its own transformer reaches the internal node, the group one."""
    s_nom = P.numbers("Zone1", zone1)("s_nom")
    sets = [
        par.converter_par_set(
            gen_id, resolved["zone1_prefix"], control, zone1, s_nom, resolved["zone1_lib"]
        )
    ]
    if lv_control:
        sets.append(par.group_transformer_par_set(xfmr_id, zone1, s_nom))
    else:
        dyd.drop_group_transformer(
            root / "Zone1" / f"{PRODUCER_NAME}.dyd",
            gen_id,
            f"{resolved['zone1_prefix']}terminal",
            xfmr_id,
        )
    return sets


def _zone3_par_sets(
    generators: list[dict], zone3: dict, resolved_zone3: dict, topology: str
) -> list:
    """The plant, its main transformer, and the equipment the topology adds."""
    sets = [par.main_transformer_par_set(MAIN_XFMR_ID, zone3)]

    for gen in generators:
        sets.append(
            par.converter_par_set(
                gen["gen_id"],
                resolved_zone3["zone3_prefix"],
                gen["z3_control"],
                gen["zone1_data"],
                P.numbers("Zone3", zone3)("s_nom"),
                resolved_zone3["zone3_lib"],
                plant_model=True,
            )
        )
        sets.append(
            par.group_transformer_par_set(
                gen["xfmr_id"], gen["zone1_data"], P.numbers("Zone3", zone3)("s_nom")
            )
        )

    if "aux" in topology.casefold():
        sets += [
            par.aux_transformer_par_set("AuxLoad_Xfmr", zone3),
            par.aux_load_par_set("Aux_Load", zone3),
        ]

    if topology.casefold().endswith("i"):
        # Relies on the first generator's Un1 definition as the base for the collector line
        sets.append(
            par.collector_line_par_set("IntNetwork_Line", zone3, generators[0]["zone1_data"])
        )

    return sets


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def tests_without_metadata(outdir: Path, producer: str = PRODUCER_NAME) -> list:
    """The generated tests DyCoV would refuse to run, because their metadata is blank."""
    target = outdir / "ReferenceCurves" / producer
    if not target.is_dir():
        return []
    incomplete = []
    for path in sorted(target.glob("*.dict")):
        parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
        parser.read(path, encoding="utf-8")
        if not parser.has_section("Curves-Metadata"):
            continue
        filled = dict(parser.items("Curves-Metadata"))
        if any(not filled.get(key, "").strip() for key in dicts.METADATA_HELP):
            incomplete.append(path.stem)
    return incomplete


def generate(excel: Path, outdir: Path) -> str:
    """Generate the ``Dynawo/Zone1`` + ``Dynawo/Zone3`` Producer input trees from *excel*."""
    workbook = wb.read_workbook(excel)

    # 1. Fetch available Zone1 sheets and resolve all models
    z1_sheet_names = P.zone1_sheets(workbook)
    resolved = P.resolve_multi_models(workbook, z1_sheet_names)

    zone3 = P.parse_zone(workbook, names.sheet("zone3"))
    topology = dyd.checked_topology(zone3)

    template = P.template_for(resolved["zone3"]["zone3_lib"])
    builder_gen_id = BESS_ID if template == "model_BESS" else PPM_ID

    # 2. Extract controls mapping
    config = wb.parse_config(workbook)

    root = outdir / "Dynawo"
    for zone in ("Zone1", "Zone3"):
        (root / zone).mkdir(parents=True, exist_ok=True)

    z1_par_sets = []
    generators_info = []
    is_multi_topology = len(z1_sheet_names) > 1

    # 3. Process each generating unit individually
    for idx, sheet_name in enumerate(z1_sheet_names):
        zone1_data = P.parse_zone(workbook, sheet_name)
        lv_control = P.is_true(zone1_data.get(names.row("Zone1", "converter_lv_control"), "True"))

        # Note: Control blocks could ideally be scoped per generator variant
        control = par.control_params(workbook, lv_control)
        z1_control = par.control_params_for_zone(control, config.zones, "Zone1")
        z3_control = par.control_params_for_zone(control, config.zones, "Zone3")

        if not z1_control:
            raise ValueError(par.empty_zone1_reason(config))

        gen_id = (
            f"{PRODUCER_NAME}_G{idx + 1}"
            if is_multi_topology
            else dyd.GEN_ID_BY_TECH[P.technology(resolved["zone3"]["zone3_lib"])]
        )
        xfmr_id = f"{GROUP_XFMR_ID}_{idx + 1}" if is_multi_topology else GROUP_XFMR_ID

        gen_info = {
            "gen_id": gen_id,
            "xfmr_id": xfmr_id,
            "resolved": resolved["zone1"][sheet_name],
            "zone1_data": zone1_data,
            "lv_control": lv_control,
            "z1_control": z1_control,
            "z3_control": z3_control,
        }
        generators_info.append(gen_info)

        # Sequentially aggregate Zone 1 PAR sets for all generators
        z1_par_sets.extend(
            _zone1_par_sets(
                root, zone1_data, z1_control, gen_info["resolved"], gen_id, lv_control, xfmr_id
            )
        )

    rename = (
        {builder_gen_id: generators_info[0]["gen_id"]}
        if not is_multi_topology and generators_info[0]["gen_id"] != builder_gen_id
        else {}
    )

    # 4. Generate the final files
    dyd.write_dyd(root, PRODUCER_NAME, topology, template, generators_info, rename)

    write_producer_par_file(
        root / "Zone1",
        f"{PRODUCER_NAME}.par",
        z1_par_sets,
    )

    write_producer_par_file(
        root / "Zone3",
        f"{PRODUCER_NAME}.par",
        _zone3_par_sets(generators_info, zone3, resolved["zone3"], topology),
    )

    # Use the first generator's Zone 1 limits for compatibility; the plant's power share should
    # aggregate correctly
    ini.write_ini(
        root,
        PRODUCER_NAME,
        topology,
        generators_info,
        zone3,
        include_consumption=template == "model_BESS",
    )

    all_curves_reports = []

    for gen in generators_info:
        signals = sig.parse_signals(workbook, gen["gen_id"], storage=template == "model_BESS")

        curves = rc.write_reference_curves(outdir, gen["gen_id"], signals, excel.parent)

        all_curves_reports.append(curves)

    final_report = [_submodel_report(resolved, config.selections, control), ""]

    for curve_report in all_curves_reports:
        final_report.append(_reference_curves_report(curve_report))
        final_report.append("")

    return "\n".join(final_report).strip()
