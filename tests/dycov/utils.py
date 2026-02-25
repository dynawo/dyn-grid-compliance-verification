import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from dycov.configuration.cfg import config
from dycov.core.global_variables import ELECTRIC_PERFORMANCE, MODEL_VALIDATION
from dycov.validate.parameters import ValidationParameters
from dycov.validate.validation import Validation

PERFORMANCE = Path(__file__).resolve().parent.parent.parent / "examples" / "Performance"
MODEL = Path(__file__).resolve().parent.parent.parent / "examples" / "Model"


def _resolve_dynawo_sh():
    env_path = os.environ.get("DYNAWOPATH")
    if env_path:
        candidate = Path(env_path) / "dynawo.sh"
        if candidate.exists():
            return candidate.resolve()

    found = shutil.which("dynawo.sh")
    return Path(found).resolve() if found else None


def execute_tool(
    producer_model_path: Path | None,
    producer_curves_path: Path | None,
    reference_curves_path: Path | None,
):
    with TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        assert output_dir.exists()
        if producer_model_path:
            assert producer_model_path.exists()
        if producer_curves_path:
            assert producer_curves_path.exists()
        if reference_curves_path:
            assert reference_curves_path.exists()

        try:
            old_timeout = config.get_float("Dynawo", "simulation_limit", 30.0)
            config.set_value("Dynawo", "simulation_limit", str(10.0))
            only_dtr = True
            if producer_model_path:
                if "Performance" in str(producer_model_path):
                    sim_type = ELECTRIC_PERFORMANCE
                else:
                    sim_type = MODEL_VALIDATION
            else:
                if "Performance" in str(producer_curves_path):
                    sim_type = ELECTRIC_PERFORMANCE
                else:
                    sim_type = MODEL_VALIDATION

            dynawo_sh = _resolve_dynawo_sh()

            params = ValidationParameters(
                dynawo_sh,
                producer_model_path if producer_model_path else None,
                producer_curves_path if producer_curves_path else None,
                reference_curves_path if reference_curves_path else None,
                None,
                output_dir,
                only_dtr,
                sim_type,
            )
            md = Validation(params, dry_run=True)
            md.set_testing(True)
            compliance = md.validate(use_parallel=True, num_processes=4)
        except Exception as e:
            compliance = str(e)
        finally:
            config.set_value("Dynawo", "simulation_limit", str(old_timeout))
            return compliance
