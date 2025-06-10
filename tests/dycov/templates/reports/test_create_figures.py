from dycov.core import global_variables
from dycov.templates.reports import create_figures


def test_pcs_name():
    pcs_names = ["PCS_RTE-I2", "PCS_RTE-I5", "PCS_RTE-I16z1"]
    simulation_types = [
        global_variables.ELECTRIC_PERFORMANCE_SM,
        global_variables.ELECTRIC_PERFORMANCE_PPM,
        global_variables.MODEL_VALIDATION_PPM,
    ]
    expected_ouputs = ["RTE-I2SM", "RTE-I5", "RTE-I16z1"]
    for pcs_name, simulation_type, expected_ouput in zip(
        pcs_names, simulation_types, expected_ouputs
    ):
        pcs = create_figures._get_pcs_name(pcs_name, simulation_type)
        assert pcs == expected_ouput


def test_figures():
    figures = create_figures._get_pcs_figures("RTE-I2SM")
    assert figures == [
        "fig_P_PCS_RTE-I2.USetPointStep.AReactance.pdf",
        "fig_P_PCS_RTE-I2.USetPointStep.BReactance.pdf",
        "fig_Q_PCS_RTE-I2.USetPointStep.AReactance.pdf",
        "fig_Q_PCS_RTE-I2.USetPointStep.BReactance.pdf",
        "fig_Ustator_PCS_RTE-I2.USetPointStep.AReactance.pdf",
        "fig_Ustator_PCS_RTE-I2.USetPointStep.BReactance.pdf",
        "fig_V_PCS_RTE-I2.USetPointStep.AReactance.pdf",
        "fig_V_PCS_RTE-I2.USetPointStep.BReactance.pdf",
        "fig_W_PCS_RTE-I2.USetPointStep.AReactance.pdf",
        "fig_W_PCS_RTE-I2.USetPointStep.BReactance.pdf",
    ]
