from __future__ import annotations

import argparse

from learningpackage.server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Syllora local backend server")
    parser.add_argument("command", nargs="?", default="serve", choices=["serve"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.command == "serve":
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
