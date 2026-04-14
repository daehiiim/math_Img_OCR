from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schema_preflight import build_next_steps, collect_schema_preflight_checks, has_blocking_failures


def main() -> None:
    """운영 백엔드 런타임 스키마 호환성을 점검한다."""
    checks = collect_schema_preflight_checks(root_path=Path(__file__).resolve().parents[1])
    for check in checks:
        print(f"[{check.status.upper()}] {check.key}: {check.detail}")
    print("")
    print("다음 사용자 작업:")
    for index, step in enumerate(build_next_steps(checks), start=1):
        print(f"{index}. {step}")
    if has_blocking_failures(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
