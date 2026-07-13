from dycov.report import printable


def test_format_compound_check():
    text_value = printable.format_compound_check(True)
    assert text_value == f"{{ {str(True)} }}"

    text_value = printable.format_compound_check(False)
    assert text_value == f"\\textcolor{{red}}{{ {str(False)} }}"
