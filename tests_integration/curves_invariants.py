"""What a run over the examples yields whatever curves it was given.

The curves of the examples are not versioned any more: they arrive with the asset of a release
or with a regeneration, so a test over them cannot assert a verdict — ``Compliant`` against
``NonCompliant`` is the one thing the curves decide, and a clone legitimately holds the curves of
one release or of a regeneration of its own.

Everything else a run yields is fixed by what is in the commit, and that is what is asserted
here:

* **which tests ran**, which the PCS descriptions and the producer decide;
* **that every one of them reached a verdict**, so a run that fell over — an invalid test, a
  simulation that failed or timed out — is a failure however the curves read;
* **which tests are not applicable**, which the control mode of the model decides and nothing
  else: a model either implements the mode a test needs or it does not;
* **that every delivered curve was verified**, because each CSV of a producer directory is one
  test, so the tests that reached a verdict are exactly the curves that arrived, less the ones
  the model cannot do.
"""

from pathlib import Path

from dycov.model.compliance import Compliance

# A test that was verified and said so, whichever way.
VERDICTS = (Compliance.Compliant, Compliance.NonCompliant)

# A test that could not be verified because a curve it needs, or the envelopes it is checked
# against, are not delivered. This is a statement about the dictionaries, the curves and the INI
# files on disk, not about what they contain.
UNDELIVERED = (
    Compliance.WithoutCurves,
    Compliance.WithoutReferenceCurves,
    Compliance.WithoutProducerCurves,
    Compliance.VoltageCurveMissing,
    Compliance.WithoutEnvelopes,
)

# The Grid Forming tests of the DTR Fiche I18, which the performance of a storage given its
# curves checks: the examples deliver neither their envelopes nor the parameters to generate them.
I18_TESTS = [
    f"PCS_RTE-I18z1.{scenario}.OC{oc}"
    for scenarios, operating_conditions in (
        ([f"S_VolAngStep{n}" for n in range(1, 13)], 5),
        ([f"S_VolAmpStep{n}" for n in range(1, 7)], 7),
        (["S_SCRup1", "S_SCRdown1"], 5),
        ([f"S_Rocof{n}" for n in range(1, 13)], 5),
    )
    for scenario in scenarios
    for oc in range(1, operating_conditions + 1)
]


def test_ids(summaries: list) -> list:
    """The tests the run executed, as ``PCS.benchmark.operating_condition``."""
    return [
        f"{summary.pcs}.{summary.benchmark}.{summary.operating_condition}" for summary in summaries
    ]


def _ids_with(summaries: list, compliances: tuple) -> set:
    return {
        test
        for test, summary in zip(test_ids(summaries), summaries)
        if summary.compliance in compliances
    }


def delivered_tests(*curve_paths: Path) -> set:
    """The tests whose curves are delivered: one CSV is one test, and a test needs its curve in
    every directory the run reads, so what it can verify is what they have in common."""
    delivered = [{curve.stem for curve in curve_path.rglob("*.csv")} for curve_path in curve_paths]
    return set.intersection(*delivered) if delivered else set()


def assert_run_is_sound(
    summaries: list,
    expected_tests: list,
    *curve_paths: Path,
    not_applicable: tuple = (),
) -> None:
    """Checks everything about a run that the curves do not decide. See the module docstring."""
    assert expected_tests == test_ids(summaries)

    unverified = {
        test: summary.compliance.name
        for test, summary in zip(test_ids(summaries), summaries)
        if summary.compliance not in VERDICTS + UNDELIVERED + (Compliance.NotApplicableTest,)
    }
    assert not unverified, f"tests that reached no verdict: {unverified}"

    assert set(not_applicable) == _ids_with(summaries, (Compliance.NotApplicableTest,))

    verifiable = delivered_tests(*curve_paths) - set(not_applicable)
    assert verifiable == _ids_with(summaries, VERDICTS)
