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
MODEL_DIR = re.compile(r"\*\*\*Model dir: .*examples/Model/(.+?)/Dynawo\*\*\*")


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


def executed_tests(log_path: Path) -> dict:
    """The tests each example reports. An example whose zones are split among producers reports
    the same test once per producer, so they are gathered as a set."""
    executed = defaultdict(set)
    example = None
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        model_dir = MODEL_DIR.search(line)
        if model_dir:
            example = model_dir.group(1)
        elif example and line.startswith("Producer") and "PCS_RTE-" in line:
            executed[example].add(tuple(line.split()[1:4]))
    return executed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="the log of the run")
    parser.add_argument("--examples", nargs="+", required=True, help="the examples that ran")
    arguments = parser.parse_args()

    executed = executed_tests(arguments.log)
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
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
