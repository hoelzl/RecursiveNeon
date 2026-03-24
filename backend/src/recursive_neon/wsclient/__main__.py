"""Entry point: python -m recursive_neon.wsclient"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys

from recursive_neon.wsclient.client import run_client


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect to Recursive://Neon terminal via WebSocket",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)",
    )
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}/ws/terminal"

    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run_client(url))

    sys.exit(0)


if __name__ == "__main__":
    main()
