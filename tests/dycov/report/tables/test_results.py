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
