#!/usr/bin/env python3
import os
from pathlib import Path

from ast_inventory import collect_public_methods
from run_mypy import run_mypy
from run_pydocstyle import run_pydocstyle

from cross_check import cross_check

# Always run from repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
os.chdir(REPO_ROOT)

OUTPUT_FILE = Path("public_api_audit.txt")


def main():
    methods = collect_public_methods()
    mypy_lines = run_mypy()
    pydoc_lines = run_pydocstyle()

    findings = cross_check(methods, mypy_lines, pydoc_lines)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for m in findings:
            f.write(f"{m['file']}:{m['name']} " f"({m['start']}-{m['end']})\n")

            if m["typing_lines"]:
                lines = ", ".join(map(str, sorted(set(m["typing_lines"]))))
                f.write(f"  - falta typing (mypy: línea {lines})\n")

            if m["docstring_lines"]:
                lines = ", ".join(map(str, sorted(set(m["docstring_lines"]))))
                f.write(f"  - falta docstring (pydocstyle: línea {lines})\n")

            f.write("\n")

    print(f"✅ Public API audit written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
