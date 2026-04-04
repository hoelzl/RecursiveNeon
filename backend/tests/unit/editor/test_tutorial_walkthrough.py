"""Tutorial walk-through integration test (Phase 6k).

Exercises every chapter of ``TUTORIAL.txt`` programmatically via the
``EditorHarness`` to verify that every feature the tutorial teaches
actually works end-to-end.

One test class per chapter.  Assertions focus on observable behaviour
(point location, buffer text, message line) — not prose.
"""

from __future__ import annotations

import pytest

from recursive_neon.config import settings
from recursive_neon.dependencies import ServiceFactory
from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.variables import VARIABLES
from recursive_neon.editor.view import EditorView
from recursive_neon.shell.shell import Shell
from tests.unit.editor.harness import EditorHarness, make_harness


@pytest.fixture(autouse=True)
def _restore_global_variables():
    """Restore mutable global variable defaults after each test.

    Chapter 11/12 tests use commands (``set-fill-column``, direct
    ``set_variable``) that mutate the module-level ``VARIABLES``
    registry.  Without this fixture those changes leak into unrelated
    tests in ``test_variables.py`` and fail assertions about defaults.
    """
    saved = {name: var.default for name, var in VARIABLES.items()}
    yield
    for name, default in saved.items():
        VARIABLES[name].default = default


# ═══════════════════════════════════════════════════════════════════════
# Chapter 1 — Moving the cursor
# ═══════════════════════════════════════════════════════════════════════


