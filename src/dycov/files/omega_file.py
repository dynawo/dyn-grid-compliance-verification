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

from dycov.curves.dynawo.translator import dynawo_translator
from dycov.model.parameters import Gen_params


def _connect_generator_by_lib(
    dyd_root: etree.Element, ns: str, omega_lib, generator: Gen_params, grp: str
) -> None:
    if omega_lib is None:
        _connect_generator_to_infinitebus(dyd_root, ns, generator)
    elif "DYNModelOmegaRef" == omega_lib:
        _connect_generator_to_dynmodelomegaref(dyd_root, ns, generator, grp)
    elif "SetPoint" == omega_lib:
        _connect_generator_to_setpoint(dyd_root, ns, generator)


def _connect_generator_to_dynmodelomegaref(
    dyd_root: etree.Element, ns: str, generator: Gen_params, grp: str
) -> None:
    _, variable = dynawo_translator.get_dynawo_variable(generator.lib, "RotorSpeedPu")
    _connect_generator(dyd_root, ns, generator.id, variable, "OmegaRef", f"omega_grp_{grp}_value")

    _, variable = dynawo_translator.get_dynawo_variable(generator.lib, "NetworkFrequencyPu")
    _connect_generator(
        dyd_root, ns, generator.id, variable, "OmegaRef", f"omegaRef_grp_{grp}_value"
    )

    _, variable = dynawo_translator.get_dynawo_variable(generator.lib, "Running")
    _connect_generator(dyd_root, ns, generator.id, variable, "OmegaRef", f"running_grp_{grp}")


def _connect_generator_to_setpoint(
    dyd_root: etree.Element, ns: str, generator: Gen_params
) -> None:
    _, variable = dynawo_translator.get_dynawo_variable(generator.lib, "NetworkFrequencyValue")
    if variable:
        _connect_generator(
            dyd_root, ns, generator.id, variable, "OmegaRef", "setPoint_setPoint_value"
        )


def _connect_generator_to_infinitebus(
    dyd_root: etree.Element, ns: str, generator: Gen_params
) -> None:
    _, variable = dynawo_translator.get_dynawo_variable(generator.lib, "NetworkFrequencyPu")
    _connect_generator(
        dyd_root, ns, generator.id, variable, "InfiniteBus", "infiniteBus_omegaRefPu"
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


def _add_generator_weight(parset: etree.Element, ns: str, grp: str) -> int:
    if grp is None:
        return grp

    parset.append(
        etree.Element(
            f"{{{ns}}}par",
            type="DOUBLE",
            name=f"weight_gen_{grp}",
            value="1e-16",
        )
    )

    return grp + 1


def complete_omega(
    path: Path,
    dyd_file: str,
    par_file: str,
    generators: list,
) -> None:
    """Replace DYD/PAR Omega files placeholders with values.

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
    """
    dyd_tree = etree.parse(path / dyd_file, etree.XMLParser(remove_blank_text=True))
    dyd_root = dyd_tree.getroot()
    dyd_ns = etree.QName(dyd_root).namespace

    par_tree = etree.parse(path / par_file, etree.XMLParser(remove_blank_text=True))
    par_root = par_tree.getroot()
    par_ns = etree.QName(dyd_root).namespace

    lib = None
    parset = None
    grp = None
    omega_ref = dyd_root.find(f"{{{dyd_ns}}}blackBoxModel[@id='OmegaRef']")
    if omega_ref is not None:
        lib = omega_ref.get("lib")
        par_id = omega_ref.get("parId")
        parset = par_root.find(f"{{{par_ns}}}set[@id='{par_id}']")
        nbGen = parset.find(f"{{{par_ns}}}par[@name='nbGen']")
        if nbGen is not None:
            grp = int(nbGen.get("value"))

    for generator in generators:
        _connect_generator_by_lib(dyd_root, dyd_ns, lib, generator, grp)
        grp = _add_generator_weight(parset, par_ns, grp)

    if grp:
        nbGen.set("value", str(grp))

    par_tree.write(path / par_file, pretty_print=True)
    dyd_tree.write(path / dyd_file, pretty_print=True)
