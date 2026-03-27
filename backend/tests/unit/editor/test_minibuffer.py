"""Tests for the Minibuffer and commands that use it."""

from __future__ import annotations

from recursive_neon.editor.default_commands import build_default_keymap
from recursive_neon.editor.editor import Editor
from recursive_neon.editor.minibuffer import Minibuffer


# ═══════════════════════════════════════════════════════════════════════
# Minibuffer standalone
# ═══════════════════════════════════════════════════════════════════════


class TestMinibufferBasic:
    def test_initial_state(self):
        mb = Minibuffer("M-x ", lambda s: None)
        assert mb.prompt == "M-x "
        assert mb.text == ""
        assert mb.cursor == 0
        assert mb.display == "M-x "

    def test_insert_chars(self):
        mb = Minibuffer("M-x ", lambda s: None)
        mb.process_key("h")
        mb.process_key("e")
        mb.process_key("l")
        assert mb.text == "hel"
        assert mb.cursor == 3

    def test_backspace(self):
        mb = Minibuffer("M-x ", lambda s: None, initial="hello")
        mb.process_key("Backspace")
        assert mb.text == "hell"
        assert mb.cursor == 4

    def test_backspace_at_start(self):
        mb = Minibuffer("M-x ", lambda s: None)
        mb.process_key("Backspace")
        assert mb.text == ""

    def test_c_a_goes_to_start(self):
        mb = Minibuffer("M-x ", lambda s: None, initial="hello")
        mb.process_key("C-a")
        assert mb.cursor == 0

    def test_c_e_goes_to_end(self):
        mb = Minibuffer("M-x ", lambda s: None, initial="hello")
        mb.process_key("C-a")
        mb.process_key("C-e")
        assert mb.cursor == 5

    def test_c_k_kills_to_end(self):
        mb = Minibuffer("M-x ", lambda s: None, initial="hello")
        mb.process_key("C-a")
        mb.process_key("C-f")
        mb.process_key("C-f")
        mb.process_key("C-k")
        assert mb.text == "he"

    def test_arrow_keys(self):
        mb = Minibuffer("M-x ", lambda s: None, initial="hello")
        mb.process_key("ArrowLeft")
        assert mb.cursor == 4
        mb.process_key("ArrowRight")
        assert mb.cursor == 5

    def test_display_includes_prompt(self):
        mb = Minibuffer("Find: ", lambda s: None, initial="foo")
        assert mb.display == "Find: foo"


class TestMinibufferEnterCancel:
    def test_enter_calls_callback(self):
        result = {}
        mb = Minibuffer("M-x ", lambda s: result.update(text=s), initial="hello")
        active = mb.process_key("Enter")
        assert not active
        assert result["text"] == "hello"
        assert not mb.cancelled

    def test_c_g_cancels(self):
        called = []
        mb = Minibuffer("M-x ", lambda s: called.append(s))
        mb.process_key("h")
        active = mb.process_key("C-g")
        assert not active
        assert mb.cancelled
        assert not called  # callback not invoked

    def test_escape_cancels(self):
        mb = Minibuffer("M-x ", lambda s: None)
        active = mb.process_key("Escape")
        assert not active
        assert mb.cancelled


class TestMinibufferCompletion:
    def test_tab_completes(self):
        def completer(text: str) -> list[str]:
            options = ["forward-char", "forward-word", "find-file"]
            return [o for o in options if o.startswith(text)]

        mb = Minibuffer("M-x ", lambda s: None, completer=completer)
        mb.process_key("f")
        mb.process_key("Tab")
        assert mb.text in ["forward-char", "forward-word", "find-file"]

    def test_tab_cycles(self):
        options = ["alpha", "beta"]
        mb = Minibuffer("M-x ", lambda s: None, completer=lambda t: options)
        mb.process_key("Tab")
        first = mb.text
        mb.process_key("Tab")
        second = mb.text
        assert first != second
        assert {first, second} == {"alpha", "beta"}

    def test_tab_no_completions(self):
        mb = Minibuffer("M-x ", lambda s: None, completer=lambda t: [])
        mb.process_key("x")
        mb.process_key("Tab")
        assert mb.text == "x"

    def test_no_completer(self):
        mb = Minibuffer("M-x ", lambda s: None)
        mb.process_key("x")
        mb.process_key("Tab")
        assert mb.text == "x"


