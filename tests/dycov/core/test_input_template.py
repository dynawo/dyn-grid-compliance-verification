#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

# =========================
# _get_input
# =========================

def test_get_input(monkeypatch):
    from dycov.core.input_template import InputTemplateGenerator

    monkeypatch.setattr("builtins.input", lambda _: "ok")

    gen = InputTemplateGenerator()

    assert gen._get_input("msg") == "ok"


# =========================
# _create_and_validate_file
# =========================

def test_create_and_validate_file(monkeypatch, tmp_path):
    from dycov.core.input_template import InputTemplateGenerator

    gen = InputTemplateGenerator()

    calls = {"check": 0}

    def creation_func(*args):
        pass

    def check_func(*args):
        calls["check"] += 1
        return calls["check"] >= 2  # entra en el while 1 vez

    monkeypatch.setattr(gen, "_get_input", lambda x: "")

    gen._create_and_validate_file(
        file_type="INI",
        target=tmp_path,
        topology="top",
        template="tpl",
        creation_func=creation_func,
        check_func=check_func,
        prompt_message="test",
    )

    assert calls["check"] == 2


def test_create_and_validate_file_par():
    import pytest

    from dycov.core.input_template import InputTemplateGenerator

    gen = InputTemplateGenerator()

    with pytest.raises(NotImplementedError):
        gen._create_and_validate_file(
            file_type="PAR",
            target=None,
            topology=None,
            template=None,
            creation_func=None,
            check_func=None,
            prompt_message="",
        )


# =========================
# _create_dyd_template
# =========================

def test_create_dyd_template(monkeypatch, tmp_path):
    from dycov.core.input_template import InputTemplateGenerator

    gen = InputTemplateGenerator()

    calls = {"check": 0}

    monkeypatch.setattr(
        "dycov.core.input_template.create_producer_dyd_file",
        lambda *a: None,
    )

    def fake_check(*args):
        calls["check"] += 1
        return calls["check"] >= 2

    monkeypatch.setattr(
        "dycov.core.input_template.check_dynamic_models",
        fake_check,
    )

    monkeypatch.setattr(gen, "_get_input", lambda x: "")

    gen._create_dyd_template(tmp_path, "top", "tpl")

    assert calls["check"] == 2


# =========================
# create_input_template
# =========================

def test_create_input_template_existing(tmp_path):
    from dycov.core.input_template import InputTemplateGenerator

    gen = InputTemplateGenerator()

    # path ya existe -> early exit
    res = gen.create_input_template(None, tmp_path, "top", "tpl")

    assert res == 1


def test_create_input_template_flow(monkeypatch, tmp_path):
    from dycov.core.input_template import InputTemplateGenerator

    gen = InputTemplateGenerator()

    target = tmp_path / "out"

    # evitar IO real
    monkeypatch.setattr(
        "dycov.core.input_template.manage_files.create_dir",
        lambda x: None,
    )

    monkeypatch.setattr(gen, "_copy_input_templates", lambda *a: None)
    monkeypatch.setattr(gen, "_create_dyd_template", lambda *a: None)
    monkeypatch.setattr(gen, "_create_par_template", lambda *a: None)
    monkeypatch.setattr(gen, "_create_ini_template", lambda *a: None)
    monkeypatch.setattr(gen, "_create_curves_template", lambda *a: None)

    res = gen.create_input_template(None, target, "top", "tpl")

    assert res == 0
