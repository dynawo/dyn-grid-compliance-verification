#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from src.dycov.report.tables.solver import create_map


class TestCreateMap:
    def test_create_map_with_valid_solver(self):
        results = {
            "solver": {
                "max_iter": [1000.0, 500.0],
                "method": ["newton", "bisection"],
            }
        }
        expected = [
            ["max\\_iter", "1e+03 (500)"],
            ["method", "newton (bisection)"],
        ]
        assert create_map(results) == expected

    def test_create_map_escapes_underscores(self):
        results = {
            "solver": {
                "param_with_underscore": ["value_with_underscore", "default_value"],
            }
        }
        expected = [["param\\_with\\_underscore", "value\\_with\\_underscore (default\\_value)"]]
        assert create_map(results) == expected

    def test_create_map_formats_floats(self):
        results = {
            "solver": {
                "float_param": [0.000123456, 123456.789],
            }
        }
        expected = [["float\\_param", "0.000123 (1.23e+05)"]]
        assert create_map(results) == expected

    def test_create_map_missing_solver_key(self):
        results = {"not_solver": {"some_param": [1, 2]}}
        assert create_map(results) == []

    def test_create_map_empty_solver_dict(self):
        results = {"solver": {}}
        assert create_map(results) == []

    def test_create_map_with_unexpected_value_types(self):
        class Dummy:
            def __str__(self):
                return "dummy_value"

        results = {
            "solver": {
                "custom_type": [Dummy(), Dummy()],
                "int_param": [42, 7],
                "none_param": [None, None],
            }
        }
        expected = [
            ["custom\\_type", "dummy\\_value (dummy\\_value)"],
            ["int\\_param", "42 (7)"],
            ["none\\_param", "None (None)"],
        ]
        assert create_map(results) == expected
