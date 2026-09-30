#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the post-processing of the curves Dynawo writes into the curves the tool compares."""

import numpy as np
import pandas as pd
import pytest

from dycov.curves.dynawo.runtime import _curves as curves_module
from dycov.curves.dynawo.runtime._curves import (
    ABS_TOLERANCE_FACTOR,
    VOLTAGE_DIP_THRESHOLD,
    _get_injector_terminal_curves,
    _get_magnitude_controlled_by_avr,
    _get_modulus,
    convert_columns,
    create_curves,
    prepare_complex_column,
    report_unserved_requests,
    translate_curves,
)

_PDR_TRANSLATIONS = {
    "BusPDR_BUS_Voltage": ["BusPDR_BUS_Voltage"],
    "BusPDR_BUS_ActivePower": ["BusPDR_BUS_ActivePower"],
    "BusPDR_BUS_ReactivePower": ["BusPDR_BUS_ReactivePower"],
}

_TERMINAL_POWER_REQUEST = {
    "Gen_injector_PInjPu": ["Gen_GEN_ActivePowerInjTerminal"],
    "Gen_GEN_ActivePowerInjTerminal": 1,
    "Gen_injector_QInjPu": ["Gen_GEN_ReactivePowerInjTerminal"],
    "Gen_GEN_ReactivePowerInjTerminal": 1,
}

_TERMINAL_AMPLITUDE_REQUEST = {
    "Gen_injector_UPu": ["Gen_GEN_VoltageInjTerminal"],
    "Gen_GEN_VoltageInjTerminal": 1,
}

_TERMINAL_COMPONENTS_REQUEST = {
    "Gen_injector_terminal_V_re": ["Gen_GEN_VoltageInjTerminalRe"],
    "Gen_GEN_VoltageInjTerminalRe": 1,
    "Gen_injector_terminal_V_im": ["Gen_GEN_VoltageInjTerminalIm"],
    "Gen_GEN_VoltageInjTerminalIm": 1,
}


class DummyGenerator:
    def __init__(self, id_, use_voltage_droop=False, voltage_droop=0.0):
        self.id = id_
        self.use_voltage_droop = use_voltage_droop
        self.voltage_droop = voltage_droop


class RecordingLogger:
    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)


@pytest.fixture
def recorded_warnings(monkeypatch):
    logger = RecordingLogger()
    monkeypatch.setattr(curves_module.dycov_logging, "get_logger", lambda name: logger)
    return logger.messages


def _injector_terminal_curves(voltage_request: dict, voltage_columns: dict) -> dict:
    """The InternalNode2 curves the tool emits for a unit whose terminal voltage Dynawo writes in
    the columns given, asked for as the request declares."""
    df_curves_imported = pd.DataFrame(
        {
            "time": [0.0, 1.0],
            "Gen_injector_PInjPu": [0.5, 0.25],
            "Gen_injector_QInjPu": [0.25, -0.1],
            **voltage_columns,
        }
    )
    df_curves = translate_curves(
        {**_TERMINAL_POWER_REQUEST, **voltage_request}, df_curves_imported
    )

    curves_dict = {}
    _get_injector_terminal_curves(100.0, 100.0, [DummyGenerator("Gen")], df_curves, curves_dict)
    return curves_dict


# ---------------------------------------------------------------------------
# Curve creation
# ---------------------------------------------------------------------------


def test_create_curves_raises_on_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_curves(_PDR_TRANSLATIONS, tmp_path / "missing.csv", [], 1.0, 1.0, 50.0)


def test_create_curves_raises_on_a_file_without_time(recorded_warnings, tmp_path):
    malformed_file = tmp_path / "malformed.csv"
    malformed_file.write_text("not,a,valid,csv\n1,2,3\n")

    with pytest.raises(KeyError, match="time"):
        create_curves(_PDR_TRANSLATIONS, malformed_file, [], 1.0, 1.0, 50.0)


def test_create_curves_divides_the_pdr_powers_by_the_pdr_voltage(monkeypatch, tmp_path):
    input_file = tmp_path / "curves.csv"
    input_file.write_text("time;\n0.0;\n1.0;\n2.0;\n")
    translated = pd.DataFrame(
        {
            "Measurements_BUS_Voltage": [1.0, 0.5, 1.0],
            "Measurements_BUS_ActivePower": [0.5, 0.5, 0.5],
            "Measurements_BUS_ReactivePower": [0.3, 0.3, 0.3],
        }
    )
    monkeypatch.setattr(curves_module, "translate_curves", lambda *args: translated)

    result = create_curves({}, input_file, [], 100.0, 100.0, 50.0)

    assert result["time"].tolist() == [0.0, 1.0, 2.0]
    assert result["BusPDR_BUS_ActiveCurrent"].tolist() == pytest.approx([0.5, 1.0, 0.5])
    assert result["BusPDR_BUS_ReactiveCurrent"].tolist() == pytest.approx([0.3, 0.6, 0.3])


