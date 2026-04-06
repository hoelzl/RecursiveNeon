"""Tests for editor/faces.py — face→ANSI mapping and resolution."""

from __future__ import annotations

from recursive_neon.editor.faces import FACES, face_reset, resolve_face
from recursive_neon.editor.variables import VARIABLES, defvar


class TestFaces:
    """Face registry and resolution."""

    def test_built_in_faces_non_empty(self):
        assert len(FACES) > 0

    def test_keyword_face_exists(self):
        assert "keyword" in FACES

    def test_string_face_exists(self):
        assert "string" in FACES

    def test_comment_face_exists(self):
        assert "comment" in FACES

    def test_number_face_exists(self):
        assert "number" in FACES

    def test_heading_face_exists(self):
        assert "heading" in FACES

    def test_all_faces_are_ansi_sequences(self):
        for name, seq in FACES.items():
            assert seq.startswith("\033["), f"Face {name!r} is not an ANSI sequence"

    def test_resolve_face_returns_builtin(self):
        result = resolve_face("keyword")
        assert result == FACES["keyword"]

    def test_resolve_face_unknown_returns_empty(self):
        assert resolve_face("nonexistent-face-xyz") == ""

    def test_resolve_face_user_override(self):
        """User can override a face via defvar('face-keyword', ...)."""
        custom = "\033[35m"
        defvar("face-keyword", custom, "override keyword face", var_type=str)
        try:
            assert resolve_face("keyword") == custom
        finally:
            # Clean up
            VARIABLES.pop("face-keyword", None)

    def test_resolve_face_override_takes_precedence(self):
        custom = "\033[48;5;22m"
        defvar("face-string", custom, "override string face", var_type=str)
        try:
            assert resolve_face("string") == custom
            assert resolve_face("string") != FACES["string"]
        finally:
            VARIABLES.pop("face-string", None)

    def test_face_reset_returns_reset(self):
        assert face_reset() == "\033[0m"

    def test_builtin_face(self):
        assert "builtin" in FACES

    def test_decorator_face(self):
        assert "decorator" in FACES

    def test_sh_variable_face(self):
        assert "sh-variable" in FACES

    def test_sh_redirect_face(self):
        assert "sh-redirect" in FACES

    def test_code_face(self):
        assert "code" in FACES

    def test_link_face(self):
        assert "link" in FACES

    def test_bold_face(self):
        assert "bold" in FACES

    def test_italic_face(self):
        assert "italic" in FACES
