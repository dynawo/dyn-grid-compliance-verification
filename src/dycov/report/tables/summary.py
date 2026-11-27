from dycov.model.compliance import Compliance


def translate_compliance(value: Compliance) -> str:
    """The compliance as the report prints it, in red when it is not compliant."""
    if value != Compliance.Compliant:
        return f"\\textcolor{{red}}{{{value.to_str()}}}"
    else:
        return value.to_str()


def _altered_note(altered_criteria: tuple, already_defined: bool) -> str:
    """Marks a PCS the user configuration measured with criteria of its own.

    The verdict is the one those values produce, and it is not a conformity check, so the
    note names every option that was changed.
    """
    if already_defined:
        return r"\footnotemark[\value{footnote}]"

    options = ", ".join(option.replace("_", r"\_") for option in altered_criteria)
    return (
        rf"\footnote{{Not a conformity check: the configuration of the user "
        rf"overrides {options}.}}"
    )


def create_map(summary_list: list) -> list:
    """Creates a map for the summary table.

    Parameters
    ----------
    summary_list : list
        A list of Summary objects.

    Returns
    -------
    list
        A list of lists, where each inner list represents a row in the summary table.
    """
    summary_map = []
    footnote_defined = False
    altered_defined = False
    for i in summary_list:
        compliance_str = translate_compliance(i.compliance)
        if i.compliance is Compliance.NotApplicableTest:
            if not footnote_defined:
                # First occurrence defines the footnote text; later occurrences reuse
                # the same note via \footnotemark[\value{footnote}], which resolves in
                # a single compilation pass (unlike \ref, it does not need the .aux
                # file from a previous LaTeX run).
                compliance_str += "\\footnote{Not executed: incompatible control mode.}"
                footnote_defined = True
            else:
                compliance_str += "\\footnotemark[\\value{footnote}]"

        pcs_str = f"{i.pcs}".replace("_", r"\_").strip()
        if i.altered_criteria:
            pcs_str += _altered_note(i.altered_criteria, altered_defined)
            altered_defined = True

        summary_map.append(
            [
                f"{i.producer_name}".replace("_", r"\_").strip(),
                pcs_str,
                f"{i.benchmark}".replace("_", r"\_").strip(),
                f"{i.operating_condition}".replace("_", r"\_").strip(),
                f"{compliance_str}".strip(),
            ]
        )

    return summary_map
