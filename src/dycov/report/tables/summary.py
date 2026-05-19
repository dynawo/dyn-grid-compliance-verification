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
    for i in summary_list:
        summary_map.append(
            [
                f"{i.producer_name}".replace("_", r"\_").strip(),
                f"{i.pcs}".replace("_", r"\_").strip(),
                f"{i.benchmark}".strip(),
                f"{i.operating_condition}".strip(),
                f"{_translate_compliance(i.compliance)}".strip(),
            ]
        )

    return summary_map
