"""
Recursive://Neon CLI Shell

A Unix-like command-line shell over the virtual filesystem.
Run with: python -m recursive_neon.shell
"""

from recursive_neon.shell.shell import InputSource, Shell

__all__ = ["InputSource", "Shell"]
