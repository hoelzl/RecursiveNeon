"""Entry point: python -m recursive_neon.shell"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
import warnings

# Suppress pydantic.v1 warning on Python 3.14+ (langchain-core imports it internally).
# TECH-DEBT: Remove once langchain-core drops the pydantic.v1 import.
# Track: docs/TECH_DEBT.md #TD-001
warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14",
    category=UserWarning,
)

from recursive_neon.config import settings
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

    data_dir = str(settings.data_dir)
    shell = Shell(container, data_dir=data_dir)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(shell.run())

    sys.exit(shell.session.last_exit_code)


if __name__ == "__main__":
    main()
