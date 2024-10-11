import shutil
from pathlib import Path

from dgcv.curves.importer import CurvesImporter


def test_comtrade():
    path = Path(__file__).resolve().parent / "tmp"
    shutil.copytree(Path(__file__).resolve().parent, path, dirs_exist_ok=True)

    try:
        importer = CurvesImporter(path, "Wind_farm_comtrade_example")
        df_comtrade_curve, curves_dict, tt, fs = importer.get_curves_dataframe(0)

        assert not df_comtrade_curve.empty
        assert "time" in df_comtrade_curve
        assert "Vac_a" in df_comtrade_curve
        assert "Ineg_q" in df_comtrade_curve
        assert tt == 2.584
    finally:
        shutil.rmtree(path)
