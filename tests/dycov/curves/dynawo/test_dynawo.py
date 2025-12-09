#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dycov.curves.dynawo.runtime.dynawo_simulator import DynamicSimulator


class DummyLogger:
    def __init__(self):
        self.messages = []

    def get_logger(self, name):
        return self

    def debug(self, msg):
        self.messages.append(("debug", msg))

    def info(self, msg):
        self.messages.append(("info", msg))

    def error(self, msg):
        self.messages.append(("error", msg))


@pytest.fixture(autouse=True)
def patch_dycov_logging(monkeypatch):
    dummy_logger = DummyLogger()
    monkeypatch.setattr("dycov.logging.logging.dycov_logging", dummy_logger)
    return dummy_logger


def create_minimal_model_xml(tmp_path, model_name, model_id="TestModel"):
    xml_content = f"""<root xmlns="http://www.dynawo.org/DynawoModel">
        <modelicaModel id="{model_id}"/>
    </root>"""
    model_path = tmp_path / model_name
    with open(model_path, "w") as f:
        f.write(xml_content)
    return model_path


def create_dummy_launcher(tmp_path, version="1.2.3"):
    launcher = tmp_path / "launcher_dwo"
    with open(launcher, "w") as f:
        f.write("#!/bin/sh\n")
        f.write(f'if [ "$1" = "version" ]; then echo "{version}"; exit 0; fi\n')
        f.write("touch $5\n")  # For jobs --generate-preassembled, create output file
        f.write("exit 0\n")
    os.chmod(launcher, 0o755)
    return launcher


def create_dummy_compile_script(tmp_path):
    script = tmp_path / "Vsx64.cmd"
    with open(script, "w") as f:
        f.write("@echo off\n")
        f.write("echo Compiling...\n")
        f.write("exit /b 0\n")
    os.chmod(script, 0o755)
    return script


def test_is_stable_raises_on_length_mismatch():
    # Import from correct location
    from dycov.validation.common import is_stable

    time = [0.0, 0.1, 0.2]
    curve = [1.0, 1.1]
    stable_time = 0.1
    with pytest.raises(ValueError) as excinfo:
        is_stable(time, curve, stable_time)
    assert "different length" in str(excinfo.value)


def test_create_curves_handles_missing_or_malformed_file(tmp_path):
    # Setup
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
    # Case 1: Missing file
    missing_file = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        DynamicSimulator()._create_curves(
            variable_translations, missing_file, generators, snom, snref
        )
    # Case 2: Malformed file
    malformed_file = tmp_path / "malformed.csv"
    with open(malformed_file, "w") as f:
        f.write("not,a,valid,csv\n1,2,3\n")
    with pytest.raises(Exception):
        DynamicSimulator()._create_curves(
            variable_translations, malformed_file, generators, snom, snref
        )


# Voltage dip equals expected dip within tolerance (returns 0)
def test_voltage_dip_equals_expected_dip_within_tolerance(mocker):
    # Arrange
    curves = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8],
        }
    )
    fault_start = 0.15
    fault_duration = 0.3
    expected_dip = 0.2

    # Mock _trim_curves to return controlled values
    mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._trim_curves",
        return_value=(
            [0.0, 0.1],  # pre_time_values
            [0.2, 0.3, 0.4, 0.5],  # post_time_values
            [1.0, 1.0],  # pre_voltage_values
            [0.8, 0.8, 0.8, 0.8],  # post_voltage_values
        ),
    )

    # Mock is_stable to return expected values
    mock_is_stable = mocker.patch("dycov.validation.common.is_stable")
    mock_is_stable.side_effect = [(True, 0), (True, 0)]

    # Mock logger
    mock_logger = mocker.MagicMock()
    mocker.patch("dycov.logging.logging.dycov_logging.get_logger", return_value=mock_logger)

    # Act
    result = DynamicSimulator().check_voltage_dip(
        "PCS", "BM", "OC", curves, fault_start, fault_duration, expected_dip
    )

    # Assert
    assert result == 0


