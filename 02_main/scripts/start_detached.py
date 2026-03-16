from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


DETACHED_PROCESS = 0x00000008


def parse_args() -> argparse.Namespace:
    """분리 실행에 필요한 경로와 명령 인자를 읽는다."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> None:
    """지정한 명령을 백그라운드에서 실행하고 로그 파일로 출력한다."""
    args = parse_args()
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("ab") as stream:
        subprocess.Popen(
            " ".join(args.command) if args.shell else args.command,
            cwd=args.cwd,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_PROCESS,
            shell=args.shell,
        )


if __name__ == "__main__":
    main()
