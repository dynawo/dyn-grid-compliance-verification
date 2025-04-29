#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
import pytest

from dycov.validation.compliance_list import append, contains_key


class DummyConfig:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_list(self, section, key):
        # Simulate the config.get_list interface
        return self.mapping.get((section, key), [])


@pytest.fixture(autouse=True)
def patch_config(monkeypatch):
    # Patch the config object in compliance_list to use a dummy config for each test
    # Each test will set config.mapping as needed
    dummy = DummyConfig({})
    monkeypatch.setattr("dycov.validation.compliance_list.config", dummy)
    return dummy


def test_append_adds_subtests_when_benchmark_present_and_subtests_given(patch_config):
    patch_config.mapping = {
        ("Performance-Validations", "TestCompliance"): ["BenchmarkA", "BenchmarkB"]
    }
    target = []
    append(
        target,
        "BenchmarkA",
        "Performance-Validations",
        "TestCompliance",
        subtests=["sub1", "sub2"],
    )
    assert target == ["sub1", "sub2"]


def test_append_adds_compliance_test_when_benchmark_present_and_no_subtests(patch_config):
    patch_config.mapping = {("Model-Validations", "TestCompliance"): ["BenchmarkX"]}
    target = []
    append(target, "BenchmarkX", "Model-Validations", "TestCompliance")
    assert target == ["TestCompliance"]


def test_contains_key_returns_true_when_key_found():
    keys = ["foo", "bar"]
    elements = ["baz", "bar", "qux"]
    assert contains_key(keys, elements) is True


def test_append_no_modification_when_benchmark_absent(patch_config):
    patch_config.mapping = {("Performance-Validations", "TestCompliance"): ["BenchmarkA"]}
    target = ["existing"]
    append(target, "BenchmarkZ", "Performance-Validations", "TestCompliance", subtests=["sub1"])
    assert target == ["existing"]


def test_contains_key_returns_false_with_empty_keys():
    keys = []
    elements = ["a", "b", "c"]
    assert contains_key(keys, elements) is False


def test_contains_key_returns_false_with_empty_elements():
    keys = ["x", "y"]
    elements = []
    assert contains_key(keys, elements) is False