# Fault duration exceeds simulation time
def test_fault_duration_exceeds_simulation_time(mocker):
    # Arrange
    curves = pd.DataFrame(
        {
            "time": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 0.8, 0.8, 0.8, 0.8],
        }
    )
    fault_start = 0.2
    fault_duration = 1.0  # Exceeds the max time of 0.5
    expected_dip = 0.2

    # Mock _trim_curves to verify it's called with adjusted fault_duration
    mock_trim_curves = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._trim_curves",
        return_value=(
            [0.0, 0.1],  # pre_time_values
            [0.2, 0.3, 0.4, 0.5],  # post_time_values
            [1.0, 1.0],  # pre_voltage_values
            [0.8, 0.8, 0.8, 0.8],  # post_voltage_values
        ),
    )

    # Mock is_stable
    mock_is_stable = mocker.patch("dycov.validation.common.is_stable")
    mock_is_stable.side_effect = [(True, 0), (True, 0)]

    # Mock logger
    mock_logger = mocker.MagicMock()
    mocker.patch("dycov.logging.logging.dycov_logging.get_logger", return_value=mock_logger)

    # Act
    result = DynamicSimulator().check_voltage_dip(
        "PCS", "BM", "OC", curves, fault_start, fault_duration, expected_dip
    )

    # Assert
    # Verify that _trim_curves was called with the adjusted fault_duration
    expected_adjusted_duration = 0.5 - fault_start  # 0.3
    mock_trim_curves.assert_called_once()
    _, _, _, actual_adjusted_duration = mock_trim_curves.call_args[0]
    assert math.isclose(actual_adjusted_duration, expected_adjusted_duration)

    # Verify the function returns the expected result
    assert result == 0


# Function correctly identifies pre-fault and post-fault time and voltage values
def test_correct_identification_of_pre_and_post_fault_values():
    # Arrange
    time_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    voltage_values = [1.0, 1.0, 1.0, 0.8, 0.6, 0.4, 0.6, 0.8, 0.9, 1.0, 1.0]
    fault_start = 0.4
    fault_duration = 0.4

    # Act
    pre_time, post_time, pre_voltage, post_voltage = DynamicSimulator()._trim_curves(
        time_values, voltage_values, fault_start, fault_duration
    )

    # Assert
    assert pre_time == [0.0, 0.1, 0.2, 0.3]
    assert pre_voltage == [1.0, 1.0, 1.0, 0.8]
    assert post_time == [0.4, 0.5, 0.6, 0.7]
    assert post_voltage == [0.6, 0.4, 0.6, 0.8]


# Empty input lists for time_values and voltage_values
def test_empty_input_lists():
    # Arrange
    time_values = []
    voltage_values = []
    fault_start = 0.3
    fault_duration = 0.4

    # Act
    pre_time, post_time, pre_voltage, post_voltage = DynamicSimulator()._trim_curves(
        time_values, voltage_values, fault_start, fault_duration
    )

    # Assert
    assert pre_time == []
    assert post_time == []
    assert pre_voltage == []
    assert post_voltage == []


