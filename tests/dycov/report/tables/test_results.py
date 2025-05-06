#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
from dycov.report.tables.results import _iterate_variables, create_map


class TestResultsTable:

    def test_create_map_time_values_formatting(self):
        # Only time keys present
        results = {
            "time_10U": 0.5,
            "time_5U": 1.0,
            "time_10P": 1.5,
            "time_10Pfloor": 2.0,
            "time_5P": 2.5,
            "time_85U": 3.0,
            "time_cct": 3.5,
        }
        result_map = create_map(results)
        # All time values should be formatted with 3 significant digits and ' s' suffix
        expected = [
            ["$T_{10U}$", "0.5 s"],
            ["$T_{5U}$", "1 s"],
            ["$T_{10P}$", "1.5 s"],
            ["$T_{10P_{floor}}$", "2 s"],
            ["$T_{5P}$", "2.5 s"],
            ["$T_{85U}$", "3 s"],
            ["$T_{cct}$", "3.5 s"],
        ]
        for row in expected:
            assert row in result_map

    def test_create_map_with_no_expected_keys(self):
        # No expected keys
        results = {"foo": 1, "bar": 2}
        result_map = create_map(results)
        assert result_map == []

    def test_iterate_variables_missing_during_keys(self):
        # Only before/after keys for a variable, no during
        results = {}
        for prefix in [
            "before_mxe_",
            "before_me_",
            "before_mae_",
            "after_mxe_",
            "after_me_",
            "after_mae_",
        ]:
            results[f"{prefix}active_power_value"] = 0.444
        results_map = []
        _iterate_variables(results, results_map)
        # Only active_power should be present, with 7 columns (col + 6 values)
        assert len(results_map) == 1
        assert results_map[0][0] == "P"
        assert results_map[0][1:] == ["0.444"] * 6

    def test_create_map_all_keys_present(self):
        results = {
            "time_10U": 1.234,
            "time_5U": 2.345,
            "time_10P": 3.456,
            "time_10Pfloor": 4.567,
            "time_5P": 5.678,
            "time_85U": 6.789,
            "time_cct": 7.890,
            "static_diff": 0.123,
        }
        # Add all before/after keys for all variables
        for var in [
            "voltage",
            "active_power",
            "reactive_power",
            "active_current",
            "reactive_current",
        ]:
            for prefix in [
                "before_mxe_",
                "before_me_",
                "before_mae_",
                "after_mxe_",
                "after_me_",
                "after_mae_",
            ]:
                results[f"{prefix}{var}_value"] = 1.0
        expected_time_rows = [
            ["$T_{10U}$", "1.23 s"],
            ["$T_{5U}$", "2.35 s"],
            ["$T_{10P}$", "3.46 s"],
            ["$T_{10P_{floor}}$", "4.57 s"],
            ["$T_{5P}$", "5.68 s"],
            ["$T_{85U}$", "6.79 s"],
            ["$T_{cct}$", "7.89 s"],
            ["$\epsilon$", "0.123"],
        ]
        expected_var_rows = [
            ["V", "1", "1", "1", "1", "1", "1"],
            ["P", "1", "1", "1", "1", "1", "1"],
            ["Q", "1", "1", "1", "1", "1", "1"],
            ["$I_p$", "1", "1", "1", "1", "1", "1"],
            ["$I_q$", "1", "1", "1", "1", "1", "1"],
        ]
        result = create_map(results)
        # Check time rows
        assert result[: len(expected_time_rows)] == expected_time_rows
        # Check variable rows (order and values)
        assert result[len(expected_time_rows) :] == expected_var_rows

    def test_create_map_with_during_keys(self):
        results = {}
        for var in [
            "voltage",
            "active_power",
            "reactive_power",
            "active_current",
            "reactive_current",
        ]:
            for prefix in [
                "before_mxe_",
                "before_me_",
                "before_mae_",
                "after_mxe_",
                "after_me_",
                "after_mae_",
                "during_mxe_",
                "during_me_",
                "during_mae_",
            ]:
                results[f"{prefix}{var}_value"] = 2.0
        result = create_map(results)
        # Each variable row should have 10 columns: label + 9 values
        for row in result:
            assert len(row) == 10
            assert row[0] in ["V", "P", "Q", "$I_p$", "$I_q$"]
            assert all(val == "2" for val in row[1:])

    def test_create_map_no_variable_keys(self):
        results = {
            "time_10U": 1.0,
            "time_5U": 2.0,
            "static_diff": 0.5,
        }
        result = create_map(results)
        # Only time/static rows, no variable rows
        assert result == [
            ["$T_{10U}$", "1 s"],
            ["$T_{5U}$", "2 s"],
            ["$\epsilon$", "0.5"],
        ]

    def test_create_map_missing_time_keys(self):
        results = {
            "static_diff": 0.42,
            "before_mxe_voltage_value": 0.1,
            "before_me_voltage_value": 0.2,
            "before_mae_voltage_value": 0.3,
            "after_mxe_voltage_value": 0.4,
            "after_me_voltage_value": 0.5,
            "after_mae_voltage_value": 0.6,
        }
        result = create_map(results)
        # Only static_diff and voltage variable row
        assert result[0] == ["$\epsilon$", "0.42"]
        assert result[1][0] == "V"
        assert result[1][1:] == ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6"]
        assert len(result) == 2

    def test_create_map_empty_input(self):
        results = {}
        result = create_map(results)
        assert result == []
