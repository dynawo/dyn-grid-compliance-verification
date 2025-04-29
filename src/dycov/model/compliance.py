from enum import Enum, unique


@unique
class Compliance(Enum):
    Compliant = 1
    NonCompliant = 2
    InvalidTest = 3
    FailedSimulation = 4
    UndefinedValidations = 5
    WithoutCurves = 6
    WithoutReferenceCurves = 7
    WithoutProducerCurves = 8
    FaultSimulationFails = 9
    FaultDipUnachievable = 10
    SimulationTimeOut = 11

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
        elif self == Compliance.FaultSimulationFails:
            return "Fault simulation fails"
        elif self == Compliance.FaultDipUnachievable:
            return "Fault dip unachievable"
        elif self == Compliance.SimulationTimeOut:
            return "Simulation time out"

    def show_report(self) -> bool:
        return self in [
            Compliance.Compliant,
            Compliance.NonCompliant,
            Compliance.FaultDipUnachievable,
        ]
