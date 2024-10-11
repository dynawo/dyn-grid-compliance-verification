import shutil
from pathlib import Path

from dgcv.curves.importer import CurvesImporter


def test_csv():

    path = Path(__file__).resolve().parent / "tmp"
    shutil.copytree(Path(__file__).resolve().parent, path, dirs_exist_ok=True)

    try:
        importer = CurvesImporter(path, "curves_final")
        df_csv_curve, curves_dict, tt, fs = importer.get_curves_dataframe(0)

        assert not df_csv_curve.empty
        assert "time" in df_csv_curve
        assert "BusPDR_bus_terminal_V" in df_csv_curve
        assert "Synch_Gen_generator_UStatorPu_value" in df_csv_curve
        assert tt == 0.0
    finally:
        shutil.rmtree(path)
