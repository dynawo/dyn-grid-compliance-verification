#!/usr/bin/env python3
# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Excel -> DyCoV input generator: orchestration + emission.

    read workbook -> resolve model (Model Map) -> parse Zone1/Zone3 + control params
    -> compute electrical values -> DyCoV builders -> write Zone1 + Zone3.

Reuses the ``dycov.files`` builders for structure and supplies the concrete libs, prefixed
parameter names and computed values; the PAR is written install-independently from the Excel.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from lxml import etree

_HERE = Path(__file__).resolve().parent
for _p in (_HERE, _HERE.parent.parent / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import electrical as el  # noqa: E402
import parse as P  # noqa: E402
import workbook as wb  # noqa: E402  (the stdlib xlsx reader)

from dycov.files.producer_dyd_file import (  # noqa: E402
    BESS_ID,
    PPM_ID,
    XFMR_ID,
    create_producer_dyd_file,
    fill_producer_dyd,
    write_producer_dyd,
)
from dycov.files.producer_ini_file import write_producer_ini_file  # noqa: E402
from dycov.files.producer_par_file import write_producer_par_file  # noqa: E402

LIB_XFMR_OLTC = "TransformerRatioTapChanger"
LIB_XFMR_FIXED = "TransformerFixedRatio"
LIB_LINE = "Line"
LIB_LOAD = "LoadAlphaBeta"
LIB_BUS = "Bus"

# Generator block id must pass topology_checks._is_valid_generator.
GEN_ID_BY_TECH = {"PV": "PV_Array", "Wind": "Wind_Turbine", "BESS": "Bess"}

PU_BASE_NOTE = "impedances in pu, base SnRef = 100 MVA"


def _f(value) -> float:
    return float(value)


# ---------------------------------------------------------------------------
# PAR set builders (pure)
# ---------------------------------------------------------------------------


def converter_par_set(par_id: str, prefix: str, control_params: list, zone1: dict, s_nom) -> tuple:
    """Converter ``set``: prefixed control params, ``ConverterLVControl``, the internal ``LvTr``
    (``RLvTrPu``/``XLvTrPu`` from ``Z_cc_LvTr``; the model has no B/G), and ``SNom``."""
    params = [{**p, "name": f"{prefix}{p['name']}"} for p in control_params]
    lv_control = _is_true(zone1.get("ConverterLVControl", "True"))
    params.append(
        {"name": f"{prefix}ConverterLVControl", "type": "BOOL",
         "value": str(lv_control).lower(), "comments": ["LV Transformer"]}
    )
    r_pu, x_pu = el.transformer_impedance(
        _f(zone1["Z_cc_LvTr"]), _f(zone1["R_cc_LvTr / X_cc_LvTr"]), _f(zone1["SnZone1"])
    )
    params += [
        {"name": f"{prefix}RLvTrPu", "type": "DOUBLE", "value": r_pu},
        {"name": f"{prefix}XLvTrPu", "type": "DOUBLE", "value": x_pu},
    ]
    params.append(
        {"name": f"{prefix}SNom", "type": "DOUBLE", "value": _f(s_nom), "comments": ["General"]}
    )
    return par_id, params


def main_transformer_par_set(par_id: str, zone3: dict) -> tuple:
    """Zone3 main transformer (``TransformerRatioTapChanger``): impedance + OLTC taps."""
    r_pu, x_pu = el.transformer_impedance(
        _f(zone3["Z_cc_TP"]), _f(zone3["R_cc_TP / X_cc_TP"]), _f(zone3["SnZone3"])
    )
    taps = el.transformer_taps(int(_f(zone3["N_prises"])), _f(zone3["r_min"]), _f(zone3["r_max"]))
    params = [
        {"name": "transformer_SNom", "type": "DOUBLE", "value": _f(zone3["SnZone3"]),
         "comments": [PU_BASE_NOTE]},
        {"name": "transformer_RPu", "type": "DOUBLE", "value": r_pu},
        {"name": "transformer_XPu", "type": "DOUBLE", "value": x_pu},
        {"name": "transformer_BPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_GPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_AlphaTfo0", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_RatioTfo0Pu", "type": "DOUBLE", "value": taps["RatioTfo0Pu"]},
        {"name": "transformer_RatioTfoMaxPu", "type": "DOUBLE", "value": taps["RatioTfoMaxPu"]},
        {"name": "transformer_RatioTfoMinPu", "type": "DOUBLE", "value": taps["RatioTfoMinPu"]},
        {"name": "transformer_NbTap", "type": "INT", "value": taps["NbTap"]},
        {"name": "transformer_Tap0", "type": "INT", "value": taps["Tap0"]},
    ]
    return par_id, params


def group_transformer_par_set(par_id: str, zone1: dict, s_nom) -> tuple:
    """Generator step-up transformer (``TransformerFixedRatio``) from ``Zone1a``'s ``Z_cc_TG`` /
    ``r_TG``; ``s_nom`` is the impedance base (``SnZone1`` in Zone1, ``SnZone3`` in Zone3)."""
    r_pu, x_pu = el.transformer_impedance(
        _f(zone1["Z_cc_TG"]), _f(zone1["R_cc_TG / X_cc_TG"]), _f(s_nom)
    )
    params = [
        {"name": "transformer_RPu", "type": "DOUBLE", "value": r_pu, "comments": [PU_BASE_NOTE]},
        {"name": "transformer_XPu", "type": "DOUBLE", "value": x_pu},
        {"name": "transformer_BPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_GPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_rTfoPu", "type": "DOUBLE", "value": _f(zone1["r_TG"])},
    ]
    return par_id, params


def aux_transformer_par_set(par_id: str, zone3: dict) -> tuple:
    r_pu, x_pu = el.transformer_impedance(
        _f(zone3["Z_cc_TA"]), _f(zone3["R_cc_TA / X_cc_TA"]), _f(zone3["Sn_A"])
    )
    return par_id, [
        {"name": "transformer_RPu", "type": "DOUBLE", "value": r_pu, "comments": [PU_BASE_NOTE]},
        {"name": "transformer_XPu", "type": "DOUBLE", "value": x_pu},
        {"name": "transformer_BPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_GPu", "type": "DOUBLE", "value": 0.0},
        {"name": "transformer_rTfoPu", "type": "DOUBLE", "value": _f(zone3["r_TA"])},
    ]


def aux_load_par_set(par_id: str, zone3: dict) -> tuple:
    p_ref, q_ref = el.load_pu(_f(zone3["P_A"]), _f(zone3["Q_A"]))
    return par_id, [
        {"name": "load_PRefPu", "type": "DOUBLE", "value": p_ref},
        {"name": "load_QRefPu", "type": "DOUBLE", "value": q_ref},
        {"name": "load_alpha", "type": "DOUBLE", "value": _f(zone3["alpha"])},
        {"name": "load_beta", "type": "DOUBLE", "value": _f(zone3["beta"])},
    ]


def collector_line_par_set(par_id: str, zone3: dict) -> tuple:
    line = el.line_impedance(
        _f(zone3["R_rc"]), _f(zone3["X_rc"]), _f(zone3["B_rc"]), _f(zone3["G_rc"]),
        _f(zone3["Un1"]),
    )
    return par_id, [
        {"name": "line_RPu", "type": "DOUBLE", "value": line["RPu"]},
        {"name": "line_XPu", "type": "DOUBLE", "value": line["XPu"]},
        {"name": "line_BPu", "type": "DOUBLE", "value": line["BPu"]},
        {"name": "line_GPu", "type": "DOUBLE", "value": line["GPu"]},
    ]


# ---------------------------------------------------------------------------
# Submodel report (section 8)
# ---------------------------------------------------------------------------


def submodel_report(resolved: dict, selections: list, control_params: list) -> str:
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


def zone_control_params(control_params: list, zones: dict, zone: str) -> list:
    """Control params whose block declares *zone* in ``Général``, in the same (workbook) order;
    the provenance ``block`` label is dropped before emission. A block with no declared zone
    enters no zone's PAR."""
    return [
        {k: v for k, v in p.items() if k != "block"}
        for p in control_params
        if zone in zones.get(p["block"], [])
    ]


def _empty_zone1_reason(config) -> str:
    """Why Zone1 came out without control parameters — never generate it silently incomplete."""
    declared = [
        block for block, choice in config.selections
        if wb._strip_accents(choice) not in wb._NO_BLOCK
        and "Zone1" in config.zones.get(block, [])
    ]
    if not declared:
        return (
            "no selected control block declares Zone1 (see the 'Zone' column in 'Général'); "
            "refusing to generate an incomplete Zone1."
        )
    return (
        f"the Zone1 control blocks ({', '.join(declared)}) carry no parameter values — the "
        f"parameter sheets look unfilled; refusing to generate an incomplete Zone1."
    )


def _is_true(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "vrai", "oui", "yes")


def drop_group_transformer(dyd_file: Path, gen_id: str, gen_terminal: str) -> None:
    """Remove the ``StepUp_Xfmr`` block and wire the generator to its downstream node."""
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(dyd_file), parser)
    root = tree.getroot()
    ns = etree.QName(root).namespace

    downstream = None
    for connect in list(root.iterfind(f"{{{ns}}}connect")):
        id1, var1, id2, var2 = (connect.get(k) for k in ("id1", "var1", "id2", "var2"))
        if id1 == XFMR_ID and var1 == "transformer_terminal2":
            downstream = (id2, var2)
        elif id2 == XFMR_ID and var2 == "transformer_terminal2":
            downstream = (id1, var1)
        if XFMR_ID in (id1, id2):
            root.remove(connect)
    for bbmodel in list(root.iterfind(f"{{{ns}}}blackBoxModel")):
        if bbmodel.get("id") == XFMR_ID:
            root.remove(bbmodel)
    if downstream:
        etree.SubElement(
            root, f"{{{ns}}}connect",
            id1=gen_id, var1=gen_terminal, id2=downstream[0], var2=downstream[1],
        )
    write_producer_dyd(root, dyd_file)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def generate(excel: Path, outdir: Path) -> str:
    """Generate the ``Dynawo/Zone1`` + ``Dynawo/Zone3`` Producer input trees from *excel*."""
    workbook = wb.read_workbook(excel)
    resolved = P.resolve_models(workbook)
    template = P.template_for(resolved["zone3_lib"])
    builder_gen_id = BESS_ID if template == "model_BESS" else PPM_ID
    gen_id = GEN_ID_BY_TECH[P.technology(resolved["zone3_lib"])]
    rename = {builder_gen_id: gen_id} if gen_id != builder_gen_id else {}

    zone3 = P.parse_zone(workbook, "Zone3")
    zone1 = P.parse_zone(workbook, "Zone1a")
    control = P.parse_control_params(workbook)
    topology = str(zone3["Topologie"]).strip()

    config = wb.parse_config(workbook)
    z1_control = zone_control_params(control, config.zones, "Zone1")
    z3_control = zone_control_params(control, config.zones, "Zone3")
    if not z1_control:
        raise ValueError(_empty_zone1_reason(config))

    root = outdir / "Dynawo"
    (root / "Zone1").mkdir(parents=True, exist_ok=True)
    (root / "Zone3").mkdir(parents=True, exist_ok=True)

    create_producer_dyd_file(root, topology, template)

    net_libs = {XFMR_ID: LIB_XFMR_OLTC, "AuxLoad_Xfmr": LIB_XFMR_FIXED, "Aux_Load": LIB_LOAD,
                "IntNetwork_Line": LIB_LINE, "Int_Bus": LIB_BUS}
    fill_producer_dyd(
        root / "Zone1" / "Producer.dyd",
        libs={**net_libs, XFMR_ID: LIB_XFMR_FIXED, gen_id: resolved["zone1_lib"]},
        terminals={gen_id: f"{resolved['zone1_prefix']}terminal"},
        rename=rename,
    )
    fill_producer_dyd(
        root / "Zone3" / "Producer.dyd",
        libs={**net_libs, XFMR_ID: LIB_XFMR_FIXED, gen_id: resolved["zone3_lib"]},
        terminals={gen_id: f"{resolved['zone3_prefix']}terminal"},
        rename=rename,
    )

    lv_control = _is_true(zone1.get("ConverterLVControl", "True"))

    def _stepup(zone_dir: str, prefix: str, s_nom) -> list:
        # ConverterLVControl=True -> external StepUp_Xfmr (Z_cc_TG); False -> no StepUp (the LvTr
        # carries the step-up), so drop the block and wire the generator to its downstream node.
        if lv_control:
            return [group_transformer_par_set(XFMR_ID, zone1, s_nom)]
        drop_group_transformer(root / zone_dir / "Producer.dyd", gen_id, f"{prefix}terminal")
        return []

    z1_sets = [
        converter_par_set(gen_id, resolved["zone1_prefix"], z1_control, zone1, zone1["SnZone1"]),
        *_stepup("Zone1", resolved["zone1_prefix"], zone1["SnZone1"]),
    ]
    write_producer_par_file(root / "Zone1", "Producer.par", z1_sets)

    z3_sets = [
        converter_par_set(gen_id, resolved["zone3_prefix"], z3_control, zone1, zone3["SnZone3"]),
        *_stepup("Zone3", resolved["zone3_prefix"], zone3["SnZone3"]),
    ]
    if "aux" in topology.casefold():
        z3_sets += [aux_transformer_par_set("AuxLoad_Xfmr", zone3),
                    aux_load_par_set("Aux_Load", zone3)]
    if topology.casefold().endswith("i"):
        z3_sets.append(collector_line_par_set("IntNetwork_Line", zone3))
    write_producer_par_file(root / "Zone3", "Producer.par", z3_sets)

    include_consumption = template == "model_BESS"
    # u_nom_at_PDR = the converter control's nominal side: Un2 (BT) if ConverterLVControl else Un1.
    write_producer_ini_file(
        root / "Zone1", "Producer.ini", "S",
        values={"p_max_injection_at_PDR": zone1["Pmax_injection_z1"],
                "u_nom_at_PDR": zone1["Un2"] if lv_control else zone1["Un1"],
                "q_max_at_PDR": zone1["Qmax_z1"], "q_min_at_PDR": zone1["Qmin_z1"]},
        gen_sharing={gen_id: (zone1["P_share"], zone1["Q_share"])},
    )
    z3_values = {"p_max_injection_at_PDR": zone3["Pmax_PDR"], "u_nom_at_PDR": zone3["Un_PDR"],
                 "q_max_at_PDR": zone3["Qmax_PDR"], "q_min_at_PDR": zone3["Qmin_PDR"]}
    if include_consumption:
        z3_values["p_max_consumption_at_PDR"] = zone1.get("Pmax_soutirage_z1", "")
    write_producer_ini_file(
        root / "Zone3", "Producer.ini", topology, z3_values,
        gen_sharing={gen_id: (zone1["P_share"], zone1["Q_share"])},
        include_consumption=include_consumption,
    )

    return submodel_report(resolved, config.selections, control)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate DyCoV Producer inputs from a WECC Excel.")
    ap.add_argument("--excel", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args(argv)
    if not args.excel.is_file():
        ap.error(f"Excel not found: {args.excel}")
    try:
        report = generate(args.excel, args.outdir)
    except (ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(report)
    print(f"\nWrote input tree under: {args.outdir / 'Dynawo'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
