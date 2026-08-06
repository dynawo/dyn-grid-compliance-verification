import pytest
import numpy as np
from unittest.mock import MagicMock

from dycov.gfm.gfm import GridForming
from dycov.gfm.calculators import calculator_factory
from dycov.gfm.calculators.phase_jump import PhaseJump


def test_calculator_factory_returns_correct_instance():
    """
    Checks that the factory correctly instantiates the PhaseJump calculator.
    """
    # 1. Arrange: Mock the parameters to isolate the test without loading actual files
    mocked_parameters = MagicMock()

    # 2. Act: Call the factory with a specific calculator name
    calculator = calculator_factory.get_calculator("PhaseJump", mocked_parameters)

    # 3. Assert: Verify the returned object type is accurate
    assert isinstance(calculator, PhaseJump), "The factory did not return a PhaseJump object."


def test_merge_hybrid_envelopes_mathematical_logic():
    """
    Verifies that the hybrid logic extraction merges the envelopes
    correctly using the Maximum and Minimum boundary rules.
    """
    # 1. Arrange: Create simple simulated numpy arrays
    gfm = GridForming()
    up_over = np.array([1.0, 2.0])
    low_over = np.array([-1.0, -2.0])
    up_under = np.array([1.5, 1.5])
    low_under = np.array([-1.5, -1.5])

    # 2. Act: Execute the newly refactored method
    upper_result, lower_result = gfm._merge_hybrid_envelopes(
        up_over, low_over, up_under, low_under
    )

    # 3. Assert: Verify the expected mathematical outcome
    # The maximum of upper bounds is [1.5, 2.0]. The minimum of lower bounds is [-1.5, -2.0]
    np.testing.assert_array_equal(upper_result, np.array([1.5, 2.0]))
    np.testing.assert_array_equal(lower_result, np.array([-1.5, -2.0]))
