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

    read workbook -> generating units (one per Zone1<x>, model from the Model Map) -> parse Zone3
    + control params -> DYD (producer_dyd) -> PAR (par.*) -> INI (producer_ini) -> reference curves

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
from dycov.excel import units as U
from dycov.excel import workbook as wb
from dycov.excel.reference_curves import dicts
from dycov.files.producer_dyd_file import GROUP_XFMR_ID, MAIN_XFMR_ID
from dycov.files.producer_par_file import write_producer_par_file

# Base name of the Dynawo input files and of the reference-curve directory: DyCoV derives both
# from the same producer name, so a rename travels through this one constant.
PRODUCER_NAME = "Producer"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _submodel_report(units: list, selections: list, control_params: list) -> str:
    """Report the model of each unit, the blocks declared in ``Général`` and whether their
    parameter sheet contributed a selected variant with values (``present``) or not
    (``missing``)."""
    present = {p["block"] for p in control_params}
    lines = ["Submodel report"]
    for unit in units:
        model = unit.model
        if len(units) > 1:
            lines.append(f"  {P.sheet_of(unit.zone1)}")
        lines += [
            f"  Zone3 (plant)   : {model['zone3_lib']}  (prefix {model['zone3_prefix']})",
            f"  Zone1 (turbine) : {model['zone1_lib']}  (prefix {model['zone1_prefix']})",
        ]
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


def _zone1_par_sets(root: Path, unit: U.GeneratingUnit, control: list) -> list:
    """The unit and, unless its own transformer reaches the internal node, the group one."""
    zone1, model = unit.zone1, unit.model
    s_nom = P.numbers("Zone1", zone1)("s_nom")
    sets = [
        par.converter_par_set(
            unit.gen_id, model["zone1_prefix"], control, zone1, s_nom, model["zone1_lib"]
        )
    ]
    if unit.lv_control:
        sets.append(par.group_transformer_par_set(GROUP_XFMR_ID, zone1, s_nom))
    else:
        dyd.drop_group_transformer(
            root / "Zone1" / f"{unit.zone1_file}.dyd",
            unit.gen_id,
            f"{model['zone1_prefix']}terminal",
        )
    return sets


def _zone3_par_sets(units: list, controls: list, zone3: dict, topology: str) -> list:
    """The plant's units, its main transformer, and the equipment the topology adds.

    Every unit takes the plant's ``SnZone3`` as its ``SNom``, as ``examples/Model/Wind/WECC4``
    does, its share of the plant's power coming from the INI instead.
    """
    s_nom = P.numbers("Zone3", zone3)("s_nom")
    sets = [
        par.converter_par_set(
            unit.plant_id,
            unit.model["zone3_prefix"],
            control,
            unit.zone1,
            s_nom,
            unit.model["zone3_lib"],
            plant_model=True,
        )
        for unit, control in zip(units, controls)
    ]
    sets.append(par.main_transformer_par_set(MAIN_XFMR_ID, zone3))
    if "aux" in topology.casefold():
        sets += [
            par.aux_transformer_par_set("AuxLoad_Xfmr", zone3),
            par.aux_load_par_set("Aux_Load", zone3),
        ]
    if topology.casefold().endswith("i"):
        sets.append(par.collector_line_par_set("IntNetwork_Line", zone3, units[0].zone1))
    return sets


def _unit_control(workbook: dict, config, unit: U.GeneratingUnit) -> list:
    """The control parameters of a unit, refusing a selection that leaves its Zone1 without any."""
    control = par.control_params(workbook, unit.lv_control)
    if not par.control_params_for_zone(control, config.zones, "Zone1"):
        raise ValueError(par.empty_zone1_reason(config))
    return control


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


def _write_dynawo(
    root: Path,
    zones: dict,
    zone3: dict,
    topology: str,
    units: list,
    controls: list,
    template: str,
) -> None:
    """Write both zones' DYD, PAR and INI: a set of Zone1 files per unit, and the plant's Zone3."""
    for zone in ("Zone1", "Zone3"):
        (root / zone).mkdir(parents=True, exist_ok=True)

    dyd.write_dyd(root, PRODUCER_NAME, topology, template, units)

    for unit, control in zip(units, controls):
        write_producer_par_file(
            root / "Zone1",
            f"{unit.zone1_file}.par",
            _zone1_par_sets(root, unit, par.control_params_for_zone(control, zones, "Zone1")),
        )
    write_producer_par_file(
        root / "Zone3",
        f"{PRODUCER_NAME}.par",
        _zone3_par_sets(
            units,
            [par.control_params_for_zone(control, zones, "Zone3") for control in controls],
            zone3,
            topology,
        ),
    )

    ini.write_ini(
        root,
        PRODUCER_NAME,
        topology,
        units,
        zone3,
        include_consumption=template == "model_BESS",
    )


def generate(excel: Path, outdir: Path) -> str:
    """Generate the ``Dynawo/Zone1`` + ``Dynawo/Zone3`` Producer input trees from *excel*."""
    workbook = wb.read_workbook(excel)
    zone3 = P.parse_zone(workbook, names.sheet("zone3"))
    topology = dyd.checked_topology(zone3)
    units = U.generating_units(workbook, topology, PRODUCER_NAME)
    template = P.template_for(units[0].model["zone3_lib"])

    config = wb.parse_config(workbook)
    controls = [_unit_control(workbook, config, unit) for unit in units]

    _write_dynawo(outdir / "Dynawo", config.zones, zone3, topology, units, controls, template)

    # The signal sheets describe the curves of a single unit.
    (unit,) = units
    signals = sig.parse_signals(workbook, unit.gen_id, storage=template == "model_BESS")
    curves = rc.write_reference_curves(outdir, PRODUCER_NAME, signals, excel.parent)

    return "\n".join(
        [
            _submodel_report(units, config.selections, controls[0]),
            "",
            _reference_curves_report(curves),
        ]
    )
