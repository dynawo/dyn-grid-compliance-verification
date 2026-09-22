#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#
"""
Demo: register a non-catalog Dynawo model in PyPowsybl via `additionalModelsFile`
and show it reach "instantiation OK", vs "not found" without it.

PyPowsybl has no DYD/JOBS/CRV; powsybl-dynawo generates them from the IIDM network +
a ModelMapping. A model must be known to powsybl-dynawo's model supplier. The base
catalog can be extended at runtime with the `additionalModelsFile` provider parameter
(registering libs into EXISTING categories — see additional_models.json).

The demo runs the same WECC case twice against your local Dynawo:
  1. WITHOUT additionalModelsFile -> "Model WTG3WeccCurrentSource1 not found for WECC"
  2. WITH    additionalModelsFile -> "Model WTG3WeccCurrentSource1 ... instantiation OK"

(The run then fails later on unconnected omegaRef/PCC wiring — completing that is the
next step; here we only demonstrate model registration.)

Usage:
    python run_native_vs_pypowsybl.py                        # WTG3 (non-catalog)
    python run_native_vs_pypowsybl.py WT4BWeccCurrentSource  # a base-catalog model
    # register a model under a chosen existing category via a custom additions file:
    python run_native_vs_pypowsybl.py IECWT4BCurrentSource2020 probe_iec_under_wecc.json
    DYNAWO_HOME=/opt/Dynawo_vX/dynawo python run_native_vs_pypowsybl.py

Requires the optional extra: uv pip install -e ".[dynawo-pypowsybl]".
"""
from __future__ import annotations

import glob
import os
import re
import sys
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs"
WORK = HERE / "_run"
NS = "http://www.rte-france.com/dynawo"
Q = f"{{{NS}}}"

MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "WTG3WeccCurrentSource1"
ADD_ARG = sys.argv[2] if len(sys.argv) > 2 else "additional_models.json"
ADDITIONAL = Path(ADD_ARG) if Path(ADD_ARG).is_absolute() else (HERE / ADD_ARG)


def find_dynawo_home() -> str:
    if os.environ.get("DYNAWO_HOME"):
        return os.environ["DYNAWO_HOME"]
    candidates = sorted(glob.glob("/opt/Dynawo_v*/dynawo"))
    if not candidates:
        sys.exit("No Dynawo found. Set DYNAWO_HOME to the dir containing dynawo.sh")
    return candidates[-1]  # newest by name (…_YYYYMMDD)


def get_set(par_path: Path, set_id: str):
    root = etree.parse(str(par_path)).getroot()
    for s in root.findall(f"{Q}set"):
        if s.get("id") == set_id:
            return s
    raise KeyError(f"set '{set_id}' not found in {par_path}")


def setup_workdir() -> str:
    """Write config.yml + models.par + network.par into WORK; return dynawo home."""
    WORK.mkdir(exist_ok=True)
    home = find_dynawo_home()

    root = etree.Element(f"{Q}parametersSet", nsmap={None: NS})
    root.append(get_set(INPUTS / "Producer.par", "Wind_Turbine"))
    root.append(get_set(INPUTS / "TSOModel.par", "InfiniteBus"))
    root.append(get_set(INPUTS / "TSOModel.par", "Line"))
    bus = etree.SubElement(root, f"{Q}set")
    bus.set("id", "Bus")
    e = etree.SubElement(bus, f"{Q}par")
    e.set("type", "DOUBLE"), e.set("name", "bus_UNom"), e.set("value", "225.0")
    etree.ElementTree(root).write(str(WORK / "models.par"), pretty_print=True,
                                  xml_declaration=True, encoding="UTF-8")

    (WORK / "network.par").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<parametersSet xmlns="http://www.rte-france.com/dynawo">\n'
        '  <set id="N">\n'
        '    <par type="DOUBLE" name="capacitor_no_reclosing_delay" value="300"/>\n'
        '    <par type="DOUBLE" name="load_alpha" value="1"/>\n'
        '    <par type="DOUBLE" name="load_alphaLong" value="0"/>\n'
        '    <par type="DOUBLE" name="load_beta" value="2"/>\n'
        '    <par type="DOUBLE" name="load_betaLong" value="0"/>\n'
        '    <par type="BOOL" name="load_isControllable" value="false"/>\n'
        '    <par type="BOOL" name="load_isRestorative" value="false"/>\n'
        '    <par type="DOUBLE" name="load_tFilter" value="10"/>\n'
        '    <par type="DOUBLE" name="line_currentLimit_maxTimeOperation" value="90"/>\n'
        '    <par type="DOUBLE" name="transformer_currentLimit_maxTimeOperation" value="90"/>\n'
        '    <par type="DOUBLE" name="transformer_t1st_THT" value="60"/>\n'
        '    <par type="DOUBLE" name="transformer_t1st_HT" value="60"/>\n'
        '    <par type="DOUBLE" name="transformer_tNext_THT" value="10"/>\n'
        '    <par type="DOUBLE" name="transformer_tNext_HT" value="10"/>\n'
        '    <par type="DOUBLE" name="transformer_tolV" value="0.0149999997"/>\n'
        '  </set>\n</parametersSet>\n'
    )
    (WORK / "solvers.par").write_text((INPUTS / "solvers.par").read_text())
    (WORK / "config.yml").write_text(
        "dynawo:\n"
        f"  homeDir: {home}\n"
        "dynawo-simulation-default-parameters:\n"
        f"  parametersFile: {WORK / 'models.par'}\n"
        f"  network.parametersFile: {WORK / 'network.par'}\n"
        '  network.parametersId: "N"\n'
        "  solver.type: IDA\n"
        f"  solver.parametersFile: {WORK / 'solvers.par'}\n"
        "  solver.parametersId: IDA\n"
    )
    return home


