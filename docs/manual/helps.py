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

    with open(output_path / "dgcv.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dgcv", "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        write_output(file, output.stdout)

    with open(output_path / "anonymize.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dgcv", "anonymize", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "compile.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dgcv", "compile", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "generate.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dgcv", "generate", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "performance.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dgcv", "performance", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)

    with open(output_path / "validate.rst", "w") as file:
        file.write(".. code-block:: console\n\n")
        output = subprocess.run(
            ["dgcv", "validate", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        write_output(file, output.stdout)


if __name__ == "__main__":
    sys.exit(generate_help_files())
