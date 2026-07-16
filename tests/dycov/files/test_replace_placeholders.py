#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import logging
import tempfile
from pathlib import Path


def _patch_dycov_logging(monkeypatch):
    def _get_logger(name):
        # Return a standard logging logger so caplog can intercept it
        return logging.getLogger(name)

    monkeypatch.setattr(
        "dycov.logging.logging.dycov_logging.get_logger",
        _get_logger,
        raising=True,
    )


class TestReplacePlaceholders:
    def test_dump_file_renders_and_writes_template(self):
        from dycov.files.replace_placeholders import dump_file

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            template_content = "Hello, {{ name }}!"
            template_file = "greeting.j2"
            (path / template_file).write_text(template_content, encoding="utf-8")

            output_file = path / template_file
            dump_file(path, template_file, {"name": "World"})
            assert output_file.read_text(encoding="utf-8") == "Hello, World!"

    def test_modify_jobs_file_updates_solver_attributes(self):
        from lxml import etree

        from dycov.files.replace_placeholders import modify_jobs_file

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            xml_content = """
            <root xmlns="http://example.com">
              <solver parId="old" lib="oldlib"/>
            </root>
            """
            filename = "jobs.xml"
            file_path = path / filename
            file_path.write_text(xml_content, encoding="utf-8")

            modify_jobs_file(path, filename, "new_id", "new_lib")

            tree = etree.parse(str(file_path))
            ns = {"ns": "http://example.com"}
            solver = tree.find(".//ns:solver", namespaces=ns)
            assert solver is not None
            assert solver.get("parId") == "new_id"
            assert solver.get("lib") == "new_lib"

    def test_get_all_variables_extracts_template_variables(self):
        from dycov.files.replace_placeholders import get_all_variables

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            template_content = "Value: {{ foo }}, Another: {{ bar }}"
            template_file = "vars.j2"
            (path / template_file).write_text(template_content, encoding="utf-8")

            result = get_all_variables(path, template_file)
            assert set(result.keys()) == {"foo", "bar"}
            assert all(v == 0 for v in result.values())

    def test_get_all_variables_missing_file_returns_empty_dict(self):
        from dycov.files.replace_placeholders import get_all_variables

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            template_file = "does_not_exist.j2"
            result = get_all_variables(path, template_file)
            assert result == {}

    def test_fault_time_no_fault_tbegin_logs_and_returns(self, caplog):
        from dycov.files.replace_placeholders import fault_time

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # XML without par name="fault_tBegin"
            xml_content = """
            <root xmlns="http://example.com">
              <model id="NodeFault">
                <par name="not_fault_tBegin" value="1.0"/>
              </model>
            </root>
            """
            file_path = path / "par.xml"
            file_path.write_text(xml_content, encoding="utf-8")

            # Capture at INFO for any logger
            caplog.set_level(logging.INFO)
            fault_time(file_path, 5.0)

            assert any("No event to disconnect" in r.message for r in caplog.records)

            # File should remain unchanged
            after = file_path.read_text(encoding="utf-8")
            assert "not_fault_tBegin" in after

    # =========================
    # PAR modifications
    # =========================

    def test_modify_par_file_updates_value(self):
        from dycov.files.replace_placeholders import modify_par_file

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            xml = """
            <root xmlns="http://test">
                <par name="param" value="1"/>
            </root>
            """
            f = path / "file.xml"
            f.write_text(xml, encoding="utf-8")

            modify_par_file(path, "file.xml", "param", 5.0)

            content = f.read_text()
            assert 'value="5.0"' in content

    # =========================
    # Add parameters
    # =========================

    def test_add_parameters_add(self):
        from dycov.files.replace_placeholders import add_parameters

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            xml = """
            <root xmlns="http://test">
                <set id="solver1"></set>
            </root>
            """
            f = path / "file.xml"
            f.write_text(xml, encoding="utf-8")

            add_parameters(
                path,
                "file.xml",
                "solver1",
                [{"type": "DOUBLE", "name": "p1", "value": "1"}],
            )

            content = f.read_text()
            assert "p1" in content

    def test_add_parameters_update(self):
        from dycov.files.replace_placeholders import add_parameters

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            xml = """
            <root xmlns="http://test">
                <set id="solver1">
                    <par name="p1" value="1"/>
                </set>
            </root>
            """
            f = path / "file.xml"
            f.write_text(xml, encoding="utf-8")

            add_parameters(
                path,
                "file.xml",
                "solver1",
                [{"type": "DOUBLE", "name": "p1", "value": "5"}],
            )

            content = f.read_text()
            assert 'value="5"' in content

    # =========================
    # Fault PAR
    # =========================

    def test_fault_par_file_updates_all(self):
        from dycov.files.replace_placeholders import fault_par_file

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            xml = """
            <root xmlns="http://test">
                <par name="fault_tEnd" value="1"/>
                <par name="fault_RPu" value="1"/>
                <par name="fault_XPu" value="1"/>
            </root>
            """
            f = path / "file.xml"
            f.write_text(xml, encoding="utf-8")

            fault_par_file(path, "file.xml", 2.0, 3.0, 4.0)

            content = f.read_text()
            assert 'value="2.0"' in content
            assert 'value="4.0"' in content
            assert 'value="3.0"' in content

    # =========================
    # Fault time main branch
    # =========================

    def test_fault_time_updates_values(self):
        from dycov.files.replace_placeholders import fault_time

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)

            xml = """
            <root xmlns="http://test">
                <set id="NodeFault">
                    <par name="fault_tBegin" value="1"/>
                    <par name="fault_tEnd" value="1"/>
                </set>
                <set id="DisconnectLine">
                    <par name="event_tEvent" value="1"/>
                </set>
            </root>
            """

            f = path / "file.xml"
            f.write_text(xml, encoding="utf-8")

            fault_time(f, 2.0)

            content = f.read_text()
            assert 'value="3.0"' in content