# Successfully processes a valid input file and returns a DataFrame with transformed curves
def test_valid_input_file_processing(mocker):
    # Mock dependencies
    mock_translate_curves = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._translate_curves"
    )
    mock_get_pdr_voltage = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._get_pdr_voltage"
    )
    mock_get_modulus = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._get_modulus"
    )
    mock_get_pdr_current = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._get_pdr_current"
    )
    mock_get_pdr_active_power = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._get_pdr_active_power"
    )
    mock_get_pdr_reactive_power = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._get_pdr_reactive_power"
    )
    mock_get_magnitude_controlled_by_avr = mocker.patch(
        "dycov.curves.dynawo.runtime.dynawo.DynamicSimulator._get_magnitude_controlled_by_avr"
    )

    # Setup test data
    variable_translations = {"var1": "dynawo_var1"}
    input_file = Path("test_file.csv")
    generators = [mocker.MagicMock()]
    snom = 100.0
    snref = 100.0

    # Mock read_csv
    mock_df = pd.DataFrame(
        {
            "time": [0, 1, 2],
            "BusPDR_BUS_Voltage": [1.0, 1.0, 1.0],
            "var1": [1.0, 2.0, 3.0],
            "Unnamed: 0": [0, 1, 2],
        }
    )
    mocker.patch("pandas.read_csv", return_value=mock_df)

    # Mock return values
    mock_translate_curves.return_value = pd.DataFrame(
        {"BusPDR_BUS_Voltage": [1.0, 1.0, 1.0], "var1": [1.0, 2.0, 3.0]}
    )
    mock_get_pdr_voltage.return_value = [1 + 0j, 1 + 0j, 1 + 0j]
    mock_get_modulus.side_effect = lambda x: (
        [1.0, 1.0, 1.0] if x == mock_get_pdr_voltage.return_value else [abs(val) for val in x]
    )
    mock_get_pdr_current.return_value = [0.5 + 0j, 0.5 + 0j, 0.5 + 0j]
    mock_get_pdr_active_power.return_value = [0.5, 0.5, 0.5]
    mock_get_pdr_reactive_power.return_value = [0.3, 0.3, 0.3]

    # Call function under test
    result = DynamicSimulator()._create_curves(
        variable_translations, input_file, generators, snom, snref
    )

    # Assertions
    assert isinstance(result, pd.DataFrame)
    assert "BusPDR_BUS_Voltage" in result.columns
    assert "BusPDR_BUS_ActivePower" in result.columns
    assert "BusPDR_BUS_ReactivePower" in result.columns
    assert "BusPDR_BUS_ActiveCurrent" in result.columns
    assert "BusPDR_BUS_ReactiveCurrent" in result.columns

    # Verify function calls
    mock_translate_curves.assert_called_once_with(variable_translations, mocker.ANY)
    mock_get_pdr_voltage.assert_called_once()
    mock_get_pdr_current.assert_called_once()
    mock_get_magnitude_controlled_by_avr.assert_called_once_with(
        generators, mocker.ANY, mocker.ANY
    )


# Translating complex columns with correct sign conventions
def test_prepare_complex_column_applies_sign_conventions():
    # Arrange
    column_name = "test_column"
    column_size = 3
    df_curves = pd.DataFrame(
        {f"{column_name}re": [1.0, 2.0, 3.0], f"{column_name}im": [4.0, 5.0, 6.0]}
    )
    translated_column = "translated_test"
    variable_translations = {
        "translated_testRe": -1,  # Invert real part
        "translated_testIm": 2,  # Double imaginary part
    }

    # Act
    result = DynamicSimulator()._prepare_complex_column(
        column_name, column_size, df_curves, translated_column, variable_translations
    )

    # Assert
    expected_real = [-1.0, -2.0, -3.0]  # Original values multiplied by -1
    expected_imag = [8.0, 10.0, 12.0]  # Original values multiplied by 2

    # Convert result back to complex array for easier comparison
    complex_result = np.array(result, dtype=np.complex128)

    np.testing.assert_almost_equal(complex_result.real, expected_real)
    np.testing.assert_almost_equal(complex_result.imag, expected_imag)


# Empty dataframes or missing columns in input data
def test_translate_curves_with_missing_columns():
    # Arrange
    df_curves_imported = pd.DataFrame(
        {
            "time": [0.0, 1.0, 2.0],
            "existing_column": [1.0, 2.0, 3.0],
            # Missing complex columns
        }
    )

    variable_translations = {
        "existing_column": ["translated_existing"],
        "missing_column_re": ["missing_translated_Re"],
        "missing_column_im": ["missing_translated_Im"],
        "translated_existing": 1,
    }

    # Act
    result_df = DynamicSimulator()._translate_curves(variable_translations, df_curves_imported)

    # Assert
    # Should contain time and translated existing column
    assert "time" in result_df.columns
    assert "translated_existing" in result_df.columns
    # Should not contain the missing translated column
    assert "missing_translated" not in result_df.columns

    # Check values of translated existing column
    np.testing.assert_array_equal(result_df["translated_existing"].tolist(), [1.0, 2.0, 3.0])


# Function correctly processes generators with variable in df_curves.columns
def test_process_generators_with_variable_in_columns():
    # Arrange
    class Generator:
        def __init__(self, id):
            self.id = id
            self.UseVoltageDroop = True
            self.VoltageDroop = 0.1

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

    # Act
    DynamicSimulator()._get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)
    print(curves_dict["GEN3_GEN_MagnitudeControlledByAVRPu"])
    # Assert
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


