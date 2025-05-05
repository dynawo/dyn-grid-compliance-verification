#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
import pytest

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
