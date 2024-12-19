from pathlib import Path

from dgcv.configuration.cfg import config
from dgcv.core.execution_parameters import Parameters
from dgcv.curves.curves import ImportedCurves
from dgcv.dynawo.curves import DynawoCurves


def get_producer_curves(
    parameters: Parameters,
    pcs_benchmark_name: str,
    stable_time: float,
    lib_path: Path,
    templates_path: Path,
    pcs_name: str,
):
    producer = parameters.get_producer()
    if producer.is_dynawo_model():
        job_name = config.get_value(pcs_benchmark_name, "job_name")
        rte_model = config.get_value(pcs_benchmark_name, "TSO_model")
        omega_model = config.get_value(pcs_benchmark_name, "Omega_model")

        file_path = Path(__file__).resolve().parent.parent
        sim_type_path = producer.get_sim_type_str()
        model_path = file_path / lib_path / "TSO_model" / rte_model
        omega_path = file_path / lib_path / "Omega" / omega_model
        pcs_path = file_path / templates_path / sim_type_path / pcs_name
        if not pcs_path.exists():
            pcs_path = config.get_config_dir() / templates_path / sim_type_path / pcs_name

        return DynawoCurves(
            parameters,
            pcs_name,
            model_path,
            omega_path,
            pcs_path,
            job_name,
            stable_time,
        )
    elif producer.is_user_curves():
        return ImportedCurves(parameters)

    raise ValueError("Unsupported producer curves")
