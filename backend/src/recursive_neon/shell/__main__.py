"""Entry point: python -m recursive_neon.shell"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys

from recursive_neon.config import settings
from recursive_neon.dependencies import ServiceFactory
from recursive_neon.shell.shell import Shell


async def _async_main() -> int:
    """Launch the interactive shell."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        container = await ServiceFactory.create_production_container()
    except Exception as e:
        print(f"Failed to initialize services: {e}", file=sys.stderr)
        return 1

    data_dir = str(settings.data_dir)
    shell = Shell(container, data_dir=data_dir)
    with contextlib.suppress(KeyboardInterrupt):
        await shell.run()

    return shell.session.last_exit_code


def main() -> None:
    """Synchronous entry point."""
    sys.exit(asyncio.run(_async_main()))


if __name__ == "__main__":
    main()
