import shutil
from pathlib import Path

from dgcv.files.producer_dyd_file import create_producer_dyd_file
from dgcv.files.producer_par_file import create_producer_par_file


def generate_dyd_file(topology, template):
    path = Path(__file__).resolve().parent / "tmp"
    shutil.copytree(Path(__file__).resolve().parent, path, dirs_exist_ok=True)

    content = ""
    try:
        create_producer_dyd_file(path, topology, template)
        with open(path / "Producer.dyd") as f:
            content = f.read()
    finally:
        shutil.rmtree(path)
        return content


def generate_par_file():
    path = Path(__file__).resolve().parent / "tmp"
    shutil.copytree(Path(__file__).resolve().parent, path, dirs_exist_ok=True)

    content = ""
    try:
        create_producer_par_file("dynawo.sh", path, "performance_SM")
        with open(path / "Producer.par") as f:
            content = f.read()
    finally:
        shutil.rmtree(path)
        return content


def get_reference_content(reference):
    path = Path(__file__).resolve().parent / "ref"
    with open(path / reference) as f:
        content = f.read()

    return content


def test_single_sm_ok():
    assert get_reference_content("SingleSM.dyd") == generate_dyd_file("S", "performance_SM")


def test_single_aux_sm_ok():
    assert get_reference_content("SingleAuxSM.dyd") == generate_dyd_file("S+Aux", "performance_SM")


def test_single_i_sm_ok():
    assert get_reference_content("SingleISM.dyd") == generate_dyd_file("S+i", "performance_SM")


def test_single_aux_i_ppm_ok():
    assert get_reference_content("SingleAuxIPPM.dyd") == generate_dyd_file(
        "S+Aux+i", "performance_PPM"
    )


def test_multiple_ppm_ok():
    assert get_reference_content("MultiplePPM.dyd") == generate_dyd_file("M", "performance_PPM")


def test_multiple_aux_ppm_ok():
    assert get_reference_content("MultipleAuxPPM.dyd") == generate_dyd_file(
        "M+Aux", "performance_PPM"
    )


def test_multiple_i_ppm_ok():
    assert get_reference_content("MultipleIPPM.dyd") == generate_dyd_file("M+i", "performance_PPM")


def test_multiple_aux_i_ppm_ok():
    assert get_reference_content("MultipleAuxIPPM.dyd") == generate_dyd_file(
        "M+Aux+i", "performance_PPM"
    )


def test_single_aux_i_sm_ko():
    assert get_reference_content("SingleAuxIPPM.dyd") != generate_dyd_file("S", "performance_SM")


def test_multiple_sm_ko():
    assert get_reference_content("MultiplePPM.dyd") != generate_dyd_file("M", "performance_SM")


def test_single_ppm_ko():
    assert get_reference_content("SingleSM.dyd") != generate_dyd_file("S", "performance_PPM")


def dynawo_test_par_file_ok():
    assert get_reference_content("Reference.par") == generate_par_file()


def dynawo_test_par_file_ko():
    assert get_reference_content("Invalid.par") != generate_par_file()
