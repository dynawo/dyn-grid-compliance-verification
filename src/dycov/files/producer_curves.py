#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import configparser
from pathlib import Path

from lxml import etree

from dycov.dynawo.translator import dynawo_translator
from dycov.files.model_parameters import find_bbmodel_by_type
from dycov.logging.logging import dycov_logging


def _get_sm_file_template() -> str:
    return (
        "PCS_RTE-I2.USetPointStep.AReactance = \n"
        "PCS_RTE-I2.USetPointStep.BReactance = \n"
        "PCS_RTE-I3.LineTrip.2BReactance = \n"
        "PCS_RTE-I4.ThreePhaseFault.TransientBolted = \n"
        "PCS_RTE-I6.GridVoltageDip.Qzero = \n"
        "PCS_RTE-I7.GridVoltageSwell.QMax = \n"
        "PCS_RTE-I7.GridVoltageSwell.QMin = \n"
        "PCS_RTE-I8.LoadShedDisturbance.PmaxQzero = \n"
        "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4 = \n"
    )


def _get_sm_curves_template(xfmrs: list, gen_sms: list) -> str:
    curves_dictionary = (
        "[Curves-Dictionary] \n"
        "time =  \n"
        "BusPDR_BUS_Voltage = \n"
        "BusPDR_BUS_ActivePower = \n"
        "BusPDR_BUS_ReactivePower = \n"
    )

    for xfmr in xfmrs:
        curves_dictionary += f"{xfmr.get('id')}_XFMR_Tap = \n"

    for gen_sm in gen_sms:
        curves_dictionary += (
            f"{gen_sm.get('id')}_GEN_RotorSpeedPu = \n"
            f"{gen_sm.get('id')}_GEN_InternalAngle = \n"
            f"{gen_sm.get('id')}_GEN_AVRSetpointPu = \n"
            f"{gen_sm.get('id')}_GEN_MagnitudeControlledByAVRP = \n"
            f"{gen_sm.get('id')}_GEN_NetworkFrequencyPu = \n"
        )

    curves_dictionary += (
        "# To represent a signal that is in raw abc three-phase form, the affected signal must "
        "be tripled \n"
        "# and the suffixes _a, _b and _c must be added as in the following example: \n"
        "#    BusPDR_BUS_Voltage_a = \n"
        "#    BusPDR_BUS_Voltage_b = \n"
        "#    BusPDR_BUS_Voltage_c = \n"
    )
    return curves_dictionary


def _get_ppm_file_template() -> str:
    return (
        "PCS_RTE-I2.USetPointStep.AReactance = \n"
        "PCS_RTE-I2.USetPointStep.BReactance = \n"
        "PCS_RTE-I5.ThreePhaseFault.TransientBolted = \n"
        "PCS_RTE-I6.GridVoltageDip.Qzero = \n"
        "PCS_RTE-I7.GridVoltageSwell.QMax = \n"
        "PCS_RTE-I7.GridVoltageSwell.QMin = \n"
        "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4 = \n"
    )


def _get_bess_file_template() -> str:
    return (
        "PCS_RTE-I2.USetPointStep.AReactanceInjection = \n"
        "PCS_RTE-I2.USetPointStep.BReactanceInjection = \n"
        "PCS_RTE-I2.USetPointStep.AReactanceConsumption= \n"
        "PCS_RTE-I2.USetPointStep.BReactanceConsumption= \n"
        "PCS_RTE-I5.ThreePhaseFault.TransientBoltedInjection = \n"
        "PCS_RTE-I5.ThreePhaseFault.TransientBoltedConsumption= \n"
        "PCS_RTE-I6.GridVoltageDip.QzeroInjection = \n"
        "PCS_RTE-I6.GridVoltageDip.QzeroConsumption= \n"
        "PCS_RTE-I7.GridVoltageSwell.QMaxInjection = \n"
        "PCS_RTE-I7.GridVoltageSwell.QMaxConsumption= \n"
        "PCS_RTE-I7.GridVoltageSwell.QMinInjection = \n"
        "PCS_RTE-I7.GridVoltageSwell.QMinConsumption= \n"
        "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4Injection = \n"
        "PCS_RTE-I10.Islanding.DeltaP10DeltaQ4Consumption= \n"
    )


