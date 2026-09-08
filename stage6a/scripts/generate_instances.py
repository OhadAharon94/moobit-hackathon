"""Generate the deterministic Stage 6A core instance grid."""

import json
from pathlib import Path

from qera_scaling.acceptance import require_accepted
from qera_scaling.instances import core_instances


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "artifacts" / "scaling" / "instances"
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for instance in core_instances():
        reports.append(require_accepted(instance))
        path = output / f"{instance.instance_id}.json"
        path.write_text(
            json.dumps(instance.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(path.resolve())
    report_path = output / "acceptance_report.json"
    report_path.write_text(
        json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(report_path.resolve())


if __name__ == "__main__":
    main()
