from dycov.report import printable


def test_format_time_error():
    results = {"test1": 2.468392}
    value = printable.format_time_error(results, "test1")
    assert value == f"{2.468392}"

    value = printable.format_time_error(results, "test1", apply_formatter=True)
    assert value == f"{2.468392:.3g}"


def test_format_compound_check():
    text_value = printable.format_compound_check(True)
    assert text_value == f"{{ {str(True)} }}"

    text_value = printable.format_compound_check(False)
    assert text_value == f"\\textcolor{{red}}{{ {str(False)} }}"
