from pathlib import Path

from dgcv.configuration.cfg import config
from dgcv.files import manage_files
from dgcv.files.producer_curves import check_curves, create_producer_curves
from dgcv.files.producer_dyd_file import check_dynamic_models, create_producer_dyd_file
from dgcv.files.producer_ini_file import check_ini_parameters, create_producer_ini_file
from dgcv.files.producer_par_file import check_parameters, create_producer_par_file
from dgcv.logging.logging import dgcv_logging


def _copy_input_templates(target: Path, template: str) -> None:
    input_templates_path = config.get_value("Global", "input_templates_path")
    if template == "performance_SM":
        manage_files.copy_path(Path(input_templates_path) / "performance/SM", target)
    elif template == "performance_PPM":
        manage_files.copy_path(Path(input_templates_path) / "performance/PPM", target)
    elif template == "model":
        manage_files.copy_path(Path(input_templates_path) / "model/PPM", target)


def _create_dyd_template(target: Path, topology: str, template: str) -> None:
    dgcv_logging.get_logger("Create input files").info(f"Creating the input DYD file in {target}.")
    create_producer_dyd_file(target, topology, template)
    input(
        "Edit the Producer.dyd file is necessary to complete each equipment in the "
        "model with a dynamic model. Press Enter when finishing editing."
    )
    while not check_dynamic_models(target, template):
        input(
            "Edit the Producer.dyd file is necessary to complete each equipment in the "
            "model with a dynamic model. Press Enter when finishing editing."
        )


def _create_par_template(launcher_dwo: Path, target: Path, topology: str, template: str) -> None:
    dgcv_logging.get_logger("Create input files").info(f"Creating the input PAR file in {target}.")
    create_producer_par_file(launcher_dwo, target, template)
    input(
        "Edit the Producer.par file is necessary to complete each parameter with a "
        "value. Press Enter when finishing editing."
    )
    while not check_parameters(target, template):
        input(
            "Edit the Producer.par file is necessary to complete each parameter with a "
            "value. Press Enter when finishing editing."
        )


def _create_ini_template(target: Path, topology: str, template: str) -> None:
    dgcv_logging.get_logger("Create input files").info(f"Creating the input INI file in {target}.")
    create_producer_ini_file(target, topology, template)
    input(
        "Edit the Producer.ini file is necessary to complete each parameter with a "
        "value. Press Enter when finishing editing."
    )
    while not check_ini_parameters(target, template):
        input(
            "Edit the Producer.ini file is necessary to complete each parameter with a "
            "value. Press Enter when finishing editing."
        )


def _create_curves_template(target: Path, topology: str, template: str) -> None:
    ref_target = target / "ReferenceCurves"
    dgcv_logging.get_logger("Create input files").info(
        f"Creating the reference curves files in {ref_target}."
    )
    create_producer_curves(target, ref_target, template)
    input(
        "Edit the CurvesFiles.ini file is necessary to complete each parameter with a "
        "curves file. Press Enter when finishing editing."
    )
    while not check_curves(ref_target):
        input(
            "Edit the CurvesFiles.ini file is necessary to complete each parameter with a "
            "curves file. Press Enter when finishing editing."
        )


def create_input_template(launcher_dwo: Path, target: Path, topology: str, template: str) -> None:
    """Create an input template in target path with the selected topology.

    Parameters
    ----------
    launcher_dwo: Path
        Dynawo launcher
    target: Path
        Target path
    topology: str
        Topology to the DYD file
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'model' if it is model validation
    """

    if target.exists():
        dgcv_logging.get_logger("Create Input").error(
            "The output path already exists, please indicate a new path"
        )
        return

    manage_files.create_dir(target)
    _copy_input_templates(target, template)

    _create_dyd_template(target, topology, template)

    _create_par_template(launcher_dwo, target, topology, template)

    _create_ini_template(target, topology, template)

    _create_curves_template(target, topology, template)
    print("Done")
