#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Attempt a COMPLETE dynamic simulation through PyPowsybl (IEEE-14 + synchronous
generators), based on pypowsybl's own integration test (integration_tests/test_dynawo.py,
which upstream asserts SUCCESS).

Against Dynawo 1.8.0-master this FAILS (connection variable-name drift: powsybl-dynawo 1.15
targets the Dynawo 1.7.0 release interface). See ../../docs/design/Dynawo_PyPowsybl_feasibility.md.

The Dynawo location is taken from $DYNAWO_HOME (or auto-detected under /opt/Dynawo_v*);
config.yml is generated automatically — see config.yml.example.
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_dynawo_home() -> str:
    """Locate the Dynawo install (dir containing dynawo.sh). Override with $DYNAWO_HOME."""
    if os.environ.get("DYNAWO_HOME"):
        return os.environ["DYNAWO_HOME"]
    candidates = sorted(glob.glob("/opt/Dynawo_v*/dynawo"))
    if not candidates:
        sys.exit("No Dynawo found. Set DYNAWO_HOME to the dir containing dynawo.sh "
                 "(see config.yml.example).")
    return candidates[-1]  # newest by name (…_YYYYMMDD)


# config.yml is generated here (machine-specific homeDir) — never committed.
(HERE / "config.yml").write_text(
    "dynawo:\n"
    f"  homeDir: {find_dynawo_home()}\n"
    "  debug: true\n"
)
os.environ["POWSYBL_CONFIG_DIRS"] = str(HERE)
os.environ["POWSYBL_CONFIG_NAME"] = "config"

import pandas as pd
import pypowsybl as pp
import pypowsybl.dynamic as dyn
import pypowsybl.report as rp

network = pp.network.create_ieee14()

mm = dyn.ModelMapping()
# base_load B3-L dropped: its switchOff wiring (load_switchOffSignal1 / B3_switchOff) is
# incompatible with Dynawo 1.8.0's network model (version drift). Keep only the SMs.
gens = pd.DataFrame(
    index=pd.Series(name="static_id", data=["B6-G", "B8-G"]),
    data={"parameter_set_id": ["GSTWPR_6", "GSTWPR_8"],
          "model_name": "GeneratorSynchronousThreeWindingsProportionalRegulations"},
)
mm.add_synchronous_generator(gens)

em = dyn.EventMapping()
# events dropped for the first green run (version drift with Dynawo 1.8.0):
#  - add_active_power_variation -> Step model expects 'step_step_value' (absent in 1.8.0)
#  - add_disconnection on the load -> load switchOff wiring absent in 1.8.0 network model

ov = dyn.OutputVariableMapping()
ov.add_curves(model_id="B6-G", variables=["generator_PGen", "generator_QGen", "generator_UStatorPu"])

provider = {
    "parametersFile": str(HERE / "models.par"),
    "network.parametersFile": str(HERE / "network.par"),
    "network.parametersId": "Network",
    "solver.parametersFile": str(HERE / "solvers.par"),
    "solver.parametersId": "IDA",
    "solver.type": "IDA",
    "precision": "1e-5",
}
params = dyn.Parameters(start_time=0, stop_time=100, provider_parameters=provider)

rn = rp.ReportNode()
res = dyn.Simulation().run(network, mm, em, ov, params, rn)

status = res.status() if callable(res.status) else res.status
print("STATUS:", status)
print("status_text:", (res.status_text() if callable(res.status_text) else res.status_text) or "(empty)")

curves = res.curves() if callable(res.curves) else res.curves
print("curves shape:", curves.shape, "| cols:", list(curves.columns))
curves.to_csv(HERE / "curves_pypowsybl.csv")
print("saved:", HERE / "curves_pypowsybl.csv")
print(curves.head(3))
print("...")
print(curves.tail(3))
