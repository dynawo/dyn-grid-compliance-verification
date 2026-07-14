from dycov.model.compliance import Compliance


def _translate_compliance(value: Compliance) -> str:
    if value != Compliance.Compliant:
        return f"\\textcolor{{red}}{{{value.to_str()}}}"
    else:
        return value.to_str()


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
    for i in summary_list:
        compliance_str = _translate_compliance(i.compliance)
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

        summary_map.append(
            [
                f"{i.producer_name}".replace("_", r"\_").strip(),
                f"{i.pcs}".replace("_", r"\_").strip(),
                f"{i.benchmark}".strip(),
                f"{i.operating_condition}".strip(),
                f"{compliance_str}".strip(),
            ]
        )

    return summary_map
