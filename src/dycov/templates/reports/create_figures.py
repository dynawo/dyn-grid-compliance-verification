import json
import shutil
import sys
from pathlib import Path

from dycov.core.global_variables import (
    ELECTRIC_PERFORMANCE_BESS,
    ELECTRIC_PERFORMANCE_SM,
    MODEL_VALIDATION_BESS,
)


def _get_pcs_name(pcs_name, simulation_type):
    pcs = pcs_name.replace("PCS_", "")
    if simulation_type == ELECTRIC_PERFORMANCE_SM:
        return pcs + "SM"
    if simulation_type == ELECTRIC_PERFORMANCE_BESS:
        return pcs + "BESS"
    if simulation_type == MODEL_VALIDATION_BESS:
        return pcs + "BESS"

    return pcs


def _get_pcs_figures(pcs):
    with open(Path(__file__).parent / "figures.json", "r") as f:
        figures = json.load(f)

        if pcs in figures:
            return figures[pcs]

    return []


def _create_pcs_figures(path, pcs, producer):
    figures = _get_pcs_figures(pcs)
    for figure in figures:
        shutil.copy(path / "fig_placeholder.pdf", path / f"{producer}_{figure}")


def create_figures(path, producer, pcs_name, simulation_type):
    pcs = _get_pcs_name(pcs_name, simulation_type)
    _create_pcs_figures(path, pcs, producer)


if __name__ == "__main__":
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    pcs = sys.argv[3]
    _create_pcs_figures(source, target, pcs)
