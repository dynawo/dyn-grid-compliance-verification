#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

from dycov.curves.importer.importer import CurvesImporter


@pytest.fixture
def curves_dir(tmp_path):
    (tmp_path / "ref.csv").write_text(
        "time;colA;colB\n0.0;1.0;2.0\n1.0;1.1;2.1\n",
    )
    (tmp_path / "ref.dict").write_text(
        "[Curves-Metadata]\n"
        "is_field_measurements = False\n"
        "sim_t_event_start = 0.0\n"
        "fault_duration = 0.0\n"
        "frequency_sampling = 15.0\n"
        "\n"
        "[Curves-Dictionary]\n"
        "time = time\n"
        "InternalNode1_BUS_Voltage = colA\n"
        "BusPDR_BUS_ActivePower = colB\n",
    )
    return tmp_path


def test_zone1_accepts_internalnode1_dictionary_keys(curves_dir):
    importer = CurvesImporter(curves_dir, "ref", remove_working_dict=False)

    df = importer.get_curves_dataframe(zone=1, remove_file=False)

    assert "BusPDR_BUS_Voltage" in df
    assert "BusPDR_BUS_ActivePower" in df
    assert "InternalNode1_BUS_Voltage" not in df


def test_zone1_bus_entries_resolved_from_curves_files_ini(tmp_path):
    (tmp_path / "CurvesFiles.ini").write_text(
        "[Curves-Files]\n"
        "\n"
        "[Curves-Dictionary]\n"
        "time = time\n"
        "\n"
        "[Curves-Dictionary-Zone1]\n"
        "InternalNode1_BUS_Voltage = InternalNode1_BUS_Voltage\n"
        "\n"
        "[Curves-Dictionary-Zone3]\n"
        "BusPDR_BUS_Voltage = BusPDR_BUS_Voltage\n",
    )
    (tmp_path / "ref.csv").write_text(
        "time;InternalNode1_BUS_Voltage\n0.0;1.0\n1.0;0.9\n",
    )
    (tmp_path / "ref.dict").write_text(
        "[Curves-Metadata]\n"
        "sim_t_event_start = 0.0\n"
        "fault_duration = 0.0\n"
        "\n"
        "[Curves-Dictionary]\n",
    )
    importer = CurvesImporter(tmp_path, "ref", remove_working_dict=False)

    df = importer.get_curves_dataframe(zone=1, remove_file=False)

    assert "BusPDR_BUS_Voltage" in df
    assert "InternalNode1_BUS_Voltage" not in df


def test_zone0_keeps_dictionary_keys_untranslated(curves_dir):
    importer = CurvesImporter(curves_dir, "ref", remove_working_dict=False)

    df = importer.get_curves_dataframe(zone=0, remove_file=False)

    assert "InternalNode1_BUS_Voltage" in df
    assert "BusPDR_BUS_ActivePower" in df
    assert "BusPDR_BUS_Voltage" not in df
