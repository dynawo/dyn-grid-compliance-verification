from enum import Enum, unique


@unique
class Compliance(Enum):
    """Compliance status resulting from a PCS or benchmark validation."""

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
    NotApplicableTest = 12

    def to_str(self) -> str:
        """Return a human-readable string representation of the compliance status.

        Returns
        -------
        str
            Human-readable string representation of the compliance status.

        """
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
            return "Missing some curves"
        elif self == Compliance.WithoutReferenceCurves:
            return "Missing some reference curves"
        elif self == Compliance.WithoutProducerCurves:
            return "Missing some producer curves"
        elif self == Compliance.FaultSimulationFails:
            return "Fault simulation fails"
        elif self == Compliance.FaultDipUnachievable:
            return "Fault dip unachievable"
        elif self == Compliance.SimulationTimeOut:
            return "Simulation time out"
        elif self == Compliance.NotApplicableTest:
            return "Not applicable test"

    def show_report(self) -> bool:
        """Indicate whether this compliance status should generate a report.

        Returns
        -------
        bool
            True if this compliance status should generate a report, False otherwise.
        """
        return self in [
            Compliance.Compliant,
            Compliance.NonCompliant,
            Compliance.FaultDipUnachievable,
            Compliance.WithoutReferenceCurves,
        ]
