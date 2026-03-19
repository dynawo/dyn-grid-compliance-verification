#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import numpy as np
import pandas as pd
import pytest

from dycov.curves.dynawo.runtime._curves import (
    create_curves,
    get_magnitude_controlled_by_avr,
    prepare_complex_column,
    translate_curves,
)
from dycov.curves.dynawo.runtime.dynawo_simulator import TrimmedCurves


def patch_dycov_logging(monkeypatch):
    class _DummyLogger:
        def __init__(self):
            self.messages = []

        def debug(self, msg):
            self.messages.append(("debug", msg))

        def info(self, msg):
            self.messages.append(("info", msg))

        def error(self, msg):
            self.messages.append(("error", msg))

    dummy = _DummyLogger()

    def _get_logger(_name):
        return dummy

    monkeypatch.setattr(
        "dycov.logging.logging.dycov_logging.get_logger",
        _get_logger,
        raising=True,
    )
    return dummy


@pytest.fixture(autouse=True)
def _no_leak_patches(mocker):
    yield
    try:
        mocker.stopall()
    except Exception:
        pass


# -------------------------------------------------------------------
# BASIC TESTS
# -------------------------------------------------------------------


def test_is_stable_raises_on_length_mismatch():
    from dycov.validation.common import is_stable

    time = [0.0, 0.1, 0.2]
    curve = [1.0, 1.1]
    stable_time = 0.1

    with pytest.raises(ValueError) as excinfo:
        is_stable(time, curve, stable_time)

    assert "different length" in str(excinfo.value)


# -------------------------------------------------------------------
# CURVE CREATION TESTS
# -------------------------------------------------------------------


def test_create_curves_handles_missing_or_malformed_file(tmp_path):

    variable_translations = {
        "BusPDR_BUS_Voltage": ["BusPDR_BUS_Voltage"],
        "BusPDR_BUS_ActivePower": ["BusPDR_BUS_ActivePower"],
        "BusPDR_BUS_ReactivePower": ["BusPDR_BUS_ReactivePower"],
        "time": ["time"],
    }

    class DummyGen:
        id = "G1"
        UseVoltageDroop = False

    generators = [DummyGen()]
    snom = 1.0
    snref = 1.0
    fnom = 50.0

    # Case 1: Missing file
    missing_file = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        create_curves(variable_translations, missing_file, generators, snom, snref, fnom)

    # Case 2: Malformed file
    malformed_file = tmp_path / "malformed.csv"
    with open(malformed_file, "w") as f:
        f.write("not,a,valid,csv\n1,2,3\n")

    with pytest.raises(Exception):
        create_curves(variable_translations, malformed_file, generators, snom, snref, fnom)


# -------------------------------------------------------------------
# VOLTAGE DIP TESTS
# -------------------------------------------------------------------


def test_voltage_dip_equals_expected_dip_within_tolerance(mocker):
    from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator

    curves = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8],
        }
    )

    fault_start = 0.15
    fault_duration = 0.3
    expected_dip = 0.2

    mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo_simulator.DynawoSimulator._trim_curves",
        return_value=TrimmedCurves(
            pre_time=[0.0, 0.1],  # pre_time_values
            post_time=[0.2, 0.3, 0.4, 0.5],  # post_time_values
            pre_voltage=[1.0, 1.0],  # pre_voltage_values
            post_voltage=[0.8, 0.8, 0.8, 0.8],  # post_voltage_values
        ),
    )

    mock_is_stable = mocker.patch("dycov.validation.common.is_stable")
    mock_is_stable.side_effect = [(True, 0), (True, 0)]

    mock_logger = mocker.MagicMock()
    mocker.patch("dycov.logging.logging.dycov_logging.get_logger", return_value=mock_logger)

    result = DynawoSimulator().classify_voltage_dip(
        "PCS", "BM", "OC", curves, fault_start, fault_duration, expected_dip
    )

    assert result == 0