def _get_ppm_curves_template(xfmrs: list, gen_ppms: list) -> str:

    curves_dictionary = (
        "[Curves-Dictionary] \n"
        "time = \n"
        "BusPDR_BUS_Voltage = \n"
        "BusPDR_BUS_ActivePower = \n"
        "BusPDR_BUS_ReactivePower = \n"
    )

    for xfmr in xfmrs:
        curves_dictionary += f"{xfmr.get('id')}_XFMR_Tap = \n"

    for gen_ppm in gen_ppms:
        curves_dictionary += (
            f"{gen_ppm.get('id')}_GEN_MagnitudeControlledByAVRPu = \n"
            f"{gen_ppm.get('id')}_GEN_AVRSetpointPu = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedActiveCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedReactiveCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedCurrent = \n"
        )

    curves_dictionary += (
        "# To represent a signal that is in raw abc three-phase form, the affected signal must "
        "be tripled \n"
        "# and the suffixes _a, _b and _c must be added as in the following example: \n"
        "#    BusPDR_BUS_Voltage_a = \n"
        "#    BusPDR_BUS_Voltage_b = \n"
        "#    BusPDR_BUS_Voltage_c = \n"
    )
    return curves_dictionary


def _get_model_file_template() -> str:
    return (
        "#Curves for Zone1\n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3 = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10 = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Qmin = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800 = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500 = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.PermanentBolted = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZ = \n"
        "PCS_RTE-I16z1.SetPointStep.Active = \n"
        "PCS_RTE-I16z1.SetPointStep.Reactive = \n"
        "PCS_RTE-I16z1.SetPointStep.Voltage = \n"
        "PCS_RTE-I16z1.GridFreqRamp.W500mHz250ms = \n"
        "PCS_RTE-I16z1.GridVoltageStep.Rise = \n"
        "PCS_RTE-I16z1.GridVoltageStep.Drop = \n"
        "#Curves for Zone3\n"
        "PCS_RTE-I16z3.USetPointStep.AReactance = \n"
        "PCS_RTE-I16z3.USetPointStep.BReactance = \n"
        "PCS_RTE-I16z3.PSetPointStep.Dec40 = \n"
        "PCS_RTE-I16z3.PSetPointStep.Inc40 = \n"
        "PCS_RTE-I16z3.QSetPointStep.Inc10 = \n"
        "PCS_RTE-I16z3.QSetPointStep.Dec20 = \n"
        "PCS_RTE-I16z3.ThreePhaseFault.TransientBolted = \n"
        "PCS_RTE-I16z3.GridVoltageDip.Qzero = \n"
        "PCS_RTE-I16z3.GridVoltageSwell.QMax = \n"
        "PCS_RTE-I16z3.GridVoltageSwell.QMin = \n"
        "PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4 = \n"
    )


def _get_bess_model_file_template() -> str:
    return (
        "#Curves for Zone1\n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Injection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Consumption= \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10Injection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR10Consumption= \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3QminInjection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3QminConsumption= \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800Injection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc800Consumption= \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500Injection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.TransientHiZTc500Consumption= \n"
        "PCS_RTE-I16z1.ThreePhaseFault.PermanentBoltedInjection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.PermanentBoltedConsumption= \n"
        "PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZInjection = \n"
        "PCS_RTE-I16z1.ThreePhaseFault.PermanentHiZConsumption= \n"
        "PCS_RTE-I16z1.SetPointStep.ActiveInjection = \n"
        "PCS_RTE-I16z1.SetPointStep.ActiveConsumption= \n"
        "PCS_RTE-I16z1.SetPointStep.ReactiveInjection = \n"
        "PCS_RTE-I16z1.SetPointStep.ReactiveConsumption= \n"
        "PCS_RTE-I16z1.SetPointStep.VoltageInjection = \n"
        "PCS_RTE-I16z1.SetPointStep.VoltageConsumption= \n"
        "PCS_RTE-I16z1.GridFreqRamp.W500mHz250msInjection = \n"
        "PCS_RTE-I16z1.GridFreqRamp.W500mHz250msConsumption= \n"
        "PCS_RTE-I16z1.GridVoltageStep.RiseInjection = \n"
        "PCS_RTE-I16z1.GridVoltageStep.RiseConsumption= \n"
        "PCS_RTE-I16z1.GridVoltageStep.DropInjection = \n"
        "PCS_RTE-I16z1.GridVoltageStep.DropConsumption= \n"
        "#Curves for Zone3\n"
        "PCS_RTE-I16z3.USetPointStep.AReactanceInjection = \n"
        "PCS_RTE-I16z3.USetPointStep.AReactanceConsumption= \n"
        "PCS_RTE-I16z3.USetPointStep.BReactanceInjection = \n"
        "PCS_RTE-I16z3.USetPointStep.BReactanceConsumption= \n"
        "PCS_RTE-I16z3.PSetPointStep.Dec40Injection = \n"
        "PCS_RTE-I16z3.PSetPointStep.Dec40Consumption= \n"
        "PCS_RTE-I16z3.PSetPointStep.Inc40Injection = \n"
        "PCS_RTE-I16z3.PSetPointStep.Inc40Consumption= \n"
        "PCS_RTE-I16z3.QSetPointStep.Inc10Injection = \n"
        "PCS_RTE-I16z3.QSetPointStep.Inc10Consumption= \n"
        "PCS_RTE-I16z3.QSetPointStep.Dec20Injection = \n"
        "PCS_RTE-I16z3.QSetPointStep.Dec20Consumption= \n"
        "PCS_RTE-I16z3.ThreePhaseFault.TransientBoltedInjection = \n"
        "PCS_RTE-I16z3.ThreePhaseFault.TransientBoltedConsumption= \n"
        "PCS_RTE-I16z3.GridVoltageDip.QzeroInjection = \n"
        "PCS_RTE-I16z3.GridVoltageDip.QzeroConsumption= \n"
        "PCS_RTE-I16z3.GridVoltageSwell.QMaxInjection = \n"
        "PCS_RTE-I16z3.GridVoltageSwell.QMaxConsumption= \n"
        "PCS_RTE-I16z3.GridVoltageSwell.QMinInjection = \n"
        "PCS_RTE-I16z3.GridVoltageSwell.QMinConsumption= \n"
        "PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4Injection = \n"
        "PCS_RTE-I16z3.Islanding.DeltaP10DeltaQ4Consumption= \n"
    )


