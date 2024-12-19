from pathlib import Path

from dgcv.core.execution_parameters import Parameters
from dgcv.curves.curves import ImportedCurves
from dgcv.curves.producer_factory import get_producer_curves


class CurvesManager:
    def __init__(
        self,
        parameters: Parameters,
        pcs_benchmark_name: str,
        stable_time: float,
        lib_path: Path,
        templates_path: Path,
        pcs_name: str,
    ):
        self._producer_curves = get_producer_curves(
            parameters, pcs_benchmark_name, stable_time, lib_path, templates_path, pcs_name
        )
        self._reference_curves = ImportedCurves(parameters)

    def get_producer_curves(self):
        return self._producer_curves

    def get_reference_curves(self):
        return self._reference_curves