def test_fault_duration_exceeds_simulation_time(mocker):
    from pytest import approx

    from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator

    curves = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8],
        }
    )

    fault_start = 0.2
    fault_duration = 1.0
    expected_dip = 0.2

    mock_trim = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo_simulator.DynawoSimulator._trim_curves",
        return_value=TrimmedCurves(
            pre_time=[0.0, 0.1],
            post_time=[0.2, 0.3, 0.4, 0.5],
            pre_voltage=[1.0, 1.0],
            post_voltage=[0.8, 0.8, 0.8, 0.8],
        ),
    )

    mock_is_stable = mocker.patch("dycov.validation.common.is_stable")
    mock_is_stable.side_effect = [(True, 0), (True, 0)]

    mock_logger = mocker.MagicMock()
    mocker.patch("dycov.logging.logging.dycov_logging.get_logger", return_value=mock_logger)

    result = DynawoSimulator().classify_voltage_dip(
        "PCS", "BM", "OC", curves, fault_start, fault_duration, expected_dip
    )

    mock_trim.assert_called_once()
    args, kwargs = mock_trim.call_args

    assert args[0] == curves["time"].tolist()
    assert args[1] == curves["BusPDR_BUS_Voltage"].tolist()
    assert args[2] == fault_start
    assert args[3] == approx(0.5 - fault_start)

    assert result == 0


def test_correct_identification_of_pre_and_post_fault_values():
    from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator

    time_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    voltage_values = [1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.6, 0.8, 0.9, 1.0, 1.0]

    fault_start = 0.4
    fault_duration = 0.4

    pre_time, post_time, pre_voltage, post_voltage = DynawoSimulator()._trim_curves(
        time_values, voltage_values, fault_start, fault_duration
    )

    assert pre_time == [0.0, 0.1, 0.2, 0.3]
    assert pre_voltage == [1.0, 1.0, 1.0, 0.8]
    assert post_time == [0.4, 0.5, 0.6, 0.7]
    assert post_voltage == [0.6, 0.4, 0.6, 0.8]


def test_empty_input_lists():
    from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoSimulator

    time_values = []
    voltage_values = []

    fault_start = 0.3
    fault_duration = 0.4

    pre_time, post_time, pre_voltage, post_voltage = DynawoSimulator()._trim_curves(
        time_values, voltage_values, fault_start, fault_duration
    )

    assert pre_time == []
    assert post_time == []
    assert pre_voltage == []
    assert post_voltage == []


# -------------------------------------------------------------------
# CURVE PROCESSING TESTS
# -------------------------------------------------------------------


def test_valid_input_file_processing(mocker, tmp_path):

    mock_df_import = pd.DataFrame({"time": [0.0, 1.0, 2.0], "Unnamed: 0": [0, 1, 2]})
    mocker.patch("pandas.read_csv", return_value=mock_df_import)

    translated_df = pd.DataFrame(
        {
            "Measurements_BUS_Voltage": [1.0, 1.0, 1.0],
            "Measurements_BUS_ActivePower": [0.5, 0.5, 0.5],
            "Measurements_BUS_ReactivePower": [0.3, 0.3, 0.3],
            "GEN1_GEN_MagnitudeControlledByAVRUPu": [0.2, 0.2, 0.2],
            "GEN1_GEN_MagnitudeControlledByAVRQPu": [0.1, 0.0, -0.1],
            "SomeComplex": np.array([1 + 1j, 1 + 2j, 2 + 2j], dtype=np.complex128),
        }
    )

    mock_translate = mocker.patch(
        "dycov.curves.dynawo.runtime._curves.translate_curves",
        return_value=translated_df,
    )

    class Gen:
        def __init__(self):
            self.id = "GEN1"
            self.use_voltage_droop = True
            self.voltage_droop = 0.1

    generators = [Gen()]
    snom = 100.0
    snref = 100.0
    fnom = 50.0

    result = create_curves(
        variable_translations={"x": ["y"]},
        input_file=tmp_path / "dummy.csv",
        generators=generators,
        s_nom=snom,
        s_nref=snref,
        f_nom=fnom,
    )

    assert isinstance(result, pd.DataFrame)

    for col in [
        "BusPDR_BUS_Voltage",
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
    ]:
        assert col in result.columns

    assert result["BusPDR_BUS_ActiveCurrent"].tolist() == [0.5, 0.5, 0.5]
    assert result["BusPDR_BUS_ReactiveCurrent"].tolist() == [0.3, 0.3, 0.3]

    assert "GEN1_GEN_MagnitudeControlledByAVRPu" in result.columns

    mock_translate.assert_called_once()


