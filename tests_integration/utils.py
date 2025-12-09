import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from dycov.configuration.cfg import config
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dycov.validate.parameters import ValidationParameters
from dycov.validate.validation import Validation

PERFORMANCE = "../examples/Performance"
MODEL = "../examples/Model"
RESOURCES = "./resources"


def execute_tool(producer_model_path, producer_curves_path, reference_curves_path):
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
            old_timeout = config.get_float("Dynawo", "simulation_limit", 30.0)
            config.set_value("Dynawo", "simulation_limit", str(10.0))
            only_dtr = True
            if producer_model_path:
                sim_type = (
                    ELECTRIC_PERFORMANCE
                    if "Performance" in producer_model_path
                    else MODEL_VALIDATION
                )
            else:
                sim_type = (
                    ELECTRIC_PERFORMANCE
                    if "Performance" in producer_curves_path
                    else MODEL_VALIDATION
                )

            # Buscar DYNAWOPATH o dynawo.sh
            dynawo_path = os.getenv("DYNAWOPATH")
            if not dynawo_path:
                dynawo_path = shutil.which("dynawo.sh")

            if not dynawo_path:
                return "Validation skipped: DYNAWOPATH not set and dynawo.sh not found."

            params = ValidationParameters(
                Path(dynawo_path).resolve(),
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
            compliance = md.validate(use_parallel=True, num_processes=4)
        except Exception as e:
            compliance = str(e)
        finally:
            config.set_value("Dynawo", "simulation_limit", str(old_timeout))
            return compliance
