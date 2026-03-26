"""Recursive://Neon Backend"""

import warnings

# Suppress pydantic.v1 warning on Python 3.14+ (langchain-core imports it internally).
# This must live here (package __init__) because `python -m recursive_neon.shell`
# loads `recursive_neon.shell.__init__` BEFORE `shell/__main__.py` runs, and the
# transitive import chain (shell → services → npc_manager → langchain_core)
# triggers the warning during that early import.
# TECH-DEBT: Remove once langchain-core drops the pydantic.v1 import.
# Track: docs/TECH_DEBT.md #TD-001
warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14",
    category=UserWarning,
)

__version__ = "0.1.0"