# Empty generators list
def test_empty_generators_list():
    # Arrange
    generators = []
    df_curves = pd.DataFrame({"OtherColumn1": [1.0, 2.0, 3.0], "OtherColumn2": [4.0, 5.0, 6.0]})
    original_df = df_curves.copy()
    curves_dict = {}

    # Act
    DynamicSimulator()._get_magnitude_controlled_by_avr(generators, df_curves, curves_dict)

    # Assert
    assert len(curves_dict) == 0
    pd.testing.assert_frame_equal(df_curves, original_df)


# _get_pdr_voltage returns voltage values as a list when matching columns exist
def test_get_pdr_voltage_returns_values_when_matching_columns_exist():
    # Create a DataFrame with a voltage column matching the regex
    df = pd.DataFrame({"BUS1_TE_LOAD_Voltage": [1.0, 2.0, 3.0], "Other_Column": [4.0, 5.0, 6.0]})

    # Act
    result = DynamicSimulator()._get_pdr_voltage(df)

    # Assert
    assert result == [1.0, 2.0, 3.0]
    assert isinstance(result, list)


# _get_pdr_voltage returns empty list when no matching voltage columns exist
def test_get_pdr_voltage_returns_empty_list_when_no_matching_columns():
    # Create a DataFrame without any voltage columns matching the regex
    df = pd.DataFrame(
        {"BUS1_NonMatching_Column": [1.0, 2.0, 3.0], "Other_Column": [4.0, 5.0, 6.0]}
    )

    # Act
    result = DynamicSimulator()._get_pdr_voltage(df)

    # Assert
    assert result == []
    assert isinstance(result, list)


# _get_pdr_current returns current values as a list when matching columns exist
def test_get_pdr_current_with_matching_columns():
    import numpy as np
    import pandas as pd

    # Create a DataFrame with matching current columns
    data = {
        "A_TE_1_Current": [1 + 2j, 3 + 4j],
        "B_TE_2_Current": [5 + 6j, 7 + 8j],
        "C_TE_3_Voltage": [9 + 10j, 11 + 12j],  # Non-matching column
    }
    df_curves = pd.DataFrame(data)

    # Expected result is the sum of the matching current columns
    expected_result = np.add([1 + 2j, 3 + 4j], [5 + 6j, 7 + 8j]).tolist()

    # Call the function under test
    result = DynamicSimulator()._get_pdr_current(df_curves, 2)

    # Assert the result is as expected
    assert result == expected_result


# _get_pdr_active_power correctly calculates active power using voltage and current
def test_get_pdr_active_power_calculation():
    import numpy as np

    # Sample voltage and current lists
    pdr_voltage = [1 + 2j, 3 + 4j]
    pdr_current = [5 + 6j, 7 + 8j]
    snom = 100.0
    snref = 50.0

    # Expected active power calculation
    expected_active_power = (
        np.real(np.multiply(pdr_voltage, np.conjugate(pdr_current))) * -1 * snref / snom
    )

    # Call the function under test
    result = DynamicSimulator()._get_pdr_active_power(pdr_voltage, pdr_current, snom, snref)

    # Assert the result is as expected
    assert result == expected_active_power.tolist()


# _get_pdr_reactive_power correctly calculates reactive power using voltage and current
def test_get_pdr_reactive_power_correct_calculation():
    pdr_voltage = [complex(1, 2), complex(3, 4)]
    pdr_current = [complex(5, 6), complex(7, 8)]
    snom = 100.0
    snref = 50.0
    expected_reactive_power = [-2.0, -2.0]

    result = DynamicSimulator()._get_pdr_reactive_power(pdr_voltage, pdr_current, snom, snref)

    assert result == expected_reactive_power


# _get_modulus correctly calculates the absolute value of complex numbers
def test_get_modulus_correct_calculation():
    complex_list = [complex(3, 4), complex(5, 12)]
    expected_modulus = [5.0, 13.0]

    result = DynamicSimulator()._get_modulus(complex_list)

    assert result == expected_modulus


# _get_pdr_current returns empty list when no matching current columns exist
def test_get_pdr_current_no_matching_columns():
    df_curves = pd.DataFrame({"A_TE_B_Voltage": [1, 2, 3], "B_TE_C_Voltage": [4, 5, 6]})
    column_size = 3

    result = DynamicSimulator()._get_pdr_current(df_curves, column_size)

    assert result == []
