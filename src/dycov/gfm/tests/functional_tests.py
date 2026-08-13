import pandas as pd
from pathlib import Path
from typing import Tuple


def compare_csv_directories(baseline_dir: Path, output_dir: Path) -> Tuple[bool, str]:
    """
    Recursively compares all CSV files from a baseline directory against an output directory.
    Returns a boolean indicating success, and an error message string if it fails.
    """
    baseline_csvs = list(baseline_dir.rglob("*.csv"))

    if not baseline_csvs:
        return (
            False,
            f"Setup Error: No CSV files were found in the baseline directory '{baseline_dir}'.",
        )

    for baseline_csv in baseline_csvs:
        relative_path = baseline_csv.relative_to(baseline_dir)
        output_csv = output_dir / relative_path

        # 1. Structural Validation
        if not output_csv.exists():
            return False, f"Missing File Error: Expected output file not found at '{output_csv}'."

        # 2. Data Extraction
        try:
            df_baseline = pd.read_csv(baseline_csv, sep=";")
        except Exception as e:
            return (
                False,
                f"I/O Error: Could not read baseline CSV at '{baseline_csv}'. Details: {e}",
            )

        try:
            df_output = pd.read_csv(output_csv, sep=";")
        except Exception as e:
            return False, f"I/O Error: Could not read output CSV at '{output_csv}'. Details: {e}"

        # 3. Mathematical Validation
        try:
            pd.testing.assert_frame_equal(
                df_baseline, df_output, check_exact=False, rtol=1e-5, atol=1e-8
            )
        except AssertionError as e:
            return False, f"Data Mismatch Error in file '{relative_path}':\n{e}"

    return True, ""


# ==========================================
# Example usage within a pytest framework
# ==========================================


def test_dynamic_directory_output_generation(tmp_path):
    """
    Executes the generation lifecycle and dynamically compares the nested output directories.
    """
    # In your actual test, this path should point to your reference baseline folder
    baseline_directory = Path("tests/baselines")

    # Example: 'tmp_path' is provided by pytest as a secure, temporary output folder.
    # Here is where your script would output the new generated folders and files.
    output_directory = tmp_path / "simulation_results"

    # --- RUN YOUR GENERATION CODE HERE ---
    # e.g., gfm_generation.generate(output_directory, ...)
    # -------------------------------------

    # Validate that the entire output structure and data match the baseline
    # Uncomment the following line when your generation step is successfully integrated:

    # compare_csv_directories(baseline_dir=baseline_directory, output_dir=output_directory)