class TestMinibufferOnChange:
    def test_on_change_called(self):
        changes = []
        mb = Minibuffer(
            "Search: ",
            lambda s: None,
            on_change=lambda t: changes.append(t),
        )
        mb.process_key("a")
        mb.process_key("b")
        assert changes == ["a", "ab"]

    def test_backspace_triggers_on_change(self):
        changes = []
        mb = Minibuffer(
            "Search: ",
            lambda s: None,
            initial="abc",
            on_change=lambda t: changes.append(t),
        )
        mb.process_key("Backspace")
        assert changes == ["ab"]


# ═══════════════════════════════════════════════════════════════════════
# Editor minibuffer integration
# ═══════════════════════════════════════════════════════════════════════


def make_editor(text: str = "") -> Editor:
    ed = Editor(global_keymap=build_default_keymap())
    ed.create_buffer(text=text)
    return ed


class TestEditorMinibuffer:
    def test_minibuffer_intercepts_keys(self):
        ed = make_editor("hello")
        ed.start_minibuffer("Test: ", lambda s: None)
        assert ed.minibuffer is not None
        ed.process_key("x")
        # x should go to minibuffer, not the buffer
        assert ed.buffer.text == "hello"
        assert ed.minibuffer is not None
        assert ed.minibuffer.text == "x"

    def test_enter_dismisses_minibuffer(self):
        result = {}
        ed = make_editor()
        ed.start_minibuffer("Test: ", lambda s: result.update(val=s))
        ed.process_key("h")
        ed.process_key("i")
        ed.process_key("Enter")
        assert ed.minibuffer is None
        assert result["val"] == "hi"

    def test_c_g_cancels_minibuffer(self):
        ed = make_editor()
        ed.start_minibuffer("Test: ", lambda s: None)
        ed.process_key("C-g")
        assert ed.minibuffer is None
        assert ed.message == "Quit"


# ═══════════════════════════════════════════════════════════════════════
# M-x (execute-extended-command)
# ═══════════════════════════════════════════════════════════════════════


class TestMx:
    def test_m_x_opens_minibuffer(self):
        ed = make_editor("hello")
        ed.process_key("M-x")
        assert ed.minibuffer is not None
        assert "M-x" in ed.minibuffer.prompt

    def test_m_x_runs_command(self):
        ed = make_editor("hello")
        ed.process_key("M-x")
        for ch in "end-of-line":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.point.col == 5

    def test_m_x_unknown_command(self):
        ed = make_editor()
        ed.process_key("M-x")
        for ch in "nonexistent":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert "Unknown" in ed.message

    def test_m_x_tab_completes(self):
        ed = make_editor()
        ed.process_key("M-x")
        for ch in "forw":
            ed.process_key(ch)
        ed.process_key("Tab")
        assert ed.minibuffer is not None
        assert ed.minibuffer.text.startswith("forward-")


# ═══════════════════════════════════════════════════════════════════════
# Buffer switching
# ═══════════════════════════════════════════════════════════════════════


class TestBufferSwitching:
    def test_c_x_b_opens_minibuffer(self):
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("b")
        assert ed.minibuffer is not None
        assert "buffer" in ed.minibuffer.prompt.lower()

    def test_switch_to_existing_buffer(self):
        ed = make_editor("aaa")
        ed.buffer.name = "buf-a"
        ed.create_buffer(name="buf-b", text="bbb")
        assert ed.buffer.name == "buf-b"
        # Switch back to buf-a
        ed.process_key("C-x")
        ed.process_key("b")
        for ch in "buf-a":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.name == "buf-a"

    def test_switch_creates_new_buffer(self):
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("b")
        for ch in "new-buf":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.name == "new-buf"

    def test_list_buffers(self):
        ed = make_editor("hello")
        ed.buffer.name = "test.txt"
        ed.process_key("C-x")
        ed.process_key("C-b")
        assert ed.buffer.name == "*Buffer List*"
        assert ed.buffer.read_only
        assert "test.txt" in ed.buffer.text


