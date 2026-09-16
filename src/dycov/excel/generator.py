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
    root: Path, zone1: dict, control: list, resolved: dict, gen_id: str, lv_control: bool
) -> list:
    """The unit and, unless its own transformer reaches the internal node, the group one."""
    s_nom = P.numbers("Zone1", zone1)("s_nom")
    sets = [
        par.converter_par_set(
            gen_id, resolved["zone1_prefix"], control, zone1, s_nom, resolved["zone1_lib"]
        )
    ]
    if lv_control:
        sets.append(par.group_transformer_par_set(GROUP_XFMR_ID, zone1, s_nom))
    else:
        dyd.drop_group_transformer(
            root / "Zone1" / f"{PRODUCER_NAME}.dyd",
            gen_id,
            f"{resolved['zone1_prefix']}terminal",
        )
    return sets


def _zone3_par_sets(
    zone1: dict, zone3: dict, control: list, resolved: dict, gen_id: str, topology: str
) -> list:
    """The plant, its main transformer, and the equipment the topology adds."""
    sets = [
        par.converter_par_set(
            gen_id,
            resolved["zone3_prefix"],
            control,
            zone1,
            P.numbers("Zone3", zone3)("s_nom"),
            resolved["zone3_lib"],
            plant_model=True,
        ),
        par.main_transformer_par_set(MAIN_XFMR_ID, zone3),
    ]
    if "aux" in topology.casefold():
        sets += [
            par.aux_transformer_par_set("AuxLoad_Xfmr", zone3),
            par.aux_load_par_set("Aux_Load", zone3),
        ]
    if topology.casefold().endswith("i"):
        sets.append(par.collector_line_par_set("IntNetwork_Line", zone3, zone1))
    return sets


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def tests_without_metadata(outdir: Path, producer: str = PRODUCER_NAME) -> list:
    """The generated tests DyCoV would refuse to run, because their metadata is blank.

    Parameters
    ----------
    outdir: Path
        Directory the generation wrote into.
    producer: str
        Producer name, which names the reference-curve subdirectory.

    Returns
    -------
    list
        Name of every test whose ``.dict`` leaves a metadata key without a value. A test with no
        ``.csv`` is not in the list: DyCoV reports those as not applicable and carries on.
    """
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
    resolved = P.resolve_models(workbook)
    template = P.template_for(resolved["zone3_lib"])
    builder_gen_id = BESS_ID if template == "model_BESS" else PPM_ID
    gen_id = dyd.GEN_ID_BY_TECH[P.technology(resolved["zone3_lib"])]
    rename = {builder_gen_id: gen_id} if gen_id != builder_gen_id else {}

    zone3 = P.parse_zone(workbook, names.sheet("zone3"))
    zone1 = P.parse_zone(workbook, names.sheet("zone1"))
    lv_control = P.is_true(zone1.get(names.row("Zone1", "converter_lv_control"), "True"))
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
        root / "Zone1",
        f"{PRODUCER_NAME}.par",
        _zone1_par_sets(root, zone1, z1_control, resolved, gen_id, lv_control),
    )
    write_producer_par_file(
        root / "Zone3",
        f"{PRODUCER_NAME}.par",
        _zone3_par_sets(zone1, zone3, z3_control, resolved, gen_id, topology),
    )

    ini.write_ini(
        root,
        PRODUCER_NAME,
        topology,
        zone1,
        zone3,
        gen_id,
        include_consumption=template == "model_BESS",
    )

    signals = sig.parse_signals(workbook, gen_id, storage=template == "model_BESS")
    curves = rc.write_reference_curves(outdir, PRODUCER_NAME, signals, excel.parent)

    return "\n".join(
        [
            _submodel_report(resolved, config.selections, control),
            "",
            _reference_curves_report(curves),
        ]
    )
