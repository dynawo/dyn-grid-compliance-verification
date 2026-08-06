import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock
from dycov.gfm.gfm import GridForming

def test_csv_generation_does_not_alter_results(tmp_path):
    """
    Executes the full generation lifecycle and compares the resulting CSV
    with a baseline CSV to ensure no functional regressions were introduced.
    """
    # 1. Arrange: Set up the environment
    gfm = GridForming()
    temporal_working_path = tmp_path  # pytest automatically provides a secure temporary folder
    
    # Mock the parameters required to run the 'generate' method safely
    mock_params = MagicMock()
    mock_params.get_calculator_name.return_value = "PhaseJump"
    mock_params.get_hybrid_parameters.return_value = None
    mock_params.get_standard_parameters.return_value = (0.5, 4.0)  # Standard (D, H)
    mock_params.get_effective_reactance.return_value = 0.2
    mock_params.should_save_all_envelopes.return_value = False
    
    # IMPORTANT: You must define the path to your original "gold standard" CSV here
    baseline_csv_path = Path("tests/baselines/PCS1.BM1.OC1.csv") 
    
    # 2. Act: Run the full GFM generation process
    # Note: If your calculations rely on a real 'producer', ensure your mocked 
    # parameters accurately reflect a real test case.
    gfm.generate(
        working_path=temporal_working_path,
        parameters=mock_params,
        pcs_name="PCS1",
        bm_name="BM1",
        oc_name="OC1"
    )
    
    # 3. Assert: Compare the newly generated file against the baseline
    generated_csv_path = temporal_working_path / "PCS1.BM1.OC1.csv"
    
    # Read both files using pandas, which elegantly handles floating-point tolerances
    df_generated = pd.read_csv(generated_csv_path, sep=";")
    df_baseline = pd.read_csv(baseline_csv_path, sep=";")
    
    # This assertion will fail immediately if there is even the slightest
    # mathematical difference, missing column, or row misalignment.
    pd.testing.assert_frame_equal(df_generated, df_baseline)