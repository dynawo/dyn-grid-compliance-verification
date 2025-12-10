#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from pathlib import Path

from lxml import etree

from dycov.curves.dynawo.dictionary.translator import dynawo_translator
from dycov.model.parameters import Gen_params


def _connect_generator_to_setpoint(
    dyd_root: etree.Element, ns: str, generator: Gen_params, connect_to: str
) -> int:
    setpoint_id = f"SetPoint_{generator.id}"
    _create_model(dyd_root, ns, setpoint_id, "Step", "TSOModel.par", setpoint_id)
    sign, connect_event_to = dynawo_translator.get_dynawo_variable(generator.lib, connect_to)
    _connect_generator(dyd_root, ns, generator.id, connect_event_to, setpoint_id, "step_step")
    return sign


def _create_model(
    dyd_root: etree.Element, ns: str, id: str, lib: str, par_file: str, par_id: str
) -> None:
    dyd_root.append(
        etree.Element(
            f"{{{ns}}}blackBoxModel",
            id=f"{id}",
            lib=f"{lib}",
            parFile=f"{par_file}",
            parId=f"{par_id}",
        )
    )


def _connect_generator(
    dyd_root: etree.Element, ns: str, id1: str, var1: str, id2: str, var2: str
) -> None:
    dyd_root.append(
        etree.Element(
            f"{{{ns}}}connect",
            id1=f"{id1}",
            var1=f"{var1}",
            id2=f"{id2}",
            var2=f"{var2}",
        )
    )


def _add_setpoint_parameters(
    par_root: etree.Element,
    ns: str,
    generator: Gen_params,
    event_params: dict,
    pre_value: float,
    step_value: float,
) -> None:
    parset = etree.SubElement(
        par_root,
        f"{{{ns}}}set",
        id=f"SetPoint_{generator.id}",
    )
    parset.append(
        etree.Element(
            f"{{{ns}}}par",
            type="DOUBLE",
            name="step_tStep",
            value=f"{event_params['start_time']}",
        )
    )
    parset.append(
        etree.Element(
            f"{{{ns}}}par",
            type="DOUBLE",
            name="step_Value0",
            value=f"{pre_value}",
        )
    )
    parset.append(
        etree.Element(
            f"{{{ns}}}par",
            type="DOUBLE",
            name="step_Height",
            value=f"{step_value}",
        )
    )


def complete_setpoint(
    path: Path,
    dyd_file: str,
    par_file: str,
    generators: list,
    tso_model: str,
    event_params: dict,
) -> None:
    """Replace DYD/PAR TSOModel files placeholders with values.

    Parameters
    ----------
    path: Path
        Path where the omega files are stored
    dyd_file: str
        DYD filename
    par_file: str
        PAR filename
    generators: list
        Variable where the step is connected
    tso_model: str
        TSO Model library name
    event_params: dict
        Event parameters
    """
    if tso_model != "RefTracking_1Line_InfBus":
        return

    dyd_tree = etree.parse(path / dyd_file, etree.XMLParser(remove_blank_text=True))
    dyd_root = dyd_tree.getroot()
    dyd_ns = etree.QName(dyd_root).namespace

    par_tree = etree.parse(path / par_file, etree.XMLParser(remove_blank_text=True))
    par_root = par_tree.getroot()
    par_ns = etree.QName(dyd_root).namespace

    for i in range(len(generators)):
        generator = generators[i]
        sign = _connect_generator_to_setpoint(
            dyd_root, dyd_ns, generator, event_params["connect_to"]
        )
        pre_value = event_params["pre_value"][i]
        step_value = event_params["step_value"] * sign
        _add_setpoint_parameters(par_root, par_ns, generator, event_params, pre_value, step_value)

    par_tree.write(path / par_file, pretty_print=True)
    dyd_tree.write(path / dyd_file, pretty_print=True)