def test_convert_columns_emits_the_amplitude_of_a_complex_curve():
    df_curves = pd.DataFrame({"SomeComplex": np.array([3 + 4j, 5 + 12j], dtype=np.complex128)})
    curves_dict = {}

    convert_columns(df_curves, curves_dict, 50.0)

    assert curves_dict["SomeComplex"] == pytest.approx([5.0, 13.0])


# ---------------------------------------------------------------------------
# Translation of the Dynawo columns
# ---------------------------------------------------------------------------


def test_prepare_complex_column_applies_sign_conventions():
    df_curves = pd.DataFrame(
        {
            "test_columnre": [1.0, 2.0, 3.0],
            "test_columnim": [4.0, 5.0, 6.0],
        }
    )
    variable_translations = {
        "translated_testRe": -1,
        "translated_testIm": 2,
    }

    result = prepare_complex_column(
        "test_column", 3, df_curves, "translated_test", variable_translations
    )

    complex_result = np.array(result, dtype=np.complex128)
    assert complex_result.real == pytest.approx([-1.0, -2.0, -3.0])
    assert complex_result.imag == pytest.approx([8.0, 10.0, 12.0])


def test_translate_curves_skips_the_columns_dynawo_did_not_write():
    df_curves_imported = pd.DataFrame(
        {"time": [0.0, 1.0, 2.0], "existing_column": [1.0, 2.0, 3.0]}
    )
    variable_translations = {
        "existing_column": ["translated_existing"],
        "missing_column_re": ["missing_translated_Re"],
        "missing_column_im": ["missing_translated_Im"],
        "translated_existing": 1,
    }

    result_df = translate_curves(variable_translations, df_curves_imported)

    assert list(result_df.columns) == ["time", "translated_existing"]
    assert result_df["translated_existing"].tolist() == pytest.approx([1.0, 2.0, 3.0])


def test_translate_curves_names_a_complex_curve_after_its_components():
    df_curves_imported = pd.DataFrame(
        {
            "time": [0.0, 1.0],
            "Gen_injector_terminal_V_re": [0.6, 0.3],
            "Gen_injector_terminal_V_im": [0.8, -0.4],
        }
    )

    result_df = translate_curves(_TERMINAL_COMPONENTS_REQUEST, df_curves_imported)

    assert list(result_df.columns) == ["time", "Gen_GEN_VoltageInjTerminal"]
    assert result_df["Gen_GEN_VoltageInjTerminal"].tolist() == pytest.approx(
        [complex(0.6, 0.8), complex(0.3, -0.4)]
    )


# ---------------------------------------------------------------------------
# Magnitude controlled by the AVR
# ---------------------------------------------------------------------------


def test_get_magnitude_controlled_by_avr_takes_or_composes_the_magnitude():
    generators = [
        DummyGenerator("GEN1", use_voltage_droop=True, voltage_droop=0.1),
        DummyGenerator("GEN2", use_voltage_droop=True, voltage_droop=0.1),
        DummyGenerator("GEN3", use_voltage_droop=True, voltage_droop=0.1),
    ]
    df_curves = pd.DataFrame(
        {
            "GEN1_GEN_MagnitudeControlledByAVRPu": [0.1, 0.2, 0.3],
            "GEN2_GEN_MagnitudeControlledByAVRPu": [0.4, 0.5, 0.6],
            "GEN3_GEN_MagnitudeControlledByAVRUPu": [0.2, 0.3, 0.4],
            "GEN3_GEN_MagnitudeControlledByAVRQPu": [0.2, 0.1, 0.2],
            "OtherColumn": [1.0, 2.0, 3.0],
        }
    )
    curves_dict = {}

    _get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)

    assert curves_dict["GEN1_GEN_MagnitudeControlledByAVRPu"] == [0.1, 0.2, 0.3]
    assert curves_dict["GEN2_GEN_MagnitudeControlledByAVRPu"] == [0.4, 0.5, 0.6]
    assert curves_dict["GEN3_GEN_MagnitudeControlledByAVRPu"] == pytest.approx([0.22, 0.31, 0.42])
    assert list(df_curves.columns) == ["OtherColumn"]


def test_get_magnitude_controlled_by_avr_without_generators():
    df_curves = pd.DataFrame({"OtherColumn1": [1.0, 2.0, 3.0], "OtherColumn2": [4.0, 5.0, 6.0]})
    original_df = df_curves.copy()
    curves_dict = {}

    _get_magnitude_controlled_by_avr([], df_curves, curves_dict)

    assert curves_dict == {}
    assert df_curves.equals(original_df)


