from __future__ import annotations

import argparse
import os

from learningpackage.server import run_server


def _read_port(default: int = 8000) -> int:
    raw = os.getenv("PORT", "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def main() -> None:
    parser = argparse.ArgumentParser(description="Syllora local backend server")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve"])
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=_read_port())
    args = parser.parse_args()

    if args.command == "serve":
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
