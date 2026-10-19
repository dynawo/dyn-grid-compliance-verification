"""Checks that a run of the Model examples covered every test the PCS of the tool declare.

A selection of PCS, of benchmarks or of operating conditions anywhere — in the configuration of
the machine, in a template of the user — produces fewer tests without saying so, and the curves
of the rest would then be written by nothing.

What must run is what the PCS of the tool declare plus what the example declares for itself: the
tests of Fiche F16, which the fiche does not fix and regenerate_f16.sh writes into the example
before the run.
"""

import argparse
import configparser
import re
import sys
from collections import defaultdict
from pathlib import Path

TEMPLATES = Path("src/dycov/templates/PCS/model")
CONFIGURATION = Path(__file__).resolve().parent / "example_inputs.ini"
MODEL_DIR = re.compile(r"\*\*\*Model dir: .*examples/Model/(.+?)/Dynawo\*\*\*")

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


def declared_tests(family: str, example: str) -> set:
    """The operating conditions the PCS of a family declare, which is what must run, plus the
    ones the example declares with its reference curves."""
    declared = set()
    descriptions = sorted((TEMPLATES / family).glob("[!.]*/PCSDescription.ini")) + sorted(
        Path("examples/Model", example, "ReferenceCurves").glob("*Description.ini")
    )
    for description in descriptions:
        pcs_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        pcs_config.optionxform = str
        pcs_config.read(description)
        for pcs, benchmarks in pcs_config.items("PCS-Benchmarks"):
            for benchmark in filter(None, benchmarks.split(",")):
                conditions = pcs_config.get("PCS-OperatingConditions", f"{pcs}.{benchmark}")
                declared.update((pcs, benchmark, oc) for oc in conditions.split(","))
    return declared


def executed_tests(log_path: Path) -> tuple[dict, dict]:
    """The tests each example reports and how each one ended. An example whose zones are split
    among producers reports the same test once per producer, so they are gathered as a set."""
    executed = defaultdict(set)
    fell_over = defaultdict(set)
    example = None
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        model_dir = MODEL_DIR.search(line)
        if model_dir:
            example = model_dir.group(1)
        elif example and line.startswith("Producer") and "PCS_RTE-" in line:
            test = tuple(line.split()[1:4])
            executed[example].add(test)
            verdict = line[VERDICT_AT:].strip()
            if verdict in FELL_OVER:
                fell_over[example].add((".".join(test), verdict))
    return executed, fell_over


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="the log of the run")
    parser.add_argument("--examples", nargs="+", required=True, help="the examples that ran")
    arguments = parser.parse_args()

    executed, fell_over = executed_tests(arguments.log)
    declared_total = covered_total = 0
    missing = {}
    for example in arguments.examples:
        declared = declared_tests("BESS" if example.startswith("BESS/") else "PPM", example)
        declared_total += len(declared)
        covered_total += len(declared & executed[example])
        if declared - executed[example]:
            missing[example] = sorted(declared - executed[example])

    print(f"Tests: {covered_total} executed, {declared_total} declared for the examples.")
    for example, tests in missing.items():
        print(f"  {example} never ran " + ", ".join(".".join(test) for test in tests))
    for example, tests in sorted(fell_over.items()):
        for test, verdict in sorted(tests):
            print(f"  no curve for {example} {test}: {verdict}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
