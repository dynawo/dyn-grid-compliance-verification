import subprocess
import sys
from pathlib import Path

# Every command whose --help the manual includes; the main entry point has no subcommand.
COMMANDS = [
    "",
    "anonymize",
    "excel2inputs",
    "generate",
    "generateEnvelopes",
    "performance",
    "validate",
]


def write_output(file, text):
    for line in text.splitlines():
        file.write(f"\t{line}\n")
    file.write("\n")


def generate_help_files():
    output_path = Path(__file__).parent / "source" / "usage" / "helps"
    output_path.mkdir(parents=True, exist_ok=True)

    for command in COMMANDS:
        with open(output_path / f"{command or 'dycov'}.rst", "w") as file:
            file.write(".. code-block:: console\n\n")
            output = subprocess.run(
                ["dycov"] + ([command] if command else []) + ["--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            write_output(file, output.stdout)


if __name__ == "__main__":
    sys.exit(generate_help_files())
