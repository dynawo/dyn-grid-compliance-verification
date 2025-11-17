import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dycov.validate.parameters import ValidationParameters
from dycov.validate.validation import Validation

PERFORMANCE = "../examples/Performance"
MODEL = "../examples/Model"
RESOURCES = "./resources"


def _execute_tool(producer_model_path, producer_curves_path, reference_curves_path):
    testpath = Path(__file__).resolve().parent
    with TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        assert output_dir.exists()
        if producer_model_path:
            assert (testpath / producer_model_path).exists()
        if producer_curves_path:
            assert (testpath / producer_curves_path).exists()
        if reference_curves_path:
            assert (testpath / reference_curves_path).exists()

        try:
            only_dtr = True
            if producer_model_path:
                if "Performance" in producer_model_path:
                    sim_type = ELECTRIC_PERFORMANCE
                else:
                    sim_type = MODEL_VALIDATION
            else:
                if "Performance" in producer_curves_path:
                    sim_type = ELECTRIC_PERFORMANCE
                else:
                    sim_type = MODEL_VALIDATION

            params = ValidationParameters(
                Path(shutil.which("dynawo.sh")).resolve() if shutil.which("dynawo.sh") else None,
                testpath / producer_model_path if producer_model_path else None,
                testpath / producer_curves_path if producer_curves_path else None,
                testpath / reference_curves_path if reference_curves_path else None,
                None,
                output_dir,
                only_dtr,
                sim_type,
            )
            md = Validation(params)
            md.set_testing(True)
            compliance = md.validate(use_parallel=False, num_processes=4)
        except Exception as e:
            compliance = str(e)
        finally:
            return compliance
