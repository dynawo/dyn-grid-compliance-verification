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
    _get_modulus,
    create_curves,
    get_magnitude_controlled_by_avr,
    prepare_complex_column,
    translate_curves,
)

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

    missing_file = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        create_curves(variable_translations, missing_file, generators, snom, snref, fnom)

    malformed_file = tmp_path / "malformed.csv"
    malformed_file.write_text("not,a,valid,csv\n1,2,3\n")
    with pytest.raises(Exception):
        create_curves(variable_translations, malformed_file, generators, snom, snref, fnom)


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

    variable_translations = {
        "translated_testRe": -1,
        "translated_testIm": 2,
    }

    result = prepare_complex_column(
        column_name, column_size, df_curves, "translated_test", variable_translations
    )

    complex_result = np.array(result, dtype=np.complex128)
    np.testing.assert_almost_equal(complex_result.real, [-1.0, -2.0, -3.0])
    np.testing.assert_almost_equal(complex_result.imag, [8.0, 10.0, 12.0])


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

    df_curves = pd.DataFrame({"OtherColumn1": [1.0, 2.0, 3.0], "OtherColumn2": [4.0, 5.0, 6.0]})
    original_df = df_curves.copy()

    curves_dict = {}
    get_magnitude_controlled_by_avr([], df_curves, curves_dict)

    assert len(curves_dict) == 0
    pd.testing.assert_frame_equal(df_curves, original_df)


def test_get_modulus_correct_calculation():
    complex_list = [complex(3, 4), complex(5, 12)]
    result = _get_modulus(complex_list)
    assert result == [5.0, 13.0]