_home = setup_workdir()
os.environ["POWSYBL_CONFIG_DIRS"] = str(WORK)
os.environ["POWSYBL_CONFIG_NAME"] = "config"

import pypowsybl as pp  # noqa: E402
import pypowsybl.network as nw  # noqa: E402
import pypowsybl.dynamic as dyn  # noqa: E402
import pypowsybl.loadflow as lf  # noqa: E402
from pypowsybl.report import ReportNode  # noqa: E402

print(f"pypowsybl {pp.__version__} | Dynawo home: {_home} | model_name: {MODEL_NAME}\n")


def build_network():
    n = nw.create_empty("wecc_demo")
    n.create_substations(id="S1")
    n.create_voltage_levels(id="VL_INF", substation_id="S1", nominal_v=225.0, topology_kind="BUS_BREAKER")
    n.create_voltage_levels(id="VL_PDR", substation_id="S1", nominal_v=225.0, topology_kind="BUS_BREAKER")
    n.create_buses(id="BINF", voltage_level_id="VL_INF")
    n.create_buses(id="BPDR", voltage_level_id="VL_PDR")
    zbase = 225.0**2 / 100.0
    n.create_lines(id="LINE", voltage_level1_id="VL_INF", bus1_id="BINF",
                   voltage_level2_id="VL_PDR", bus2_id="BPDR",
                   r=0.0, x=0.060603566529492454 * zbase, g1=0, b1=0, g2=0, b2=0)
    n.create_generators(id="InfBusGen", voltage_level_id="VL_INF", bus_id="BINF",
                        target_p=0.0, min_p=-2000, max_p=2000,
                        target_v=1.0453506870830052 * 225.0, voltage_regulator_on=True)
    n.create_generators(id="Wind_Turbine", voltage_level_id="VL_PDR", bus_id="BPDR",
                        target_p=76.0, min_p=0, max_p=90,
                        target_v=1.0449818594707512 * 225.0, voltage_regulator_on=True)
    lf.run_ac(n)
    s = re.sub(r'sourceFormat="[^"]*"', 'sourceFormat="IIDM"',
               n.save_to_string(format="XIIDM"), count=1)
    xiidm = WORK / "net.xiidm"
    xiidm.write_text(s)
    return nw.load(str(xiidm))


def run_once(n, with_additional: bool):
    mm = dyn.ModelMapping()
    mm.add_wecc(static_id="Wind_Turbine", parameter_set_id="Wind_Turbine", model_name=MODEL_NAME)
    mm.add_infinite_bus(static_id="BINF", parameter_set_id="InfiniteBus")
    mm.add_base_line(static_id="LINE", parameter_set_id="Line", model_name="Line")
    mm.add_base_bus(static_id="BPDR", parameter_set_id="Bus", model_name="Bus")
    ov = dyn.OutputVariableMapping()

    provider = {"additionalModelsFile": str(ADDITIONAL)} if with_additional else {}
    params = dyn.Parameters(start_time=0.0, stop_time=5.0, provider_parameters=provider)
    rn = ReportNode()
    try:
        dyn.Simulation().run(n, mm, dyn.EventMapping(), ov, params, report_node=rn)
    except Exception:  # noqa: BLE001  (run fails later on wiring; we only want the supplier lines)
        pass
    supplier = [ln for ln in str(rn).splitlines()
                if MODEL_NAME in ln or "not found" in ln or "instantiation" in ln]
    return supplier


def main():
    n = build_network()
    print("### 1) WITHOUT additionalModelsFile (base catalog only) ###")
    for ln in run_once(n, with_additional=False):
        print(ln.strip())
    print(f"\n### 2) WITH additionalModelsFile ({ADDITIONAL.name}) ###")
    for ln in run_once(n, with_additional=True):
        print(ln.strip())
    print("\n(If line 1 says 'not found' and line 2 says 'instantiation OK', the "
          "non-catalog model was successfully registered at runtime.)")


if __name__ == "__main__":
    main()