def _get_model_curves_template(xfmrs: list, z1_gen_ppms: list, z3_gen_ppms: list) -> str:
    curves_dictionary = (
        "[Curves-Dictionary] \n"
        "time = \n"
        "BusPDR_BUS_Voltage = \n"
        "BusPDR_BUS_ActivePower = \n"
        "BusPDR_BUS_ReactivePower = \n"
        "BusPDR_BUS_ActiveCurrent = \n"
        "BusPDR_BUS_ReactiveCurrent = \n"
    )

    for xfmr in xfmrs:
        curves_dictionary += f"{xfmr.get('id')}_XFMR_Tap = \n"

    curves_dictionary += (
        "# To represent a signal that is in raw abc three-phase form, the affected signal must "
        "be tripled \n"
        "# and the suffixes _a, _b and _c must be added as in the following example: \n"
        "#    BusPDR_BUS_Voltage_a = \n"
        "#    BusPDR_BUS_Voltage_b = \n"
        "#    BusPDR_BUS_Voltage_c = \n"
    )

    curves_dictionary += (
        "\n\n# Wind Turbines or PV Arrays in Zone1 \n" "[Curves-Dictionary-Zone1] \n"
    )
    for gen_ppm in z1_gen_ppms:
        curves_dictionary += (
            # Common
            "NetworkFrequencyPu = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedActiveCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedReactiveCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_MagnitudeControlledByAVRPu = \n"
        )

    curves_dictionary += (
        "\n\n# Wind Turbines or PV Arrays in Zone3 \n" "[Curves-Dictionary-Zone3] \n"
    )
    for gen_ppm in z3_gen_ppms:
        curves_dictionary += (
            # Common
            "NetworkFrequencyPu = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedActiveCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedReactiveCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_InjectedCurrent = \n"
            f"{gen_ppm.get('id')}_GEN_MagnitudeControlledByAVRPu = \n"
            # Zone3
            f"{gen_ppm.get('id')}_GEN_AVRSetpointPu = \n"
        )

    return curves_dictionary


def _check_curves(target: Path) -> bool:
    """Checks if all parameters in the INI file have a value defined. Additionally,
    checks if the defined curves files exist.

    Parameters
    ----------
    target: Path
        Target path

    Returns
    -------
    bool
        False if there are empty values in the PAR file
    """

    producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    producer_config.read(target / "CurvesFiles.ini")

    all_declared = True
    exists_files = True
    empty_values = []
    no_files = []
    for key, value in producer_config.items("[Curves-Files]"):
        if value == "":
            empty_values.append(key)
            all_declared = False
        else:
            curves_file = target / value
            if not curves_file.exists():
                no_files.append(value)
                exists_files = False

    if not all_declared:
        dycov_logging.get_logger("Create Curves input").error(
            f"The INI file contains parameters without value.\n" f"Please fix {empty_values}."
        )
    if not exists_files:
        dycov_logging.get_logger("Create Curves input").error(
            f"Not all indicated curve files exist.\n" f"Please fix {no_files}."
        )

    return all_declared and exists_files