# ═══════════════════════════════════════════════════════════════════════
# File operations
# ═══════════════════════════════════════════════════════════════════════


class TestFileOperations:
    def test_write_file_sets_path(self):
        ed = make_editor("hello")
        ed.process_key("C-x")
        ed.process_key("C-w")
        assert ed.minibuffer is not None
        for ch in "test.txt":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.filepath == "test.txt"
        assert ed.buffer.name == "test.txt"

    def test_write_file_calls_save(self):
        saved = {}
        ed = make_editor("hello")
        ed.save_callback = lambda buf: (saved.update(text=buf.text), True)[1]
        ed.process_key("C-x")
        ed.process_key("C-w")
        for ch in "out.txt":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert saved["text"] == "hello"
        assert not ed.buffer.modified

    def test_find_file_opens_minibuffer(self):
        ed = make_editor()
        ed.process_key("C-x")
        ed.process_key("C-f")
        assert ed.minibuffer is not None

    def test_find_file_creates_new_buffer(self):
        ed = make_editor("original")
        ed.process_key("C-x")
        ed.process_key("C-f")
        for ch in "new.txt":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.name == "new.txt"
        assert ed.buffer.filepath == "new.txt"

    def test_find_file_loads_via_callback(self):
        ed = make_editor("original")
        ed.open_callback = lambda path: "loaded content"
        ed.process_key("C-x")
        ed.process_key("C-f")
        for ch in "data.txt":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.text == "loaded content"
        assert ed.buffer.name == "data.txt"

    def test_find_file_switches_to_existing(self):
        ed = make_editor("aaa")
        ed.buffer.filepath = "aaa.txt"
        ed.buffer.name = "aaa.txt"
        ed.create_buffer(name="bbb.txt", text="bbb")
        ed.buffer.filepath = "bbb.txt"
        # Now find aaa.txt — should switch, not create new
        ed.process_key("C-x")
        ed.process_key("C-f")
        for ch in "aaa.txt":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.name == "aaa.txt"
        assert len(ed.buffers) == 2  # didn't create a third

    def test_write_file_save_uses_buffer_filepath(self):
        """Save callback should use buf.filepath, not the initial captured path."""
        saved_paths: list[str] = []
        ed = make_editor("content")
        # Simulate a save callback that tracks what filepath the buffer has
        def save_cb(buf):
            saved_paths.append(buf.filepath or "")
            return True

        ed.save_callback = save_cb
        # No initial filepath set — buffer starts as *scratch*
        assert ed.buffer.filepath is None
        # Write-file sets buf.filepath then calls save_callback
        ed.process_key("C-x")
        ed.process_key("C-w")
        for ch in "new_path.txt":
            ed.process_key(ch)
        ed.process_key("Enter")
        assert ed.buffer.filepath == "new_path.txt"
        assert saved_paths == ["new_path.txt"]
        assert not ed.buffer.modified

    def test_find_file_tab_completion(self):
        """find-file should support tab completion via path_completer."""
        ed = make_editor("original")
        ed.path_completer = lambda partial: ["Documents/", "Downloads/"]
        ed.process_key("C-x")
        ed.process_key("C-f")
        assert ed.minibuffer is not None
        ed.process_key("Tab")
        assert ed.minibuffer.text == "Documents/"
        ed.process_key("Tab")
        assert ed.minibuffer.text == "Downloads/"

    def test_write_file_tab_completion(self):
        """write-file should support tab completion via path_completer."""
        ed = make_editor("text")
        ed.path_completer = lambda partial: ["readme.txt", "readme.md"]
        ed.process_key("C-x")
        ed.process_key("C-w")
        assert ed.minibuffer is not None
        for ch in "read":
            ed.process_key(ch)
        ed.process_key("Tab")
        assert ed.minibuffer.text == "readme.txt"
