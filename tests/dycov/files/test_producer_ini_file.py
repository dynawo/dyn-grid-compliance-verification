#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import shutil
import tempfile
from pathlib import Path

import pytest

from dycov.files.producer_ini_file import check_ini_parameters, create_producer_ini_file


class TestProducerIniFile:

    def test_create_producer_ini_file_performance_template_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            topology = "S"
            template = "performance_SM"
            create_producer_ini_file(target, topology, template)
            ini_file = target / "Producer.ini"
            assert ini_file.exists()
            content = ini_file.read_text()
            assert "topology = S" in content
            assert "p_max_injection =" in content
            assert "p_max_consumption =" in content
            assert "u_nom =" in content
            assert "s_nom =" in content
            assert "q_max =" in content
            assert "q_min =" in content

    def test_check_ini_parameters_all_values_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            ini_file = target / "Producer.ini"
            ini_content = (
                "# p_{max_unite} as defined by the DTR in MW\n"
                "p_max = 100\n"
                "# u_nom is the nominal voltage in the PDR Bus (in kV)\n"
                "u_nom = 225\n"
                "# s_nom is the nominal apparent power of all generating units (in MVA)\n"
                "s_nom = 200\n"
                "# q_max is the maximum reactive power of all generating units (in MVar)\n"
                "q_max = 50\n"
                "# q_min is the minimum reactive power of all generating units (in MVar)\n"
                "q_min = -50\n"
                "# topology\n"
                "topology = S\n"
            )
            ini_file.write_text(ini_content)
            result = check_ini_parameters(target, "performance_SM")
            assert result is True

    def test_check_ini_parameters_with_empty_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            ini_file = target / "Producer.ini"
            ini_content = (
                "# p_{max_unite} as defined by the DTR in MW\n"
                "p_max =\n"
                "# u_nom is the nominal voltage in the PDR Bus (in kV)\n"
                "u_nom = 225\n"
                "# s_nom is the nominal apparent power of all generating units (in MVA)\n"
                "s_nom = 200\n"
                "# q_max is the maximum reactive power of all generating units (in MVar)\n"
                "q_max = 50\n"
                "# q_min is the minimum reactive power of all generating units (in MVar)\n"
                "q_min = -50\n"
                "# topology\n"
                "topology = S\n"
            )
            ini_file.write_text(ini_content)
            result = check_ini_parameters(target, "performance_SM")
            assert result is False

    def test_create_producer_ini_file_nonexistent_target(self):
        tmpdir = tempfile.mkdtemp()
        shutil.rmtree(tmpdir)
        target = Path(tmpdir)
        topology = "S"
        template = "performance_SM"
        with pytest.raises(FileNotFoundError):
            create_producer_ini_file(target, topology, template)