def test_prepare_complex_column_applies_sign_conventions():

    column_name = "test_column"
    column_size = 3

    df_curves = pd.DataFrame(
        {
            "test_columnre": [1.0, 2.0, 3.0],
            "test_columnim": [4.0, 5.0, 6.0],
        }
    )

    translated_column = "translated_test"

    variable_translations = {
        "translated_testRe": -1,
        "translated_testIm": 2,
    }

    result = prepare_complex_column(
        column_name, column_size, df_curves, translated_column, variable_translations
    )

    expected_real = [-1.0, -2.0, -3.0]
    expected_imag = [8.0, 10.0, 12.0]

    complex_result = np.array(result, dtype=np.complex128)

    np.testing.assert_almost_equal(complex_result.real, expected_real)
    np.testing.assert_almost_equal(complex_result.imag, expected_imag)


def test_translate_curves_with_missing_columns():

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

    assert "time" in result_df.columns
    assert "translated_existing" in result_df.columns
    assert "missing_translated" not in result_df.columns

    np.testing.assert_array_equal(result_df["translated_existing"].tolist(), [1.0, 2.0, 3.0])


def test_process_generators_with_variable_in_columns():

    class Generator:
        def __init__(self, id_):
            self.id = id_
            self.use_voltage_droop = True
            self.voltage_droop = 0.1

    generators = [Generator("GEN1"), Generator("GEN2"), Generator("GEN3")]

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

    get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)

    assert "GEN1_GEN_MagnitudeControlledByAVRPu" in curves_dict
    assert "GEN2_GEN_MagnitudeControlledByAVRPu" in curves_dict
    assert "GEN3_GEN_MagnitudeControlledByAVRPu" in curves_dict

    assert curves_dict["GEN1_GEN_MagnitudeControlledByAVRPu"] == [0.1, 0.2, 0.3]
    assert curves_dict["GEN2_GEN_MagnitudeControlledByAVRPu"] == [0.4, 0.5, 0.6]
    assert curves_dict["GEN3_GEN_MagnitudeControlledByAVRPu"] == [
        0.22000000000000003,
        0.31,
        0.42000000000000004,
    ]

    assert "GEN1_GEN_MagnitudeControlledByAVRPu" not in df_curves.columns
    assert "GEN2_GEN_MagnitudeControlledByAVRPu" not in df_curves.columns
    assert "GEN3_GEN_MagnitudeControlledByAVRUPu" not in df_curves.columns
    assert "OtherColumn" in df_curves.columns


def test_empty_generators_list():

    generators = []
    df_curves = pd.DataFrame({"OtherColumn1": [1.0, 2.0, 3.0], "OtherColumn2": [4.0, 5.0, 6.0]})
    original_df = df_curves.copy()

    curves_dict = {}

    get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)

    assert len(curves_dict) == 0
    pd.testing.assert_frame_equal(df_curves, original_df)


def test_get_modulus_correct_calculation():
    from dycov.curves.dynawo.runtime._curves import _get_modulus

    complex_list = [complex(3, 4), complex(5, 12)]
    expected_modulus = [5.0, 13.0]
    result = _get_modulus(complex_list)
    assert result == expected_modulus
