"""The fault searches of the examples reach their dip.

A search that stops reaching it ends its test as "Fault dip unachievable" and leaves the test
without its fault, which the model the other integration tests validate may not show. These run
the Zone 1 of the examples whose high-impedance faults are the hardest to reach, and fail when
any of their faults ends without a verdict.
"""

import pytest
from tests.dycov.utils import MODEL, _resolve_dynawo_sh, execute_tool_summary

from dycov.model.compliance import Compliance

_VERDICTS = (Compliance.Compliant, Compliance.NonCompliant)


@pytest.mark.parametrize("example", ["IECA2015", "IECB2020WithProtections", "WECC4B"])
def test_the_fault_searches_of_an_example_reach_their_dip(example):
    if _resolve_dynawo_sh() is None:
        pytest.skip("Needs Dynawo: set DYNAWOPATH or put dynawo.sh on the PATH.")

    summaries = execute_tool_summary(
        MODEL / "Wind" / example / "Dynawo",
        None,
        MODEL / "Wind" / example / "ReferenceCurves",
        "PCS_RTE-I16z1",
    )

    faults = [summary for summary in summaries if summary.benchmark == "ThreePhaseFault"]
    assert faults
    assert [
        f"{summary.benchmark}.{summary.operating_condition}: {summary.compliance}"
        for summary in faults
        if summary.compliance not in _VERDICTS
    ] == []
