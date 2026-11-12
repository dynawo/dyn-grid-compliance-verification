from dycov.report import printable


def test_format_time_error():
    results = {"test1": 2.468392}
    value, footnote_defined = printable.format_time_error(results, "test1")
    assert value == f"{2.468392}"
    assert footnote_defined is False

    value, footnote_defined = printable.format_time_error(results, "test1", apply_formatter=True)
    assert value == f"{2.468392:.3g}"
    assert footnote_defined is False


def test_format_time_error_not_calculated_defines_footnote_once():
    results = {"test1": "-"}
    value, footnote_defined = printable.format_time_error(results, "test1")
    assert value.startswith(
        "\\footnote{Not Calculated because the reference value "
        "is exactly zero or very close to zero.}"
    )
    assert footnote_defined is True

    value, footnote_defined = printable.format_time_error(
        results, "test1", footnote_defined=footnote_defined
    )
    assert value.startswith(r"\csname @makefnmark\endcsname")
    assert footnote_defined is True


def test_format_compound_check():
    text_value = printable.format_compound_check(True)
    assert text_value == f"{{ {str(True)} }}"

    text_value = printable.format_compound_check(False)
    assert text_value == f"\\textcolor{{red}}{{ {str(False)} }}"


def test_table_note_gives_the_text_once_and_then_its_mark():
    assert printable.table_note("Some note.", False) == r"\footnote{Some note.}"
    assert printable.table_note("Some note.", True) == r"\csname @makefnmark\endcsname"
