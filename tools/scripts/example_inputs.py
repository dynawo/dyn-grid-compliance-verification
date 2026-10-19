"""Writes the inputs of the example curve directories, which are not versioned.

The curves of the examples ship as an asset of the release, and so does everything that sits
beside them: nothing under ``ReferenceCurves/`` or ``ProducerCurves/`` is in the repository, so
whatever a producer would have written by hand there is written here instead.

Two things are written:

* **the producer declaration** of a curve directory (``Producer.ini``) — the same producer as the
  example the curves come from, stated as a producer delivering curves states it: the magnitudes
  of the DTR, the kind of generator, and the apparent power of its model. The parameters of the
  Dynawo model itself do not travel, because there is no model on this side;
* **the F16 declaration** (``F16Description.ini``) — the on-site tests the example declares as
  recorded.

What neither the model nor the example states — the apparent power and the power levels of the
F16 tests — is read from ``example_inputs.ini``, beside this script.
"""

import argparse
import configparser
from pathlib import Path

CONFIGURATION = Path(__file__).resolve().parent / "example_inputs.ini"

# The magnitudes of the DTR a producer declares, in the order they are written.
_DTR_MAGNITUDES = (
    ("p_max_injection", "p_{max_unite} injection as defined by the DTR in MW"),
    ("p_max_consumption", "p_{max_unite} consumption as defined by the DTR in MW (only for BESS)"),
    (
        "p_min_injection",
        "p_{min_unite} injection in MW, the lowest active power the on-site tests of the DTR"
        " Fiche F16 start from",
    ),
    ("p_min_consumption", "p_{min_unite} consumption in MW"),
    ("u_nom", "Nominal voltage of the PDR bus (in kV)"),
    ("q_max", "Maximum reactive power (in MVar)"),
    ("q_min", "Minimum reactive power (in MVar)"),
    ("topology", "Topology of the installation"),
)

_PRODUCER_HEADER = """# The producer of the curves below, as a producer delivering records
# declares it. Written by tools/scripts/example_inputs.py from {source}, which is the model
# these curves were simulated with: the magnitudes are its own, and the parameters of the
# Dynawo model do not travel, because a delivery of curves has no model.

[DEFAULT]
"""

# The two kinds of setpoint step that are declared: its name, how the job is called, the control
# mode it needs, the magnitude the event is connected to and the tolerance of the tracking check.
_F16_BENCHMARKS = (
    ("PSetPointStep", "Active Setpoint Step", "PSetpoint", "ActivePowerSetpointPu", "0.4*Pmax"),
    ("USetPointStep", "Voltage Setpoint Step", "USetpoint", "VoltageSetpointPu", "0.02"),
)

# The step of the voltage test, which does not depend on the power level.
_F16_VOLTAGE_STEP = "0.02*Udim"

_F16_CHECKS = (
    "reaction_time",
    "rise_time",
    "response_time",
    "settling_time",
    "overshoot",
    "mean_absolute_error_power_1P",
    "mean_absolute_error_injection_1P",
    "mean_absolute_error_voltage",
    "setpoint_tracking_controlled_magnitude",
)

_F16_FIGURES = ("fig_P", "fig_Q", "fig_Ip", "fig_Iq", "fig_Ustator", "fig_V")

_F16_HEADER = """# Tests of the DTR Fiche F16 declared with their records, as a producer delivers
# them. Written by tools/scripts/example_inputs.py: the fiche selects no test of its own, so
# these are invented for the examples, and the records are the tool's own simulations of
# setpoint steps, anonymized as measurements.
#
# How to complete this file is explained in the chapter 'The F16 declaration file' of the
# user manual (every key, kind of test by kind of test) and in the tutorial 'Declaring the
# on-site tests of PCS F16' (docs/tutorials/f16_declaring_recorded_tests.md), step by step.
# Every test it activates is described in the chapter 'Compliance tests' of the user manual.
"""