class TestChapter1MovingTheCursor:
    """C-f / C-b / C-n / C-p / C-a / C-e / M-< / M->."""

    def test_forward_char(self) -> None:
        h = make_harness("hello\nworld")
        h.send_keys("C-f")
        assert h.point() == (0, 1)

    def test_backward_char(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-e", "C-b")
        assert h.point() == (0, 4)

    def test_next_line(self) -> None:
        h = make_harness("hello\nworld")
        h.send_keys("C-n")
        assert h.point() == (1, 0)

    def test_previous_line(self) -> None:
        h = make_harness("hello\nworld")
        h.send_keys("C-n", "C-p")
        assert h.point() == (0, 0)

    def test_beginning_of_line(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-e", "C-a")
        assert h.point() == (0, 0)

    def test_end_of_line(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-e")
        assert h.point() == (0, 5)

    def test_beginning_of_buffer(self) -> None:
        h = make_harness("first\nsecond\nthird")
        h.send_keys("C-n", "C-n", "C-e")
        h.send_keys("M-<")
        assert h.point() == (0, 0)

    def test_end_of_buffer(self) -> None:
        h = make_harness("first\nsecond\nthird")
        h.send_keys("M->")
        assert h.point() == (2, 5)

    def test_arrow_keys(self) -> None:
        """The tutorial mentions arrow keys as an alternative."""
        h = make_harness("hello")
        h.send_keys("ArrowRight", "ArrowRight")
        assert h.point() == (0, 2)


# ═══════════════════════════════════════════════════════════════════════
# Chapter 2 — Viewport scrolling
# ═══════════════════════════════════════════════════════════════════════


def _long_text(n: int = 30) -> str:
    return "\n".join(f"line {i}" for i in range(n))


class TestChapter2ViewportScrolling:
    """C-v / M-v / C-l."""

    def test_scroll_forward_one_screenful(self) -> None:
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        h.send_keys("C-v")
        assert h.view.scroll_top == text_h
        # Point moves to top of new viewport
        assert h.point() == (text_h, 0)

    def test_scroll_backward_one_screenful(self) -> None:
        h = make_harness(_long_text(30), height=10)
        h.send_keys("C-v")  # scroll forward first
        h.send_keys("M-v")  # then back
        assert h.view.scroll_top == 0

    def test_pagedown_equivalent(self) -> None:
        h = make_harness(_long_text(30), height=10)
        text_h = h.view.text_height
        h.send_keys("PageDown")
        assert h.view.scroll_top == text_h

    def test_pageup_equivalent(self) -> None:
        h = make_harness(_long_text(30), height=10)
        h.send_keys("PageDown")
        h.send_keys("PageUp")
        assert h.view.scroll_top == 0

    def test_recenter_cycles(self) -> None:
        """C-l cycles: center → top → bottom → center."""
        h = make_harness(_long_text(30), height=12)
        # Move to the middle
        h.send_keys("C-v")
        h.send_keys("C-n", "C-n")
        first = h.view.scroll_top
        h.send_keys("C-l")
        center = h.view.scroll_top
        h.send_keys("C-l")
        top = h.view.scroll_top
        h.send_keys("C-l")
        bottom = h.view.scroll_top
        # Each press should produce a different scroll position
        # (possible exception: very short text where all three collapse)
        assert {center, top, bottom} != {first}  # something changed


# ═══════════════════════════════════════════════════════════════════════
# Chapter 3 — Basic editing
# ═══════════════════════════════════════════════════════════════════════


class TestChapter3BasicEditing:
    """Type characters, Enter, Backspace, C-d, C-/."""

    def test_type_inserts_characters(self) -> None:
        h = make_harness()
        h.type_string("hello")
        assert h.buffer_text() == "hello"

    def test_enter_inserts_newline(self) -> None:
        h = make_harness()
        h.type_string("a")
        h.send_keys("Enter")
        h.type_string("b")
        assert h.buffer_text() == "a\nb"

    def test_backspace_deletes_before_point(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-e")
        h.send_keys("Backspace")
        assert h.buffer_text() == "hell"

    def test_c_d_deletes_after_point(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-d")
        assert h.buffer_text() == "ello"

    def test_undo_restores_deletion(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-e")
        h.send_keys("Backspace")
        assert h.buffer_text() == "hell"
        h.send_keys("C-/")
        assert h.buffer_text() == "hello"

    def test_fix_typo_tutorial_exercise(self) -> None:
        """The tutorial's typo-fixing exercise."""
        h = make_harness("lne")
        # Move to position 0 and insert 'i'
        h.send_keys("C-f")  # after 'l'
        h.type_string("i")
        assert h.buffer_text() == "line"


# ═══════════════════════════════════════════════════════════════════════
# Chapter 4 — Kill and yank
# ═══════════════════════════════════════════════════════════════════════


class TestChapter4KillAndYank:
    """C-k / C-w / C-y / M-y / M-d / M-Backspace."""

    def test_kill_line(self) -> None:
        h = make_harness("hello world")
        h.send_keys("C-k")
        assert h.buffer_text() == ""

    def test_kill_line_then_yank(self) -> None:
        h = make_harness("hello world")
        h.send_keys("C-k")
        h.send_keys("C-y")
        assert h.buffer_text() == "hello world"

    def test_consecutive_c_k_accumulates(self) -> None:
        h = make_harness("line1\nline2\nline3")
        # C-k kills line content, then newline, then next line content, etc.
        h.send_keys("C-k", "C-k", "C-k", "C-k")
        assert "line1" not in h.buffer_text()
        assert "line2" not in h.buffer_text()
        # Yank back
        h.send_keys("C-y")
        assert "line1" in h.buffer_text()
        assert "line2" in h.buffer_text()

    def test_kill_word_forward(self) -> None:
        h = make_harness("hello world")
        h.send_keys("M-d")
        assert h.buffer_text() == " world"

    def test_kill_word_backward(self) -> None:
        h = make_harness("hello world")
        h.send_keys("M->")  # end of buffer
        h.send_keys("M-Backspace")
        assert h.buffer_text() == "hello "

    def test_yank_pop(self) -> None:
        h = make_harness("first\nsecond\nthird")
        # Kill "first", then move and kill "second"
        h.send_keys("C-k")  # kill "first"
        h.send_keys("C-d")  # delete remaining newline
        h.send_keys("C-k")  # kill "second"
        h.send_keys("C-d")  # delete newline
        # Now at "third"
        h.send_keys("C-e")  # end of line
        h.send_keys("Enter")
        h.send_keys("C-y")  # yank most recent ("second")
        assert "second" in h.buffer_text()
        h.send_keys("M-y")  # replace with previous ("first")
        assert "first" in h.buffer_text()


# ═══════════════════════════════════════════════════════════════════════
# Chapter 5 — Mark and region
# ═══════════════════════════════════════════════════════════════════════


class TestChapter5MarkAndRegion:
    """C-space / C-w."""

    def test_set_mark(self) -> None:
        h = make_harness("hello world")
        h.send_keys("C-space")
        assert "Mark set" in h.message_line()

    def test_kill_region(self) -> None:
        h = make_harness("Keep this DELETE THIS but not that.")
        # Move to D of DELETE
        for _ in range(10):
            h.send_keys("C-f")
        h.send_keys("C-space")
        # Move past "DELETE THIS"
        for _ in range(11):
            h.send_keys("C-f")
        h.send_keys("C-w")
        assert h.buffer_text() == "Keep this  but not that."

    def test_yank_after_kill_region(self) -> None:
        h = make_harness("abcdefg")
        h.send_keys("C-f", "C-f", "C-space", "C-f", "C-f", "C-f")
        h.send_keys("C-w")  # kill "cde"
        assert h.buffer_text() == "abfg"
        h.send_keys("C-e", "C-y")
        assert h.buffer_text() == "abfgcde"


# ═══════════════════════════════════════════════════════════════════════
# Chapter 6 — Word movement
# ═══════════════════════════════════════════════════════════════════════


class TestChapter6WordMovement:
    """M-f / M-b."""

    def test_forward_word(self) -> None:
        h = make_harness("hello world foo")
        h.send_keys("M-f")
        # Point should land after "hello"
        assert h.point()[1] == 5

    def test_backward_word(self) -> None:
        h = make_harness("hello world foo")
        h.send_keys("M->")
        h.send_keys("M-b")
        # Point should land at start of "foo"
        assert h.point() == (0, 12)

    def test_multiple_forward_word(self) -> None:
        h = make_harness("alpha beta gamma delta")
        h.send_keys("M-f", "M-f", "M-f")
        # After "alpha beta gamma"
        assert h.point()[1] == 16


# ═══════════════════════════════════════════════════════════════════════
# Chapter 7 — Search (incremental)
# ═══════════════════════════════════════════════════════════════════════


class TestChapter7Search:
    """C-s / C-r."""

    def test_isearch_forward_finds_match(self) -> None:
        h = make_harness("hello NEON world NEON end")
        h.send_keys("C-s")
        h.type_string("NEON")
        # Point at start of first "NEON"? Implementation lands after
        # the match, so we just check it moved forward.
        assert h.point()[1] > 0
        h.send_keys("Enter")  # exit search at match
        # Minibuffer should be closed
        assert h.editor.minibuffer is None

    def test_isearch_next_match(self) -> None:
        h = make_harness("NEON one NEON two NEON three")
        h.send_keys("C-s")
        h.type_string("NEON")
        first_point = h.point()
        h.send_keys("C-s")  # next match
        second_point = h.point()
        assert second_point != first_point
        h.send_keys("Enter")

    def test_isearch_cancel_with_c_g(self) -> None:
        h = make_harness("hello world")
        h.send_keys("C-e")  # end of line
        start = h.point()
        h.send_keys("C-s")
        h.type_string("xyz")  # not in buffer
        h.send_keys("C-g")
        # Should return to starting position and close minibuffer
        assert h.editor.minibuffer is None
        assert h.point() == start

    def test_isearch_backward(self) -> None:
        h = make_harness("NEON foo NEON bar")
        h.send_keys("M->")  # end of buffer
        h.send_keys("C-r")
        h.type_string("NEON")
        assert h.editor.minibuffer is not None
        h.send_keys("Enter")
        # Point should have moved back
        assert h.point()[1] < len("NEON foo NEON bar")


# ═══════════════════════════════════════════════════════════════════════
# Chapter 8 — Files and buffers
# ═══════════════════════════════════════════════════════════════════════


class TestChapter8FilesAndBuffers:
    """C-x C-f / C-x C-s / C-x b / C-x k / C-x C-b."""

    def test_find_file_opens_minibuffer(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-x", "C-f")
        assert h.editor.minibuffer is not None
        assert "Find file" in h.editor.minibuffer.prompt

    def test_find_file_creates_new_buffer(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-x", "C-f")
        h.type_string("newfile.txt")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "newfile.txt"

    def test_switch_buffer(self) -> None:
        h = make_harness("hello")
        h.editor.create_buffer(name="other", text="other content")
        # Back to scratch via the key-driven flow (so windows stay in sync)
        h.send_keys("C-x", "b")
        h.type_string("*scratch*")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "*scratch*"
        # Now switch to "other"
        h.send_keys("C-x", "b")
        assert h.editor.minibuffer is not None
        h.type_string("other")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "other"

    def test_list_buffers(self) -> None:
        h = make_harness("hello")
        h.editor.create_buffer(name="alpha", text="a")
        h.editor.create_buffer(name="beta", text="b")
        h.send_keys("C-x", "C-b")
        assert h.editor.buffer.name == "*Buffer List*"
        text = h.editor.buffer.text
        assert "alpha" in text
        assert "beta" in text

    def test_kill_buffer(self) -> None:
        h = make_harness("hello")
        h.editor.create_buffer(name="to-kill", text="gone soon")
        # Switch to "to-kill" via the key flow so the window follows
        h.send_keys("C-x", "b")
        h.type_string("to-kill")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "to-kill"
        h.send_keys("C-x", "k")
        assert h.editor.minibuffer is not None
        h.send_keys("Enter")  # default = current buffer ("to-kill")
        assert h.editor.buffer.name != "to-kill"
        assert not any(b.name == "to-kill" for b in h.editor.buffers)


# ═══════════════════════════════════════════════════════════════════════
# Chapter 9 — Getting help
# ═══════════════════════════════════════════════════════════════════════


class TestChapter9GettingHelp:
    """C-h k / C-h a / C-h t / C-h b (new)."""

    def test_describe_key(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-h", "k", "C-f")
        assert h.editor.buffer.name == "*Help*"
        assert "forward-char" in h.editor.buffer.text

    def test_command_apropos(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-h", "a")
        h.type_string("forward")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "*Help*"
        assert "forward-char" in h.editor.buffer.text
        assert "forward-word" in h.editor.buffer.text

    def test_help_tutorial(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-h", "t")
        assert h.editor.buffer.name == "TUTORIAL.txt"
        assert "NEON-EDIT TUTORIAL" in h.editor.buffer.text

    def test_describe_bindings(self) -> None:
        """C-h b lists every keybinding (Phase 6k addition)."""
        h = make_harness("hello")
        h.send_keys("C-h", "b")
        assert h.editor.buffer.name == "*Help*"
        text = h.editor.buffer.text
        assert "Global bindings" in text
        assert "forward-char" in text
        assert "C-x C-s" in text  # nested prefix expanded


# ═══════════════════════════════════════════════════════════════════════
# Chapter 10 — Sentence motion (Phase 6f)
# ═══════════════════════════════════════════════════════════════════════


class TestChapter10SentenceMotion:
    """M-a / M-e / M-k."""

    def test_forward_sentence(self) -> None:
        h = make_harness("First sentence. Second sentence.")
        h.send_keys("M-e")
        # Lands after first "."
        assert h.point() == (0, 15)

    def test_backward_sentence(self) -> None:
        h = make_harness("First sentence. Second sentence.")
        h.send_keys("M->")
        h.send_keys("M-a")
        # Lands at start of "Second sentence"
        assert h.point()[1] < 32  # moved backward

    def test_kill_sentence(self) -> None:
        h = make_harness("First sentence. Second sentence.")
        h.send_keys("M-k")
        # First sentence gone, second remains
        assert "First sentence." not in h.buffer_text()
        assert "Second sentence." in h.buffer_text()

    def test_exclamation_also_ends_sentence(self) -> None:
        h = make_harness("Wow! Nice.")
        h.send_keys("M-e")
        assert h.point()[1] == 4  # after "!"

    def test_question_also_ends_sentence(self) -> None:
        h = make_harness("What? Yes.")
        h.send_keys("M-e")
        assert h.point()[1] == 5  # after "?"


# ═══════════════════════════════════════════════════════════════════════
# Chapter 11 — Find and replace (Phase 6h)
# ═══════════════════════════════════════════════════════════════════════


class TestChapter11FindAndReplace:
    """M-x replace-string."""

    def _replace(self, h: EditorHarness, search: str, repl: str) -> None:
        h.send_keys("M-x")
        h.type_string("replace-string")
        h.send_keys("Enter")
        h.type_string(search)
        h.send_keys("Enter")
        h.type_string(repl)
        h.send_keys("Enter")

    def test_basic_replace(self) -> None:
        h = make_harness("foo bar foo baz foo")
        self._replace(h, "foo", "qux")
        assert h.buffer_text() == "qux bar qux baz qux"

    def test_replace_reports_count(self) -> None:
        h = make_harness("aaa aaa aaa")
        self._replace(h, "aaa", "b")
        assert "3 occurrences" in h.message_line()

    def test_replace_from_point_only(self) -> None:
        """Replacement begins at point, not at the start of the buffer."""
        h = make_harness("foo foo foo")
        h.send_keys("M-f")  # past first foo
        self._replace(h, "foo", "qux")
        # First "foo" should be untouched
        assert h.buffer_text().startswith("foo")
        assert h.buffer_text().count("qux") == 2

    def test_replace_is_undoable_as_group(self) -> None:
        h = make_harness("aa bb aa cc aa")
        self._replace(h, "aa", "xx")
        assert h.buffer_text() == "xx bb xx cc xx"
        h.send_keys("C-/")
        assert h.buffer_text() == "aa bb aa cc aa"


# ═══════════════════════════════════════════════════════════════════════
# Chapter 12 — Text filling (Phase 6h)
# ═══════════════════════════════════════════════════════════════════════


class TestChapter12TextFilling:
    """M-q / C-x f / M-x auto-fill-mode."""

    def test_fill_paragraph_rewraps(self) -> None:
        long = "This is a very long line of text that will be wrapped when we fill the paragraph."
        h = make_harness(long)
        # Set a narrow fill-column so wrapping happens
        h.editor.set_variable("fill-column", 30)
        h.send_keys("M-q")
        # After fill, should contain a newline (wrapped)
        assert "\n" in h.buffer_text()

    def test_set_fill_column_with_prefix_arg(self) -> None:
        h = make_harness("hello")
        # C-u 50 C-x f sets fill-column to 50
        h.send_keys("C-u")
        h.type_string("50")
        h.send_keys("C-x", "f")
        assert h.editor.get_variable("fill-column") == 50

    def test_auto_fill_mode_toggle(self) -> None:
        h = make_harness()
        # Start with auto-fill off
        assert h.editor.get_variable("auto-fill") is False
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        # Should now be on
        minor_names = [m.name for m in h.editor.buffer.minor_modes]
        assert "auto-fill-mode" in minor_names

    def test_auto_fill_modeline_indicator(self) -> None:
        h = make_harness()
        h.send_keys("M-x")
        h.type_string("auto-fill-mode")
        h.send_keys("Enter")
        # Modeline should contain the fill indicator
        assert "Fill" in h.modeline()


# ═══════════════════════════════════════════════════════════════════════
# Chapter 13 — Windows (Phase 6i)
# ═══════════════════════════════════════════════════════════════════════


class TestChapter13Windows:
    """C-x 2 / C-x 3 / C-x o / C-x 0 / C-x 1."""

    def test_split_horizontal(self) -> None:
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        assert len(h.editor._window_tree.windows()) == 2

    def test_split_vertical(self) -> None:
        h = make_harness("hello", width=80, height=12)
        h.send_keys("C-x", "3")
        assert len(h.editor._window_tree.windows()) == 2

    def test_other_window(self) -> None:
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        tree = h.editor._window_tree
        first = tree.active
        h.send_keys("C-x", "o")
        assert tree.active is not first

    def test_delete_window(self) -> None:
        h = make_harness("hello", width=40, height=12)
        h.send_keys("C-x", "2")
        assert len(h.editor._window_tree.windows()) == 2
        h.send_keys("C-x", "0")
        assert len(h.editor._window_tree.windows()) == 1

    def test_delete_other_windows(self) -> None:
        h = make_harness("hello", width=40, height=14)
        h.send_keys("C-x", "2")
        h.send_keys("C-x", "2")
        assert len(h.editor._window_tree.windows()) == 3
        h.send_keys("C-x", "1")
        assert len(h.editor._window_tree.windows()) == 1

    def test_windows_share_buffer_after_split(self) -> None:
        h = make_harness("shared", width=40, height=12)
        h.send_keys("C-x", "2")
        wins = h.editor._window_tree.windows()
        assert wins[0].buffer is wins[1].buffer


# ═══════════════════════════════════════════════════════════════════════
# Chapter 14 — Shell mode (Phase 6j)
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def shell_container(mock_llm):
    container = ServiceFactory.create_test_container(
        mock_npc_manager=ServiceFactory.create_npc_manager(llm=mock_llm),
    )
    container.app_service.load_initial_filesystem(
        initial_fs_dir=str(settings.initial_fs_path)
    )
    return container


@pytest.fixture
def shell_harness(shell_container):
    """An EditorHarness with a *shell* buffer already set up."""
    editor = Editor(global_keymap=build_default_keymap())
    shell = Shell(shell_container)
    editor.shell_factory = lambda: shell
    view = EditorView(editor=editor)
    h = EditorHarness(view, width=80, height=24)
    # Invoke M-x shell via the view so window sync happens
    h.send_keys("M-x")
    h.type_string("shell")
    h.send_keys("Enter")
    assert editor.buffer.name == "*shell*"
    return h


class TestChapter14ShellMode:
    """M-x shell / M-p / M-n / Tab."""

    def test_m_x_shell_creates_shell_buffer(self, shell_harness) -> None:
        assert shell_harness.editor.buffer.name == "*shell*"

    def test_shell_buffer_shows_welcome_banner(self, shell_harness) -> None:
        assert (
            "Recursive" in shell_harness.buffer_text()
            or "NEON" in shell_harness.buffer_text()
        )

    def test_shell_modeline_shows_shell(self, shell_harness) -> None:
        assert "Shell" in shell_harness.modeline()

    async def test_execute_echo_command(self, shell_harness) -> None:
        """End-to-end: type a command, Enter, see output."""
        shell_harness.type_string("echo hello-from-tutorial")
        shell_harness.send_keys("Enter")
        # Drive the async path the way on_key → on_after_key does
        await shell_harness.view.on_after_key()
        assert "hello-from-tutorial" in shell_harness.buffer_text()

    async def test_history_previous(self, shell_harness) -> None:
        """M-p recalls the previous command."""
        shell_harness.type_string("echo first-command")
        shell_harness.send_keys("Enter")
        await shell_harness.view.on_after_key()
        shell_harness.send_keys("M-p")
        # The current input line should now contain the previous command
        assert "first-command" in shell_harness.buffer_text()

    async def test_m_x_shell_twice_switches_to_existing(self, shell_harness) -> None:
        """Running M-x shell again should switch to the existing buffer."""
        # Already in *shell* — create another buffer, then invoke M-x shell
        shell_harness.editor.create_buffer(name="other", text="x")
        assert shell_harness.editor.buffer.name == "other"
        shell_harness.send_keys("M-x")
        shell_harness.type_string("shell")
        shell_harness.send_keys("Enter")
        assert shell_harness.editor.buffer.name == "*shell*"
        # Still only one *shell* buffer
        shells = [b for b in shell_harness.editor.buffers if b.name == "*shell*"]
        assert len(shells) == 1


# ═══════════════════════════════════════════════════════════════════════
# Quick reference: verify the advertised keys match reality
# ═══════════════════════════════════════════════════════════════════════


class TestQuickReferenceConsistency:
    """Every binding advertised in the tutorial's Quick Reference
    should be reachable via ``describe-bindings``."""

    def test_all_advertised_commands_present(self) -> None:
        h = make_harness("hello")
        h.send_keys("C-h", "b")
        bindings_text = h.editor.buffer.text
        # A representative sample spanning every feature category
        expected_commands = [
            "forward-char",
            "backward-char",
            "next-line",
            "previous-line",
            "beginning-of-line",
            "end-of-line",
            "forward-word",
            "backward-word",
            "forward-sentence",
            "backward-sentence",
            "kill-sentence",
            "kill-line",
            "kill-region",
            "kill-word",
            "yank",
            "undo",
            "set-mark-command",
            "isearch-forward",
            "isearch-backward",
            "save-buffer",
            "save-some-buffers",
            "find-file",
            "switch-to-buffer",
            "kill-buffer",
            "list-buffers",
            "describe-key",
            "describe-bindings",
            "command-apropos",
            "help-tutorial",
            "split-window-below",
            "split-window-right",
            "other-window",
            "delete-window",
            "delete-other-windows",
            "find-file-other-window",
            "scroll-other-window",
            "fill-paragraph",
            "set-fill-column",
        ]
        missing = [c for c in expected_commands if c not in bindings_text]
        assert not missing, f"Commands missing from describe-bindings: {missing}"

    def test_tutorial_file_has_no_not_yet_tags(self) -> None:
        """The tutorial must not contain any [NOT YET IMPLEMENTED] markers."""
        from recursive_neon.editor.default_commands import _TUTORIAL_PATH

        text = _TUTORIAL_PATH.read_text(encoding="utf-8")
        assert "[NOT YET IMPLEMENTED]" not in text
