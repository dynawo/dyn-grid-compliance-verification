import json
import shutil
import sys
from pathlib import Path

ELECTRIC_PERFORMANCE_SM = 0
ELECTRIC_PERFORMANCE_PPM = 1
MODEL_VALIDATION_PPM = 10


def get_pcs_name(pcs_name, simulation_type):
    pcs = pcs_name.replace("PCS_", "")
    if simulation_type == ELECTRIC_PERFORMANCE_SM:
        return pcs + "SM"
    elif simulation_type == ELECTRIC_PERFORMANCE_PPM:
        return pcs + "PPM"

    return pcs


def get_pcs_figures(pcs):
    with open(Path(__file__).parent / "figures.json", "r") as f:
        figures = json.load(f)

        if pcs in figures:
            return figures[pcs]

    return []


def create_pcs_figures(path, pcs):
    figures = get_pcs_figures(pcs)
    for figure in figures:
        shutil.copy(path / "fig_placeholder.pdf", path / figure)


def create_figures(path, pcs_name, simulation_type):
    pcs = get_pcs_name(pcs_name, simulation_type)
    create_pcs_figures(path, pcs)


if __name__ == "__main__":
    source = Path(sys.argv[1])
    target = Path(sys.argv[2])
    pcs = sys.argv[3]
    create_pcs_figures(source, target, pcs)
