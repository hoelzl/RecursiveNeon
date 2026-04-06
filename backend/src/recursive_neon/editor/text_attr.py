"""
TextAttr — visual text attributes modelled after terminal SGR.

A frozen value type representing the visual styling of a character.
Used by the buffer's attribute layer to store colours and decorations
alongside text (e.g., ANSI-coloured shell output).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TextAttr:
    """Visual attributes for a character.

    Modelled after ANSI SGR parameters.  ``None`` fields mean
    "use terminal default".  Two attrs with the same field values
    are equal (frozen dataclass semantics).
    """

    fg: int | None = None  # 256-colour index, None = terminal default
    bg: int | None = None  # 256-colour index, None = terminal default
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    reverse: bool = False

    def to_sgr(self) -> str:
        """Convert to an ANSI SGR escape sequence.

        Returns an empty string if all fields are default (no styling).
        The result is cached after the first call.
        """
        cached: str | None = object.__getattribute__(self, "_sgr_cache")
        if cached is not None:
            return cached
        codes: list[str] = []
        if self.bold:
            codes.append("1")
        if self.dim:
            codes.append("2")
        if self.italic:
            codes.append("3")
        if self.underline:
            codes.append("4")
        if self.reverse:
            codes.append("7")
        if self.fg is not None:
            codes.append(f"38;5;{self.fg}")
        if self.bg is not None:
            codes.append(f"48;5;{self.bg}")
        result = f"\033[{';'.join(codes)}m" if codes else ""
        object.__setattr__(self, "_sgr_cache", result)
        return result

    # Cache slot — not part of equality or repr
    _sgr_cache: str | None = field(default=None, repr=False, compare=False)
