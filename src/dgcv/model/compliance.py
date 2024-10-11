from enum import Enum


class Compliance(Enum):
    Compliant = 1
    NonCompliant = 2
    InvalidTest = 3
    FailedSimulation = 4
    UndefinedValidations = 5
    WithoutCurves = 6
    WithoutReferenceCurves = 7
    WithoutProducerCurves =  8

    def to_str(self) -> str:
        if self == Compliance.Compliant:
            return "Compliant"
        elif self == Compliance.NonCompliant:
            return "Non-compliant"
        elif self == Compliance.InvalidTest:
            return "Invalid test"
        elif self == Compliance.FailedSimulation:
            return "Failed simulation"
        elif self == Compliance.UndefinedValidations:
            return "Undefined validations"
        elif self == Compliance.WithoutCurves:
            return "Test without curves"
        elif self == Compliance.WithoutReferenceCurves:
            return "Test without reference curves"
        elif self == Compliance.WithoutProducerCurves:
            return "Test without producer curves"
