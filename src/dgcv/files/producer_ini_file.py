import configparser
from pathlib import Path

from dgcv.logging.logging import dgcv_logging


def _create_producer_ini_file(
    target: Path,
    topology: str,
) -> None:
    producer_ini_txt = (
        f"# p_{{max_unite}} as defined by the DTR in MW\n"
        f"p_max =\n"
        f"# u_nom is the nominal voltage in the PDR Bus (in kV)\n"
        f"# Allowed values: 400, 225, 150, 90, 63 (land) and 132, 66 (offshore)\n"
        f"u_nom =\n"
        f"# s_nom is the nominal apparent power of all generating units (in MVA)\n"
        f"s_nom =\n"
        f"# q_max is the maximum reactive power of all generating units (in MVar)\n"
        f"q_max =\n"
        f"# q_min is the minimum reactive power of all generating units (in MVar)\n"
        f"q_min =\n"
        f"# topology\n"
        f"topology = {topology}\n"
    )
    with open(target / "Producer.ini", "w") as f:
        f.write(producer_ini_txt)


def _check_ini_parameters(target: Path) -> bool:

    default_section = "DEFAULT"
    with open(target / "Producer.ini", "r") as f:
        producer_ini_txt = "[" + default_section + "]\n" + f.read()

    producer_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
    producer_config.read_string(producer_ini_txt)

    success = True
    empty_values = []
    for key, value in producer_config.items(default_section):
        if value == "":
            empty_values.append(key)
            success = False

    if not success:
        dgcv_logging.get_logger("Create INI input").error(
            f"The INI file contains parameters without value.\n" f"Please fix {empty_values}."
        )
    return success


def create_producer_ini_file(
    target: Path,
    topology: str,
    template: str,
) -> None:
    """Create a INI file in target path

    Parameters
    ----------
    target: Path
        Target path
    topology: str
        Topology to the DYD file
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model
    """
    if template.startswith("model"):
        _create_producer_ini_file(target / "Zone1", "S")
        _create_producer_ini_file(target / "Zone3", topology)
    else:
        _create_producer_ini_file(target, topology)


def check_ini_parameters(target: Path, template: str) -> bool:
    """Checks if all parameters in the INI file have a value defined.

    Parameters
    ----------
    target: Path
        Target path
    template: str
        Input template name:
        * 'performance_SM' if it is electrical performance for Synchronous Machine Model
        * 'performance_PPM' if it is electrical performance for Power Park Module Model
        * 'performance_BESS' if it is electrical performance for Storage Model
        * 'model_PPM' if it is model validation for Power Park Module Model
        * 'model_BESS' if it is model validation for Storage Model

    Returns
    -------
    bool
        False if there are empty values in the INI file
    """
    if template.startswith("model"):
        check_zone1 = _check_ini_parameters(target / "Zone1")
        check_zone3 = _check_ini_parameters(target / "Zone3")
        return check_zone1 and check_zone3
    else:
        return _check_ini_parameters(target)
