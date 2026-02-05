from pathlib import Path

from dycov.files.replace_placeholders import get_all_variables


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def test_par_file():
    path = _get_resources_path()
    variables = get_all_variables(path, "TSOModel.par")
    control_variables = dict.fromkeys(
        {
            "main_P0Pu",
            "main_Q0Pu",
            "main_U0Pu",
            "main_UPhase0",
            "secondary_P0Pu",
            "secondary_Q0Pu",
            "secondary_U0Pu",
            "secondary_UPhase0",
            "event_start",
        },
        0,
    )
    assert len(variables) == len(control_variables)
    assert (
        len(
            {
                k: variables[k]
                for k in variables
                if k in control_variables and variables[k] == control_variables[k]
            }
        )
        == 9
    )


def test_txt_file():
    path = _get_resources_path()
    variables = get_all_variables(path, "TableInfiniteBus.txt")
    control_variables = dict.fromkeys(
        {
            "simulation_start",
            "simulation_stop",
            "start_event",
            "end_event",
            "t_rec2",
            "t_rec3",
        },
        0,
    )
    assert len(variables) == len(control_variables)
    assert (
        len(
            {
                k: variables[k]
                for k in variables
                if k in control_variables and variables[k] == control_variables[k]
            }
        )
        == 6
    )
