from dycov.model.compliance import Compliance
from tests.dycov.utils import MODEL, execute_tool

RESOURCES = "./resources"


def test_model_validation_iec2015_curves():
    compliance = execute_tool(
        None,
        f"{MODEL}/Wind/IECB2015/ProducerCurves",
        f"{MODEL}/Wind/IECB2015/ReferenceCurves",
    )
    assert [
        Compliance.Compliant,  # 0
        Compliance.Compliant,  # 1
        Compliance.Compliant,  # 2
        Compliance.Compliant,  # 3
        Compliance.Compliant,  # 4
        Compliance.Compliant,  # 5
        Compliance.Compliant,  # 6
        Compliance.Compliant,  # 7
        Compliance.Compliant,  # 8
        Compliance.Compliant,  # 9
        Compliance.InvalidTest,  # 10
        Compliance.Compliant,  # 11
        Compliance.Compliant,  # 12
        Compliance.Compliant,  # 13
        Compliance.Compliant,  # 14
        Compliance.Compliant,  # 15
        Compliance.Compliant,  # 16
        Compliance.Compliant,  # 17
        Compliance.Compliant,  # 18
        Compliance.Compliant,  # 19
        Compliance.Compliant,  # 20
        Compliance.Compliant,  # 21
        Compliance.Compliant,  # 22
        Compliance.Compliant,  # 23
    ] == compliance
