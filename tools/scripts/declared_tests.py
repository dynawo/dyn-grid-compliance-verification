"""Checks that a run of the Model examples covered every test the PCS of the tool declare.

A selection of PCS, of benchmarks or of operating conditions anywhere — in the configuration of
the machine, in a template of the user — produces fewer tests without saying so, and the curves
of the rest would then be written by nothing.

What must run is what the PCS of the tool declare plus what the example declares for itself: the
tests of Fiche F16, which the fiche does not fix and regenerate_f16.sh writes into the example
before the run. The PCS of the tool are read as the revision of the DTR the run followed writes
them for the category of the installation of the example, and a test they run only when it is
recorded is not one that must run.
"""

import argparse
import configparser
import re
import sys
from collections import defaultdict
from pathlib import Path

from dycov.configuration.cfg import config
from dycov.electrical.generator_variables import generator_variables

PACKAGE_TEMPLATES = Path("src/dycov/templates")
TEMPLATES = PACKAGE_TEMPLATES / "PCS/model"
CONFIGURATION = Path(__file__).resolve().parent / "example_inputs.ini"
MODEL_DIR = re.compile(r"\*\*\*Model dir: .*examples/Model/(.+?)/Dynawo\*\*\*")
DTR_REVISION = re.compile(r"Validating against the DTR revision (\w+)\.")

# Where the summary of a run says how each test ended. The columns before it are fixed-width:
# producer, PCS, benchmark and operating condition.
VERDICT_AT = 20 + 15 + 25 + 40

# A test that ran and fell over, and so has no curve to ship. The ones that did run are still
# worth writing — an example is more useful with the curves it has than with none — so these are
# named, every time, and the count of them travels with the example. A test that did not run at
# all is another matter: something selected what to verify, and that stops the regeneration.
FELL_OVER = (
    "Invalid test",
    "Failed simulation",
    "Undefined validations",
    "Fault simulation fails",
    "Fault dip unachievable",
    "Simulation time out",
    "Missing the simulated voltage curve",
)


def names_in(value: str) -> list:
    """The names of a list of the configuration. The word ``none`` means a list with nothing
    in it, which an empty value cannot say, and a revision that withdraws a fiche writes it."""
    if value is None or value.strip().lower() == "none":
        return []
    return [name for name in value.split(",") if name]


def delta_of(description: Path, revision: str) -> Path:
    """The description the selected revision of the DTR writes for the same PCS, if it writes
    one. The delta of a revision mirrors the shipped templates, and the base has none."""
    try:
        inside = description.relative_to(PACKAGE_TEMPLATES)
    except ValueError:
        return None

    delta = PACKAGE_TEMPLATES / "revisions" / revision / inside
    return delta if delta.is_file() else None


def installation_category(example: str, revision: str) -> str:
    """The category the DTR gives the installation of an example, from the INI of its Zone 3,
    as the revision of the DTR the run followed draws the line between the categories."""
    producer = configparser.ConfigParser(inline_comment_prefixes=("#",))
    producer.read(Path("examples/Model", example, "Dynawo", "Zone3", "Producer.ini"))
    config.set_value("DTR", "current", revision)
    config.load_dtr_delta_config(revision)
    return generator_variables.get_generator_category(
        producer.getfloat("DEFAULT", "u_nom"),
        producer.getfloat("DEFAULT", "p_max_injection"),
        example.startswith("BESS/"),
    )


def version_of(description: Path, revision: str, category: str) -> list:
    """The version of a PCS the revision writes for the category of the installation, which
    patches its delta, as the tool picks it: a Type<categories>.ini beside the delta whose name
    holds the category."""
    try:
        inside = description.parent.relative_to(PACKAGE_TEMPLATES)
    except ValueError:
        return []

    versions = sorted((PACKAGE_TEMPLATES / "revisions" / revision / inside).glob("Type*.ini"))
    return [version for version in versions if category in version.stem[len("Type") :]][:1]


def declared_tests(family: str, example: str, revision: str) -> set:
    """The operating conditions the PCS of a family declare for a revision of the DTR, which is
    what must run, plus the ones the example declares with its reference curves."""
    declared = set()
    category = installation_category(example, revision)
    descriptions = sorted((TEMPLATES / family).glob("[!.]*/PCSDescription.ini")) + sorted(
        Path("examples/Model", example, "ReferenceCurves").glob("*Description.ini")
    )
    for description in descriptions:
        pcs_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        pcs_config.optionxform = str
        pcs_config.read(description)
        # A delta overlays the description key by key, and a version the delta, which is what
        # each further read does.
        delta = delta_of(description, revision)
        if delta is not None:
            pcs_config.read(delta)
        pcs_config.read(version_of(description, revision, category))

        for pcs, benchmarks in pcs_config.items("PCS-Benchmarks"):
            for benchmark in names_in(benchmarks):
                conditions = pcs_config.get(
                    "PCS-OperatingConditions", f"{pcs}.{benchmark}", fallback=""
                )
                declared.update(
                    (pcs, benchmark, oc)
                    for oc in names_in(conditions)
                    if not pcs_config.getboolean(
                        f"{pcs}.{benchmark}.{oc}", "only_with_reference", fallback=False
                    )
                )
    return declared


def executed_tests(log_path: Path) -> tuple[dict, dict, str]:
    """The tests each example reports, how each one ended, and the revision of the DTR the run
    followed. An example whose zones are split among producers reports the same test once per
    producer, so they are gathered as a set."""
    executed = defaultdict(set)
    fell_over = defaultdict(set)
    example = None
    revision = ""
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        selected = DTR_REVISION.search(line)
        if selected:
            revision = selected.group(1)
        model_dir = MODEL_DIR.search(line)
        if model_dir:
            example = model_dir.group(1)
        elif example and line.startswith("Producer") and "PCS_RTE-" in line:
            test = tuple(line.split()[1:4])
            executed[example].add(test)
            verdict = line[VERDICT_AT:].strip()
            if verdict in FELL_OVER:
                fell_over[example].add((".".join(test), verdict))
    return executed, fell_over, revision


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="the log of the run")
    parser.add_argument("--examples", nargs="+", required=True, help="the examples that ran")
    arguments = parser.parse_args()

    executed, fell_over, revision = executed_tests(arguments.log)
    if not revision:
        print(f"The log {arguments.log} does not say which revision of the DTR the run followed.")
        sys.exit(1)

    declared_total = covered_total = 0
    missing = {}
    for example in arguments.examples:
        family = "BESS" if example.startswith("BESS/") else "PPM"
        declared = declared_tests(family, example, revision)
        declared_total += len(declared)
        covered_total += len(declared & executed[example])
        if declared - executed[example]:
            missing[example] = sorted(declared - executed[example])

    print(
        f"Tests: {covered_total} executed, {declared_total} declared for the examples "
        f"by the DTR revision {revision}."
    )
    for example, tests in missing.items():
        print(f"  {example} never ran " + ", ".join(".".join(test) for test in tests))
    for example, tests in sorted(fell_over.items()):
        for test, verdict in sorted(tests):
            print(f"  no curve for {example} {test}: {verdict}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
