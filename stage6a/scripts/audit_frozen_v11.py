"""Create the Stage 6A frozen-state checkpoint and adaptive audit."""

from pathlib import Path

from qera_scaling.audit import write_audit_artifacts


def main() -> None:
    stage6a_root = Path(__file__).resolve().parents[1]
    write_audit_artifacts(stage6a_root)
    print((stage6a_root / "artifacts" / "scaling" / "tables").resolve())


if __name__ == "__main__":
    main()