# ---------------------------------------------------------------------------
# Injector terminal
# ---------------------------------------------------------------------------


def test_get_modulus_correct_calculation():
    result = _get_modulus([complex(3, 4), complex(5, 12)])

    assert result == [5.0, 13.0]


def test_injector_terminal_currents_divided_by_terminal_voltage():
    df_curves = pd.DataFrame(
        {
            "GEN1_GEN_VoltageInjTerminal": [complex(0.8, 0.6), complex(0.5, 0.0)],
            "GEN1_GEN_ActivePowerInjTerminal": [0.5, 1.0],
            "GEN1_GEN_ReactivePowerInjTerminal": [0.25, 0.5],
        }
    )
    curves_dict = {}

    _get_injector_terminal_curves(90.0, 45.0, [DummyGenerator("GEN1")], df_curves, curves_dict)

    assert curves_dict["GEN1_GEN_VoltageInjTerminal"] == pytest.approx([1.0, 0.5])
    assert curves_dict["GEN1_GEN_ActiveCurrentInjTerminal"] == pytest.approx([1.0, 4.0])
    assert curves_dict["GEN1_GEN_ReactiveCurrentInjTerminal"] == pytest.approx([0.5, 2.0])
    assert df_curves.columns.empty


def test_the_injector_currents_are_emitted_under_their_own_name():
    df_curves = pd.DataFrame(
        {
            "GEN1_GEN_VoltageInjTerminal": [complex(1.0, 0.0)],
            "GEN1_GEN_ActivePowerInjTerminal": [1.0],
            "GEN1_GEN_ReactivePowerInjTerminal": [0.5],
        }
    )
    curves_dict = {}

    _get_injector_terminal_curves(100.0, 100.0, [DummyGenerator("GEN1")], df_curves, curves_dict)

    assert "GEN1_GEN_ActiveCurrentInjTerminal" in curves_dict
    assert "GEN1_GEN_ReactiveCurrentInjTerminal" in curves_dict
    assert "GEN1_GEN_ActivePowerInjTerminal" not in curves_dict
    assert "GEN1_GEN_ReactivePowerInjTerminal" not in curves_dict


def test_injector_terminal_currents_divide_however_small_the_voltage_is():
    df_curves = pd.DataFrame(
        {
            "GEN1_GEN_VoltageInjTerminal": [complex(1e-6, 0.0), complex(1.0, 0.0)],
            "GEN1_GEN_ActivePowerInjTerminal": [1e-6, 1.0],
            "GEN1_GEN_ReactivePowerInjTerminal": [5e-7, 0.5],
        }
    )
    curves_dict = {}

    _get_injector_terminal_curves(100.0, 100.0, [DummyGenerator("GEN1")], df_curves, curves_dict)

    assert curves_dict["GEN1_GEN_ActiveCurrentInjTerminal"] == pytest.approx([1.0, 1.0])
    assert curves_dict["GEN1_GEN_ReactiveCurrentInjTerminal"] == pytest.approx([0.5, 0.5])


def test_injector_terminal_currents_are_zero_only_where_the_voltage_is():
    df_curves = pd.DataFrame(
        {
            "GEN1_GEN_VoltageInjTerminal": [complex(0.0, 0.0), complex(1.0, 0.0)],
            "GEN1_GEN_ActivePowerInjTerminal": [1.0, 1.0],
            "GEN1_GEN_ReactivePowerInjTerminal": [0.5, 0.5],
        }
    )
    curves_dict = {}

    _get_injector_terminal_curves(100.0, 100.0, [DummyGenerator("GEN1")], df_curves, curves_dict)

    assert curves_dict["GEN1_GEN_ActiveCurrentInjTerminal"] == pytest.approx([0.0, 1.0])
    assert curves_dict["GEN1_GEN_ReactiveCurrentInjTerminal"] == pytest.approx([0.0, 0.5])


def test_injector_terminal_curves_skip_a_unit_without_all_its_terminal_curves():
    df_curves = pd.DataFrame(
        {
            "GEN1_GEN_VoltageInjTerminal": [1.0],
            "GEN1_GEN_ActivePowerInjTerminal": [1.0],
        }
    )
    curves_dict = {}

    _get_injector_terminal_curves(100.0, 100.0, [DummyGenerator("GEN1")], df_curves, curves_dict)

    assert curves_dict == {}
    assert list(df_curves.columns) == [
        "GEN1_GEN_VoltageInjTerminal",
        "GEN1_GEN_ActivePowerInjTerminal",
    ]


