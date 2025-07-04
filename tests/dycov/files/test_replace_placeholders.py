#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import tempfile
from pathlib import Path

from lxml import etree

from dycov.files.replace_placeholders import (
    dump_file,
    fault_time,
    get_all_variables,
    modify_jobs_file,
)


class TestReplacePlaceholders:

    def test_dump_file_renders_and_writes_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            template_content = "Hello, {{ name }}!"
            template_file = "greeting.j2"
            with open(path / template_file, "w", encoding="utf-8") as f:
                f.write(template_content)
            output_file = path / template_file
            dump_file(path, template_file, {"name": "World"})
            with open(output_file, "r", encoding="utf-8") as f:
                result = f.read()
            assert result == "Hello, World!"

    def test_modify_jobs_file_updates_solver_attributes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            xml_content = """<root xmlns="http://example.com">
                <solver parId="old" lib="oldlib"/>
            </root>"""
            filename = "jobs.xml"
            file_path = path / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            modify_jobs_file(path, filename, "new_id", "new_lib")
            tree = etree.parse(file_path)
            ns = {"ns": "http://example.com"}
            solver = tree.find(".//ns:solver", namespaces=ns)
            assert solver is not None
            assert solver.get("parId") == "new_id"
            assert solver.get("lib") == "new_lib"

    def test_get_all_variables_extracts_template_variables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            template_content = "Value: {{ foo }}, Another: {{ bar }}"
            template_file = "vars.j2"
            with open(path / template_file, "w", encoding="utf-8") as f:
                f.write(template_content)
            result = get_all_variables(path, template_file)
            assert set(result.keys()) == {"foo", "bar"}
            assert all(v == 0 for v in result.values())

    def test_get_all_variables_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            template_file = "does_not_exist.j2"
            result = get_all_variables(path, template_file)
            assert result == {}

    def test_fault_time_no_fault_tbegin_logs_and_returns(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # XML with no par element with name="fault_tBegin"
            xml_content = """<root xmlns="http://example.com">
                <model id="NodeFault">
                    <par name="not_fault_tBegin" value="1.0"/>
                </model>
            </root>"""
            file_path = path / "par.xml"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            # Use caplog to capture logs
            with caplog.at_level("INFO"):
                fault_time(file_path, 5.0)
            # Check that the log message was emitted
            assert any("No event to disconnect" in record.message for record in caplog.records)
            # File should remain unchanged
            with open(file_path, "r", encoding="utf-8") as f:
                after = f.read()
            assert "not_fault_tBegin" in after
