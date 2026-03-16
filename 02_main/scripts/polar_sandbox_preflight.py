from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.polar_preflight import build_next_steps, collect_preflight_checks, has_blocking_failures


def parse_args() -> argparse.Namespace:
    """사전 점검에 필요한 선택 인자를 읽는다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base-url", default=None)
    return parser.parse_args()


def main() -> None:
    """Polar sandbox 실행 전 필수 준비 항목을 출력한다."""
    args = parse_args()
    checks = collect_preflight_checks(
        root_path=Path(__file__).resolve().parents[1],
        api_base_url=args.api_base_url,
    )

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