def _get_performance_templates(
    model_path: Path,
    template: str,
):
    producer_dyd_tree = etree.parse(
        model_path / "Producer.dyd", etree.XMLParser(remove_blank_text=True)
    )
    producer_dyd_root = producer_dyd_tree.getroot()
    xfmrs = []
    for xfmr in find_bbmodel_by_type(producer_dyd_root, "Transformer"):
        if "StepUp_Xfmr" in xfmr.get("id"):
            xfmrs.append(xfmr)

    if template == "performance_SM":
        gen_sms = []
        for model in dynawo_translator.get_synchronous_machine_models():
            gen_sms.extend(find_bbmodel_by_type(producer_dyd_root, model))
        producer_curves_txt = _get_sm_file_template()
        curves_names_txt = _get_sm_curves_template(xfmrs, gen_sms)
    else:
        gen_ppms = []
        if template == "performance_PPM":
            for model in dynawo_translator.get_power_park_models():
                gen_ppms.extend(find_bbmodel_by_type(producer_dyd_root, model))
            producer_curves_txt = _get_ppm_file_template()
        elif template == "performance_BESS":
            for model in dynawo_translator.get_storage_models():
                gen_ppms.extend(find_bbmodel_by_type(producer_dyd_root, model))
            producer_curves_txt = _get_bess_file_template()
        curves_names_txt = _get_ppm_curves_template(xfmrs, gen_ppms)

    return producer_curves_txt, curves_names_txt


def _get_xmfrs_models(
    model_path: Path,
    zone: str,
) -> list:
    producer_dyd_tree = etree.parse(
        model_path / zone / "Producer.dyd", etree.XMLParser(remove_blank_text=True)
    )
    producer_dyd_root = producer_dyd_tree.getroot()
    xfmrs = []
    for xfmr in find_bbmodel_by_type(producer_dyd_root, "Transformer"):
        if "StepUp_Xfmr" in xfmr.get("id"):
            xfmrs.append(xfmr)

    return xfmrs


def _get_generator_models(
    model_path: Path,
    template: str,
    zone: str,
) -> list:
    producer_dyd_tree = etree.parse(
        model_path / zone / "Producer.dyd", etree.XMLParser(remove_blank_text=True)
    )
    producer_dyd_root = producer_dyd_tree.getroot()

    gen_ppms = []
    if template == "model_PPM":
        for model in dynawo_translator.get_power_park_models():
            gen_ppms.extend(find_bbmodel_by_type(producer_dyd_root, model))
    elif template == "model_BESS":
        for model in dynawo_translator.get_storage_models():
            gen_ppms.extend(find_bbmodel_by_type(producer_dyd_root, model))

    return gen_ppms


def _get_model_templates(
    model_path: Path,
    template: str,
):
    xfmrs = _get_xmfrs_models(model_path, "Zone3")
    z3_gen_ppms = _get_generator_models(model_path, template, "Zone3")
    # TODO: (M-topologies) Copy the zone1 curves files by each zone1 model and modify them
    z1_gen_ppms = _get_generator_models(model_path, template, "Zone1")

    if template == "model_PPM":
        producer_curves_txt = _get_model_file_template()
    elif template == "model_BESS":
        producer_curves_txt = _get_bess_model_file_template()
    curves_names_txt = _get_model_curves_template(xfmrs, z1_gen_ppms, z3_gen_ppms)

    return producer_curves_txt, curves_names_txt


def create_producer_curves(
    model_path: Path,
    curves_path: Path,
    template: str,
) -> None:
    """Create the curves file.

    Parameters
    ----------
    model_path: Path
        Producer model path
    curves_path: Path
        target path
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model
    """

    if template.startswith("performance"):
        producer_curves_txt, curves_names_txt = _get_performance_templates(model_path, template)
    elif template.startswith("model"):
        producer_curves_txt, curves_names_txt = _get_model_templates(model_path, template)
    else:
        producer_curves_txt = ""
        curves_names_txt = ""

    with open(curves_path / "CurvesFiles.ini", "w") as f:
        f.write("[Curves-Files]\n")
        f.write(producer_curves_txt)
        f.write("\n\n")
        f.write(curves_names_txt)


def check_curves(target: Path) -> bool:
    """Checks if all parameters in the INI file have a value defined. Additionally,
    checks if the defined curves files exist.

    Parameters
    ----------
    target: Path
        Target path

    Returns
    -------
    bool
        False if there are empty values in the PAR file
    """

    producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    producer_config.read(target / "CurvesFiles.ini")

    all_declared = True
    exists_files = True
    empty_values = []
    no_files = []
    for key, value in producer_config.items("Curves-Files"):
        if value == "":
            empty_values.append(key)
            all_declared = False
        else:
            curves_file = target / value
            if not curves_file.exists():
                no_files.append(value)
                exists_files = False

    if not all_declared:
        dycov_logging.get_logger("Create Curves input").error(
            f"The INI file contains parameters without value.\n" f"Please fix {empty_values}."
        )
    if not exists_files:
        dycov_logging.get_logger("Create Curves input").error(
            f"Not all indicated curve files exist.\n" f"Please fix {no_files}."
        )

    return all_declared and exists_files