def test_the_injector_currents_divide_by_the_amplitude_dynawo_publishes():
    """#555: an amplitude is read as it is, without the sign conventions of components the
    model does not publish."""
    curves = _injector_terminal_curves(
        _TERMINAL_AMPLITUDE_REQUEST, {"Gen_injector_UPu": [1.0, 0.5]}
    )

    assert curves["Gen_GEN_VoltageInjTerminal"] == pytest.approx([1.0, 0.5])
    assert curves["Gen_GEN_ActiveCurrentInjTerminal"] == pytest.approx([0.5, 0.5])
    assert curves["Gen_GEN_ReactiveCurrentInjTerminal"] == pytest.approx([0.25, -0.2])


def test_the_injector_curves_are_the_same_from_the_amplitude_or_from_the_components():
    """#555: a model declares the voltage at InternalNode2 in either form, and the curves the
    tool emits do not depend on which."""
    from_amplitude = _injector_terminal_curves(
        _TERMINAL_AMPLITUDE_REQUEST, {"Gen_injector_UPu": [1.0, 0.5]}
    )
    from_components = _injector_terminal_curves(
        _TERMINAL_COMPONENTS_REQUEST,
        {"Gen_injector_terminal_V_re": [0.6, 0.3], "Gen_injector_terminal_V_im": [0.8, -0.4]},
    )

    assert from_components.keys() == from_amplitude.keys()
    assert pd.DataFrame(from_components).to_numpy() == pytest.approx(
        pd.DataFrame(from_amplitude).to_numpy()
    )


def test_voltage_guard_matches_documented_value():
    assert ABS_TOLERANCE_FACTOR * VOLTAGE_DIP_THRESHOLD == pytest.approx(2e-4)


# ---------------------------------------------------------------------------
# Unserved requests
# ---------------------------------------------------------------------------


def test_a_request_dynawo_did_not_serve_is_warned_with_the_curves_it_feeds(recorded_warnings):
    variable_translations = {
        "Main_Xfmr_transformer_tap": ["Main_Xfmr_XFMR_Tap"],
        "Main_Xfmr_XFMR_Tap": 1,
    }
    df_curves_imported = pd.DataFrame({"time": [0.0, 1.0]})

    report_unserved_requests(variable_translations, df_curves_imported)

    assert recorded_warnings == [
        "Dynawo did not provide the requested curves: "
        "Main_Xfmr_transformer_tap (Main_Xfmr_XFMR_Tap)"
    ]


def test_every_unserved_request_is_named_in_a_single_warning(recorded_warnings):
    variable_translations = {
        "InfiniteBus_infiniteBus_omegaRefPu": ["InfiniteBus_BUS_NetworkFrequencyPu"],
        "Main_Xfmr_transformer_tap": ["Main_Xfmr_XFMR_Tap"],
    }
    df_curves_imported = pd.DataFrame({"time": [0.0, 1.0]})

    report_unserved_requests(variable_translations, df_curves_imported)

    assert recorded_warnings == [
        "Dynawo did not provide the requested curves: "
        "InfiniteBus_infiniteBus_omegaRefPu (InfiniteBus_BUS_NetworkFrequencyPu), "
        "Main_Xfmr_transformer_tap (Main_Xfmr_XFMR_Tap)"
    ]


def test_a_served_request_is_not_warned_about(recorded_warnings):
    variable_translations = {
        "Measurements_measurements_UPu": ["BusPDR_BUS_Voltage"],
        "BusPDR_BUS_Voltage": 1,
    }
    df_curves_imported = pd.DataFrame(
        {"time": [0.0, 1.0], "Measurements_measurements_UPu": [1.0, 1.0]}
    )

    report_unserved_requests(variable_translations, df_curves_imported)

    assert recorded_warnings == []


def test_a_sign_convention_entry_is_not_taken_for_a_request(recorded_warnings):
    variable_translations = {"BusPDR_BUS_Voltage": 1, "BusPDR_BUS_ActivePower": -1}
    df_curves_imported = pd.DataFrame({"time": [0.0, 1.0]})

    report_unserved_requests(variable_translations, df_curves_imported)

    assert recorded_warnings == []


def test_create_curves_reports_the_requests_dynawo_did_not_serve(
    monkeypatch, recorded_warnings, tmp_path
):
    input_file = tmp_path / "curves.csv"
    input_file.write_text("time;Measurements_measurements_UPu\n0.0;1.0\n1.0;1.0\n")
    variable_translations = {
        "Measurements_measurements_UPu": ["BusPDR_BUS_Voltage"],
        "BusPDR_BUS_Voltage": 1,
        "Main_Xfmr_transformer_tap": ["Main_Xfmr_XFMR_Tap"],
    }
    monkeypatch.setattr(
        curves_module, "build_output_curves", lambda *args, **kwargs: pd.DataFrame()
    )

    create_curves(variable_translations, input_file, [], 100.0, 100.0, 50.0)

    assert recorded_warnings == [
        "Dynawo did not provide the requested curves: "
        "Main_Xfmr_transformer_tap (Main_Xfmr_XFMR_Tap)"
    ]
