"""Entry point: python -m recursive_neon.shell"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys

from recursive_neon.dependencies import ServiceFactory
from recursive_neon.shell.shell import Shell


def main() -> None:
    """Launch the interactive shell."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        container = ServiceFactory.create_production_container()
    except Exception as e:
        print(f"Failed to initialize services: {e}", file=sys.stderr)
        sys.exit(1)

    shell = Shell(container)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(shell.run())

    sys.exit(shell.session.last_exit_code)


if __name__ == "__main__":
    main()
