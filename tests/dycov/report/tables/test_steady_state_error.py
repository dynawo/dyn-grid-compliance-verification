#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from dycov.report.tables.steady_state_error import _steady_state_error, create_map


class TestSteadyStateErrorTable:

    def test_steady_state_error_appends_row_on_valid_check(self):
        results = {
            "mae_voltage_1P_check": True,
            "mae_voltage_1P": 0.1234,
            "ss_error_voltage_1P": 0.5678,
        }
        errors_map = []
        _steady_state_error(results, "V", "voltage", errors_map)
        assert len(errors_map) == 1
        row = errors_map[0]
        assert row[0] == "V"
        assert row[1] == "0.123"
        assert row[2] == "0.568"
        assert row[3] == "{ True }"

    def test_create_map_multiple_measurements(self):
        results = {
            "mae_voltage_1P_check": True,
            "mae_voltage_1P": 0.01,
            "ss_error_voltage_1P": 0.02,
            "mae_active_power_1P_check": True,
            "mae_active_power_1P": 0.03,
            "ss_error_active_power_1P": 0.04,
            "mae_reactive_power_1P_check": True,
            "mae_reactive_power_1P": 0.05,
            "ss_error_reactive_power_1P": 0.06,
            "mae_active_current_1P_check": True,
            "mae_active_current_1P": 0.07,
            "ss_error_active_current_1P": 0.08,
            "mae_reactive_current_1P_check": True,
            "mae_reactive_current_1P": 0.09,
            "ss_error_reactive_current_1P": 0.10,
        }
        errors_map = create_map(results)
        assert len(errors_map) == 5
        names = [row[0] for row in errors_map]
        assert set(names) == {"V", "P", "Q", "$I_p$", "$I_q$"}

    def test_create_map_with_missing_keys(self):
        results = {}
        errors_map = create_map(results)
        assert errors_map == []

    def test_steady_state_error_appends_red_on_failed_check(self):
        results = {
            "mae_voltage_1P_check": False,
            "mae_voltage_1P": 0.1234,
            "ss_error_voltage_1P": 0.5678,
        }
        errors_map = []
        _steady_state_error(results, "V", "voltage", errors_map)
        assert len(errors_map) == 1
        row = errors_map[0]
        assert row[0] == "V"
        assert row[1] == "\\textcolor{red}{ 0.123 }"
        assert row[2] == "0.568"
        assert row[3] == "\\textcolor{red}{ False }"

    def test_create_map_with_all_valid_keys(self):
        results = {
            "mae_voltage_1P": 0.12345,
            "ss_error_voltage_1P": 0.23456,
            "mae_voltage_1P_check": True,
            "mae_active_power_1P": 0.34567,
            "ss_error_active_power_1P": 0.45678,
            "mae_active_power_1P_check": True,
            "mae_reactive_power_1P": 0.56789,
            "ss_error_reactive_power_1P": 0.67891,
            "mae_reactive_power_1P_check": True,
            "mae_active_current_1P": 0.78912,
            "ss_error_active_current_1P": 0.89123,
            "mae_active_current_1P_check": True,
            "mae_reactive_current_1P": 0.91234,
            "ss_error_reactive_current_1P": 0.12345,
            "mae_reactive_current_1P_check": True,
        }
        error_map = create_map(results)
        assert len(error_map) == 5
        for entry, name, mae_key, ss_key, check_key in zip(
            error_map,
            ["V", "P", "Q", "$I_p$", "$I_q$"],
            [
                "mae_voltage_1P",
                "mae_active_power_1P",
                "mae_reactive_power_1P",
                "mae_active_current_1P",
                "mae_reactive_current_1P",
            ],
            [
                "ss_error_voltage_1P",
                "ss_error_active_power_1P",
                "ss_error_reactive_power_1P",
                "ss_error_active_current_1P",
                "ss_error_reactive_current_1P",
            ],
            [
                "mae_voltage_1P_check",
                "mae_active_power_1P_check",
                "mae_reactive_power_1P_check",
                "mae_active_current_1P_check",
                "mae_reactive_current_1P_check",
            ],
        ):
            assert entry[0] == name
            # Check formatted MAE value (rounded to 3 significant digits)
            assert entry[1] == f"{results[mae_key]:.3g}"
            # Check formatted SS error value (rounded to 3 significant digits)
            assert entry[2] == f"{results[ss_key]:.3g}"
            # Check check value is formatted as LaTeX True
            assert entry[3] == "{ True }"

    def test_steady_state_error_latex_coloring_on_failure(self):
        results = {
            "mae_voltage_1P": 0.12345,
            "ss_error_voltage_1P": 0.23456,
            "mae_voltage_1P_check": False,
        }
        error_map = create_map(results)
        assert len(error_map) == 1
        entry = error_map[0]
        assert entry[0] == "V"
        # Should be colored in red
        assert entry[1] == r"\textcolor{red}{ 0.123 }"
        assert entry[2] == "0.235"
        assert entry[3] == r"\textcolor{red}{ False }"

    def test_create_map_invokes_steady_state_error_for_all_measurements(self):
        results = {
            "mae_voltage_1P": 0.1,
            "ss_error_voltage_1P": 0.2,
            "mae_voltage_1P_check": True,
            "mae_active_power_1P": 0.3,
            "ss_error_active_power_1P": 0.4,
            "mae_active_power_1P_check": True,
            "mae_reactive_power_1P": 0.5,
            "ss_error_reactive_power_1P": 0.6,
            "mae_reactive_power_1P_check": True,
            "mae_active_current_1P": 0.7,
            "ss_error_active_current_1P": 0.8,
            "mae_active_current_1P_check": True,
            "mae_reactive_current_1P": 0.9,
            "ss_error_reactive_current_1P": 1.0,
            "mae_reactive_current_1P_check": True,
        }
        error_map = create_map(results)
        assert len(error_map) == 5
        expected_names = ["V", "P", "Q", "$I_p$", "$I_q$"]
        for i, name in enumerate(expected_names):
            assert error_map[i][0] == name

    def test_create_map_with_missing_measurement_keys(self):
        results = {
            "mae_voltage_1P": 0.1,
            "ss_error_voltage_1P": 0.2,
            "mae_voltage_1P_check": True,
            # Missing all other measurement keys
        }
        error_map = create_map(results)
        assert len(error_map) == 1
        assert error_map[0][0] == "V"
        assert error_map[0][1] == "0.1"
        assert error_map[0][2] == "0.2"
        assert error_map[0][3] == "{ True }"

    def test_create_map_with_error_values_below_minimum(self):
        # All values below minimum threshold (1e-8)
        results = {
            "mae_voltage_1P": 1e-10,
            "ss_error_voltage_1P": 5e-10,
            "mae_voltage_1P_check": True,
        }
        error_map = create_map(results)
        assert len(error_map) == 1
        entry = error_map[0]
        assert entry[0] == "V"
        # Should be formatted as 0.0
        assert entry[1] == "0.0"
        assert entry[2] == "0.0"
        assert entry[3] == "{ True }"

    def test_create_map_with_empty_results(self):
        results = {}
        error_map = create_map(results)
        assert error_map == []
