import subprocess
import sys
from pathlib import Path


def write_output(file, text):
    for line in text.splitlines():
        file.write(f"\t{line}\n")
    file.write("\n")


def generate_help_files():
    output_path = Path(__file__).parent / "source" / "usage" / "helps"
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "dycov.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dycov", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        write_output(file, output.stdout)

    with open(output_path / "anonymize.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dycov", "anonymize", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "generate.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dycov", "generate", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "performance.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dycov", "performance", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "validate.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dycov", "validate", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)


if __name__ == "__main__":
    sys.exit(generate_help_files())
