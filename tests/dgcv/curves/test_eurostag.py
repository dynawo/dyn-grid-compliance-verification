import shutil
from pathlib import Path

from dgcv.curves.importer import CurvesImporter


def _get_resources_path():
    return (Path(__file__).resolve().parent) / "resources"


def test_eurostag():

    path = _get_resources_path() / "tmp"
    shutil.copytree(_get_resources_path(), path, dirs_exist_ok=True)

    try:
        importer = CurvesImporter(path, "fiche8")
        df_eurostag_curve, curves_dict, tt, fs = importer.get_curves_dataframe(0)

        assert not df_eurostag_curve.empty
        assert "time" in df_eurostag_curve
        assert "bus_PDR_V" in df_eurostag_curve
        assert "generator_Omega" in df_eurostag_curve
        assert tt == 0.0
    finally:
        shutil.rmtree(path)