def _read_ini(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(inline_comment_prefixes=("#",))
    parser.optionxform = str
    if not parser.read(path):
        raise SystemExit(f"{path}: not found.")
    return parser


def producer_declaration(dynawo_path: Path, generator_type: str, zone: str) -> str:
    """The ``Producer.ini`` of a curve directory, from the model its curves were simulated with
    and, for a zone of a Model example, the apparent power the configuration declares for it."""
    source = dict(_read_ini(dynawo_path / "Producer.ini").defaults())
    lines = [_PRODUCER_HEADER.format(source=dynawo_path)]
    for key, comment in _DTR_MAGNITUDES:
        if key in source:
            lines.append(f"# {comment}\n{key} = {source[key]}\n")
    lines.append(
        "# Generator type in the original network (SM, PPM or BESS)\n"
        f"generator_type = {generator_type}\n"
    )
    if zone:
        s_nom = _read_ini(CONFIGURATION).get(f"Producer.{generator_type}", f"{zone}.s_nom")
        lines.append(
            "# Nominal apparent power of the producer (in MVA), the one its model declares\n"
            f"s_nom = {s_nom}\n"
        )
    return "".join(lines)


def _f16_operating_condition(benchmark: tuple, level: str, pdr_p: str, active_step: str) -> str:
    name, _, test_type, connect_to, step_size = benchmark
    step = active_step if test_type == "PSetpoint" else _F16_VOLTAGE_STEP
    return f"""
[PCS_RTE-F16z3.{name}.{level}]
report_name = report.F16z3.DeclaredTest.tex
reference_step_size = {step_size}
bolted_fault = false
hiz_fault = false
setpoint_change_test_type = {test_type}

[PCS_RTE-F16z3.{name}.{level}.Model]
line_XPu = b
pdr_P = {pdr_p}
pdr_Q = 0
pdr_U = Udim

[PCS_RTE-F16z3.{name}.{level}.Event]
connect_event_to = {connect_to}
sim_t_event_start = 20
setpoint_step_value = {step}
"""


def f16_declaration(generator_type: str) -> str:
    """The ``F16Description.ini`` of an example: the on-site tests it declares as recorded, at
    the power levels the configuration gives for this kind of producer."""
    section = _read_ini(CONFIGURATION)[f"F16.{generator_type}"]
    levels = [
        (level, *(value.strip() for value in section[level].split(",")))
        for level in section
        if level != "label"
    ]
    names = [benchmark[0] for benchmark in _F16_BENCHMARKS]
    both = ",".join(f"PCS_RTE-F16z3.{name}" for name in names)

    lines = [
        _F16_HEADER,
        "\n# One benchmark per kind of recorded test (setpoint step, fault, dip, swell, ramp,"
        f" islanding)\n[PCS-Benchmarks]\nPCS_RTE-F16z3 = {','.join(names)}\n",
        "\n# One operating condition per benchmark and active power level recorded\n"
        "[PCS-OperatingConditions]\n",
    ]
    lines.extend(
        f"PCS_RTE-F16z3.{name} = {','.join(level for level, _, _ in levels)}\n" for name in names
    )

    for benchmark in _F16_BENCHMARKS:
        name, job = benchmark[0], benchmark[1]
        lines.append(
            "\n# A benchmark: the grid simulated on the TSO side and the kind of event\n"
            f"[PCS_RTE-F16z3.{name}]\n"
            f"job_name = PCS F16-Zone3 ({section['label']}) - {job}\n"
            "TSO_model = RefTracking_1Line_InfBus\n"
            "Omega_model = SetPoint\n"
        )
        lines.extend(_f16_operating_condition(benchmark, *level) for level in levels)

    lines.append(
        "\n# The compliance tests, each one listing the benchmarks it applies to\n"
        "[Model-Validations]\n"
    )
    lines.extend(f"{check} = {both}\n" for check in _F16_CHECKS)
    lines.append(
        "\n# The figures of the report, each one listing the benchmarks it is drawn for\n"
        "[ReportCurves]\n"
    )
    lines.extend(f"{figure} = {both}\n" for figure in _F16_FIGURES)
    return "".join(lines)


_ANNOUNCED_RECORD = """# The record this test was run with. Written by
# tools/scripts/example_inputs.py to announce it: a declared test of Fiche F16 is only run where
# its record exists, so the dictionary comes first and the run replaces it with the one its own
# curves describe.

[Curves-Metadata]
# True when the reference curves are field measurements
is_field_measurements = False
# Instant of time at which the event or fault starts
sim_t_event_start = {start}
# Duration of the event or fault
fault_duration = 0.0

[Curves-Dictionary]
time = time
"""


def declared_tests(declaration: Path) -> list:
    """Every test a declaration names, as ``PCS.benchmark.operating_condition``."""
    parser = _read_ini(declaration)
    tests = []
    for pcs, benchmarks in parser.items("PCS-Benchmarks"):
        for benchmark in filter(None, (value.strip() for value in benchmarks.split(","))):
            conditions = parser.get("PCS-OperatingConditions", f"{pcs}.{benchmark}")
            tests.extend(
                f"{pcs}.{benchmark}.{condition.strip()}"
                for condition in filter(None, conditions.split(","))
            )
    return tests


def announce_records(declaration: Path, reference_path: Path, model_path: Path, kind: str) -> int:
    """Announces the records of every test a declaration names: the index of the delivery, which
    the tool writes from the model, and a dictionary per test, which is what makes the tool run
    the test at all. Returns how many tests it announced."""
    from dycov.files.producer_curves import create_producer_curves

    producer_path = reference_path / "Producer"
    producer_path.mkdir(parents=True, exist_ok=True)
    if not (producer_path / "CurvesFiles.ini").is_file():
        create_producer_curves(model_path, reference_path, f"model_{kind}")

    parser = _read_ini(declaration)
    announced = 0
    for test in declared_tests(declaration):
        dictionary = producer_path / f"{test}.dict"
        if dictionary.is_file():
            continue
        start = parser.get(f"{test}.Event", "sim_t_event_start", fallback="20")
        dictionary.write_text(_ANNOUNCED_RECORD.format(start=start), encoding="utf-8")
        announced += 1
    return announced


_IMAX_COMMENT = "# Maximum injected current of the generator, which the fault test checks"


def declare_field_measurements(declaration: Path, producer_path: Path) -> int:
    """Says in the record of every test a declaration names that it was measured on site, which
    is what a test of Fiche F16 is. The anonymizer writes False into every dictionary, because
    what it anonymized was simulated — true of these records and beside the point: what the
    example shows is a delivery of on-site tests, and the tool reads the flag to decide how to
    treat them. Returns how many records it corrected."""
    corrected = 0
    for test in declared_tests(declaration):
        dictionary = producer_path / f"{test}.dict"
        if not dictionary.is_file():
            continue
        lines = dictionary.read_text(encoding="utf-8").splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("is_field_measurements") and "True" not in line:
                lines[index] = "is_field_measurements = True\n"
                dictionary.write_text("".join(lines), encoding="utf-8")
                corrected += 1
                break
    return corrected


def declare_imax(producer_path: Path, kind: str) -> int:
    """Writes into the dictionary of each test that reads it the maximum injected current of the
    generator. The anonymizer cannot: no curve carries it, and it is a value of the producer.
    Returns how many dictionaries it wrote it into."""
    configuration = _read_ini(CONFIGURATION)
    if not configuration.has_section(f"Imax.{kind}"):
        return 0

    section = configuration[f"Imax.{kind}"]
    declaration = f"{section['generator']}_GEN_MaxInjectedCurrentPu = {section['value']}"
    written = 0
    for test in filter(None, (value.strip() for value in section["tests"].split(","))):
        dictionary = producer_path / f"{test}.dict"
        if not dictionary.is_file():
            raise SystemExit(
                f"{dictionary}: the test that reads the maximum current has no record."
            )
        lines = dictionary.read_text(encoding="utf-8").splitlines(keepends=True)
        if any(line.startswith(declaration.split(" =")[0]) for line in lines):
            continue
        for index, line in enumerate(lines):
            if line.startswith("[Curves-Dictionary]"):
                lines[index:index] = [f"{_IMAX_COMMENT}\n", f"{declaration}\n", "\n"]
                break
        dictionary.write_text("".join(lines), encoding="utf-8")
        written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="what", required=True)

    producer = subparsers.add_parser("producer", help="write a curve directory's Producer.ini")
    producer.add_argument("--model", type=Path, required=True, help="the model of the curves")
    producer.add_argument("--type", required=True, choices=("SM", "PPM", "BESS"))
    producer.add_argument("--zone", default="", help="the zone whose apparent power to declare")
    producer.add_argument("--output", type=Path, required=True)

    f16 = subparsers.add_parser("f16", help="write an example's F16Description.ini")
    f16.add_argument("--type", required=True, choices=("PPM", "BESS"))
    f16.add_argument("--output", type=Path, required=True)

    announce = subparsers.add_parser(
        "announce", help="announce the records of every test a declaration names"
    )
    announce.add_argument("--declaration", type=Path, required=True)
    announce.add_argument("--reference", type=Path, required=True, help="where the records go")
    announce.add_argument("--model", type=Path, required=True, help="the model that is recorded")
    announce.add_argument("--type", required=True, choices=("PPM", "BESS"))

    measured = subparsers.add_parser(
        "field-measurements", help="say in the records of a declaration that they were measured"
    )
    measured.add_argument("--declaration", type=Path, required=True)
    measured.add_argument("--producer", type=Path, required=True, help="where the records are")

    imax = subparsers.add_parser(
        "imax", help="declare the generator's maximum injected current in the tests that read it"
    )
    imax.add_argument("--producer", type=Path, required=True, help="the directory of the records")
    imax.add_argument("--type", required=True, choices=("SM", "PPM", "BESS"))

    arguments = parser.parse_args()
    if arguments.what == "field-measurements":
        corrected = declare_field_measurements(arguments.declaration, arguments.producer)
        print(f"  {corrected} records said to be measured on site")
        return
    if arguments.what == "imax":
        print(
            f"  {declare_imax(arguments.producer, arguments.type)} tests given a maximum current"
        )
        return
    if arguments.what == "announce":
        announced = announce_records(
            arguments.declaration, arguments.reference, arguments.model, arguments.type
        )
        print(f"  {announced} tests announced in {arguments.reference}")
        return

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    if arguments.what == "producer":
        content = producer_declaration(arguments.model, arguments.type, arguments.zone)
    else:
        content = f16_declaration(arguments.type)
    arguments.output.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
