from dycov.model.compliance import Compliance


def _translate_compliance(value: Compliance) -> str:
    if value != Compliance.Compliant:
        return f"\\textcolor{{red}}{{{value.to_str()}}}"
    else:
        return value.to_str()


def create_map(summary_list: list) -> list:
    summary_map = []
    for i in summary_list:
        summary_map.append(
            [
                f"{i.producer_file}".replace("_", "\_").strip(),
                f"{i.pcs}".replace("_", "\_").strip(),
                f"{i.benchmark}".strip(),
                f"{i.operating_condition}".strip(),
                f"{_translate_compliance(i.compliance)}".strip(),
            ]
        )

    return summary_map
