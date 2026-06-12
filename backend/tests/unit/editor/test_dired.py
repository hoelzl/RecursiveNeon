"""Tests for dired-mode (editor/dired.py).

Behaviour is pinned against GNU Emacs 29.3 via the probe transcripts of
2026-06-12 and parity scenarios 31+. The listing *content* (synthesized
permissions/owner/link counts, exact column layout) cannot be verified
against Emacs — these unit tests are its ground truth, the parity
scenarios verify the shape (point motion, modeline, prompts, messages).
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

from recursive_neon.editor.dired import (
    DIRED_FREE_SPACE,
    DiredEntry,
    _format_mtime,
    open_dired,
)

from .harness import EditorHarness, make_harness

# A fixed "recent" timestamp: tests build expected date stamps from the
# same value, so render-vs-expectation can never drift.
NOW = datetime.now().replace(microsecond=0)
DATE = f"{('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')[NOW.month - 1]} {NOW.day:2d} {NOW.hour:02d}:{NOW.minute:02d}"  # noqa: E501


class FakeProvider:
    """In-memory DiredProvider over a nested-dict tree.

    Directories are dicts, files are str contents. All mtimes are NOW
    unless overridden via *mtimes* (path → datetime).
    """

    def __init__(self, tree: dict, mtimes: dict | None = None) -> None:
        self.tree = tree
        self.mtimes = mtimes or {}

    # -- helpers -----------------------------------------------------------
    def _node(self, path: str):
        node: dict | str = self.tree
        for part in [p for p in path.split("/") if p]:
            if not isinstance(node, dict) or part not in node:
                raise FileNotFoundError(f"{path}: No such file or directory")
            node = node[part]
        return node

    def _parent_and_name(self, path: str) -> tuple[dict, str]:
        parts = [p for p in path.split("/") if p]
        if not parts:
            raise ValueError("cannot operate on the root directory")
        parent = self._node("/" + "/".join(parts[:-1]))
        if not isinstance(parent, dict):
            raise NotADirectoryError(f"{path}: Not a directory")
        return parent, parts[-1]

    def _entry(self, name: str, node: dict | str, path: str) -> DiredEntry:
        if isinstance(node, dict):
            nsub = sum(1 for v in node.values() if isinstance(v, dict))
            return DiredEntry(
                name=name,
                is_dir=True,
                mtime=self.mtimes.get(path, NOW),
                nsubdirs=nsub,
            )
        return DiredEntry(
            name=name,
            is_dir=False,
            size=len(node.encode("utf-8")),
            mtime=self.mtimes.get(path, NOW),
        )

    # -- DiredProvider ------------------------------------------------------
    def list_dir(self, path: str) -> list[DiredEntry]:
        node = self._node(path)
        if not isinstance(node, dict):
            raise NotADirectoryError(f"{path}: Not a directory")
        return [
            self._entry(name, child, f"{path.rstrip('/')}/{name}")
            for name, child in node.items()
        ]

    def metadata(self, path: str) -> DiredEntry:
        name = path.rsplit("/", 1)[-1] or "/"
        return self._entry(name, self._node(path), path)

    def is_dir(self, path: str) -> bool | None:
        try:
            return isinstance(self._node(path), dict)
        except FileNotFoundError:
            return None

    def create_dir(self, path: str) -> None:
        parent, name = self._parent_and_name(path)
        if name in parent:
            raise ValueError(f"{name} already exists")
        parent[name] = {}

    def delete(self, path: str) -> None:
        parent, name = self._parent_and_name(path)
        if name not in parent:
            raise FileNotFoundError(f"{path}: No such file or directory")
        del parent[name]

    def _resolve_target(self, new: str, default_name: str) -> tuple[dict, str, str]:
        try:
            node = self._node(new)
            if isinstance(node, dict):
                return node, default_name, f"{new.rstrip('/')}/{default_name}"
        except FileNotFoundError:
            pass
        parent, name = self._parent_and_name(new)
        return parent, name, new

    def rename(self, old: str, new: str) -> str:
        src_parent, src_name = self._parent_and_name(old)
        node = src_parent[src_name]
        parent, name, result = self._resolve_target(new, src_name)
        if name in parent:
            raise ValueError(f"{name} already exists")
        del src_parent[src_name]
        parent[name] = node
        return result

    def copy(self, old: str, new: str) -> str:
        node = self._node(old)
        _, src_name = self._parent_and_name(old)
        parent, name, result = self._resolve_target(new, src_name)
        if name in parent:
            raise ValueError(f"{name} already exists")
        parent[name] = copy.deepcopy(node)
        return result


def default_tree() -> dict:
    return {
        "home": {
            "user": {
                "alpha.txt": "alpha line\n",
                "beta.py": "print('beta')\n",
                "sub": {"gamma.txt": "gamma\n"},
            }
        }
    }


def make_dired_harness(
    tree: dict | None = None, *, open_listing: bool = True
) -> tuple[EditorHarness, FakeProvider]:
    h = make_harness("start text\n", width=80, height=24)
    h.editor.buffer.name = "start.txt"
    h.editor.buffer.filepath = "/home/user/start.txt"
    provider = FakeProvider(tree if tree is not None else default_tree())
    h.editor.dired_provider = provider
    h.editor.default_directory = "/home/user"

    def open_callback(path: str) -> str:
        try:
            node = provider._node(path)
        except FileNotFoundError:
            return ""
        return node if isinstance(node, str) else ""

    h.editor.open_callback = open_callback
    if open_listing:
        h.send_keys("C-x", "d", "Enter")  # prompt pre-filled with /home/user/
    return h, provider


def submit_minibuffer(h: EditorHarness, text: str, *, clear: bool = False) -> None:
    assert h.editor.minibuffer is not None, "no minibuffer active"
    if clear:
        h.send_keys("C-a", "C-k")
    h.type_string(text)
    h.send_keys("Enter")


NAME_COL = 43  # 2 mark + 10 perms + 1+1 nlink + 1+4 owner + 1+4 group + 1+4 size + 1+12 date + 1


# ═══════════════════════════════════════════════════════════════════════
# Layout
# ═══════════════════════════════════════════════════════════════════════


class TestDiredLayout:
    def test_listing_format_exact(self) -> None:
        h, _ = make_dired_harness()
        assert h.editor.buffer.text == (
            f"  /home/user: ({DIRED_FREE_SPACE} available)\n"
            f"  drwxr-xr-x 3 neon neon 4096 {DATE} .\n"
            f"  drwxr-xr-x 3 neon neon 4096 {DATE} ..\n"
            f"  -rw-r--r-- 1 neon neon   11 {DATE} alpha.txt\n"
            f"  -rw-r--r-- 1 neon neon   14 {DATE} beta.py\n"
            f"  drwxr-xr-x 2 neon neon 4096 {DATE} sub\n"
        )

    def test_modeline_and_initial_point(self) -> None:
        h, _ = make_dired_harness()
        ml = h.modeline()
        assert ml.startswith("-UUU:%%-  F1  user")
        assert " L4 " in ml
        assert "(Dired by name)" in ml
        assert h.point() == (3, NAME_COL)

    def test_empty_directory(self) -> None:
        h, _ = make_dired_harness({"home": {"user": {}}})
        lines = h.editor.buffer.text.split("\n")
        assert len(lines) == 4  # header, ., .., trailing blank
        # Probe: point lands on the trailing blank line, column 0.
        assert h.point() == (3, 0)

    def test_buffer_named_after_basename_and_uniquified(self) -> None:
        h, _ = make_dired_harness({"home": {"user": {"sub": {}}, "other": {"sub": {}}}})
        assert h.editor.buffer.name == "user"
        open_dired(h.editor, "/home/user/sub")
        assert h.editor.buffer.name == "sub"
        open_dired(h.editor, "/home/other/sub")
        assert h.editor.buffer.name == "sub<2>"

    def test_old_mtime_renders_year(self) -> None:
        now = datetime(2026, 6, 12, 20, 40)
        old = datetime(2025, 3, 5, 10, 0)
        assert _format_mtime(old, now) == "Mar  5  2025"
        assert _format_mtime(datetime(2026, 6, 1, 9, 5), now) == "Jun  1 09:05"
        # Future timestamps also use the year form (GNU ls).
        assert _format_mtime(now + timedelta(days=2), now) == "Jun 14  2026"

    def test_read_only_buffer(self) -> None:
        h, _ = make_dired_harness()
        before = h.editor.buffer.text
        h.send_keys("z")  # unbound printable → self-insert is blocked
        assert h.editor.buffer.text == before


# ═══════════════════════════════════════════════════════════════════════
# Navigation
# ═══════════════════════════════════════════════════════════════════════


class TestDiredNavigation:
    def test_n_and_p_land_on_filename(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("n")
        assert h.point() == (4, NAME_COL)
        h.send_keys("n")
        assert h.point() == (5, NAME_COL)
        h.send_keys("p")
        assert h.point() == (4, NAME_COL)

    def test_space_moves_down(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys(" ")
        assert h.point() == (4, NAME_COL)

    def test_p_walks_onto_dot_lines_then_header(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("p")  # ".." line, filename column
        assert h.point() == (2, NAME_COL)
        h.send_keys("p")  # "." line
        assert h.point() == (1, NAME_COL)
        h.send_keys("p")  # header — no filename, column 0
        assert h.point() == (0, 0)
        h.send_keys("p")  # at top: stays, silently
        assert h.point() == (0, 0)
        assert h.message_line().strip() == ""

    def test_n_at_end_of_buffer_stays(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("M->")
        assert h.point() == (6, 0)
        h.send_keys("n")
        assert h.point() == (6, 0)

    def test_ret_on_file_visits_it(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("Enter")  # point starts on alpha.txt
        assert h.editor.buffer.name == "alpha.txt"
        assert h.editor.buffer.text == "alpha line\n"
        assert h.editor.buffer.filepath == "/home/user/alpha.txt"

    def test_ret_on_already_open_file_switches(self) -> None:
        h, _ = make_dired_harness()
        h.editor.create_buffer(
            name="alpha.txt", text="stale", filepath="/home/user/alpha.txt"
        )
        h.editor.switch_to_buffer("user")
        h.send_keys("Enter")
        assert h.editor.buffer.text == "stale"  # reused, not re-read

    def test_ret_on_directory_descends(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("n", "n", "Enter")  # onto "sub"
        assert h.editor.buffer.name == "sub"
        assert h.editor.buffer.lines[0].startswith("  /home/user/sub:")
        assert h.point() == (3, NAME_COL)  # gamma.txt

    def test_ret_on_dot_and_dotdot(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("p", "p", "Enter")  # "." → same directory buffer
        assert h.editor.buffer.name == "user"
        h.send_keys("n", "Enter")  # ".." → parent
        assert h.editor.buffer.name == "home"
        assert h.editor.buffer.lines[0].startswith("  /home:")

    def test_ret_on_header_line_messages(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("M-<", "Enter")
        assert h.message_line().startswith("No file on this line")

    def test_up_directory_lands_on_child_line(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("^")
        assert h.editor.buffer.name == "home"
        line = h.editor.buffer.point.line
        assert h.editor.buffer.lines[line].endswith(" user")

    def test_quit_window_returns_to_previous_buffer(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("q")
        assert h.editor.buffer.name == "start.txt"
        # The dired buffer is buried — dropped to the bottom of the
        # recency order, like Emacs's bury-buffer.
        assert h.editor._mru[-1] == "user"

    def test_revisit_reuses_buffer(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("q")
        h.send_keys("C-x", "d", "Enter")
        assert h.editor.buffer.name == "user"
        assert sum(1 for b in h.editor.buffers if b.name.startswith("user")) == 1

    def test_revisit_after_change_hints_g(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("q")
        provider.tree["home"]["user"]["new.txt"] = "x\n"
        h.send_keys("C-x", "d", "Enter")
        assert h.message_line().startswith(
            "Directory has changed on disk; type g to update Dired"
        )
        # The listing itself is untouched until g.
        assert "new.txt" not in h.editor.buffer.text

    def test_g_reverts_and_keeps_point_file_and_marks(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("d")  # flag alpha.txt, point moves to beta.py
        provider.tree["home"]["user"]["aaa.txt"] = "x\n"
        h.send_keys("g")
        text = h.editor.buffer.text
        assert "aaa.txt" in text
        # New entry sorts first; alpha's D flag survived; point stayed
        # on beta.py (the file it was on).
        lines = text.split("\n")
        assert lines[3].endswith(" aaa.txt")
        assert lines[4].startswith("D ") and lines[4].endswith(" alpha.txt")
        assert h.editor.buffer.lines[h.editor.buffer.point.line].endswith(" beta.py")


# ═══════════════════════════════════════════════════════════════════════
# Flagging and deletion
# ═══════════════════════════════════════════════════════════════════════


class TestDiredFlagging:
    def test_d_flags_and_moves_down(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("d")
        assert h.editor.buffer.lines[3].startswith("D ")
        assert h.point() == (4, NAME_COL)
        assert h.editor.buffer.modified  # modeline %* — probed
        assert "-UUU:%*-" in h.modeline()

    def test_d_on_dot_lines_skips_silently(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("p", "d")  # on ".."
        assert not h.editor.buffer.lines[2].startswith("D")
        assert h.point() == (3, NAME_COL)
        assert h.message_line().strip() == ""

    def test_u_unflags_and_moves_down(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("d", "p", "u")
        assert h.editor.buffer.lines[3].startswith("  ")
        assert h.point() == (4, NAME_COL)

    def test_x_without_flags(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("x")
        assert h.message_line().startswith("(No deletions requested)")

    def test_x_single_file_yes(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("d", "x")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Delete alpha.txt (yes or no) "
        submit_minibuffer(h, "yes")
        assert "alpha.txt" not in provider.tree["home"]["user"]
        assert "alpha.txt" not in h.editor.buffer.text
        assert h.message_line().startswith("Deleting...done")
        # Point stays at the same line number (probe) — now beta.py.
        assert h.editor.buffer.lines[h.editor.buffer.point.line].endswith(" beta.py")

    def test_x_invalid_answer_reprompts(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("d", "x")
        submit_minibuffer(h, "y")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Delete alpha.txt (yes or no) "
        submit_minibuffer(h, "no")

    def test_x_answer_no_keeps_flags(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("d", "x")
        submit_minibuffer(h, "no")
        assert "alpha.txt" in provider.tree["home"]["user"]
        assert h.editor.buffer.lines[3].startswith("D ")
        assert h.message_line().startswith("(No deletions performed)")

    def test_x_multiple_pops_deletions_buffer(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("d", "d", "x")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Delete D [2 files] (yes or no) "
        popup = next(b for b in h.editor.buffers if b.name == " *Deletions*")
        assert popup.text == "alpha.txt\nbeta.py"
        assert popup.read_only and popup.modified  # probed modeline %*
        submit_minibuffer(h, "yes")
        assert "alpha.txt" not in provider.tree["home"]["user"]
        assert "beta.py" not in provider.tree["home"]["user"]
        assert all(b.name != " *Deletions*" for b in h.editor.buffers)
        assert h.editor._window_tree.is_single()

    def test_x_cancel_dismisses_popup_and_keeps_flags(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("d", "d", "x")
        h.send_keys("C-g")
        assert all(b.name != " *Deletions*" for b in h.editor.buffers)
        assert "alpha.txt" in provider.tree["home"]["user"]
        assert h.editor.buffer.lines[3].startswith("D ")

    def test_x_deletes_directories_recursively(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("n", "n", "d", "x")  # flag "sub"
        submit_minibuffer(h, "yes")
        assert "sub" not in provider.tree["home"]["user"]


# ═══════════════════════════════════════════════════════════════════════
# Create / rename / copy
# ═══════════════════════════════════════════════════════════════════════


class TestDiredCreateRenameCopy:
    def test_create_directory(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("+")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Create directory: "
        assert h.editor.minibuffer.text == "/home/user/"
        submit_minibuffer(h, "newdir")
        assert provider.tree["home"]["user"]["newdir"] == {}
        # Inserted at point's line (probe: before the entry point was on).
        assert h.editor.buffer.lines[3].endswith(" newdir")
        assert h.editor.buffer.lines[3][2] == "d"
        assert h.point()[0] == 3
        assert h.editor.buffer.modified

    def test_create_directory_elsewhere_adds_no_line(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("+")
        submit_minibuffer(h, "/home/elsewhere", clear=True)
        assert provider.tree["home"]["elsewhere"] == {}
        assert "elsewhere" not in h.editor.buffer.text

    def test_create_directory_collision_messages(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("+")
        submit_minibuffer(h, "sub")
        assert "already exists" in h.message_line()

    def test_rename_in_place(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("n", "R")  # beta.py
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Rename beta.py to: "
        assert h.editor.minibuffer.text == "/home/user/"
        submit_minibuffer(h, "mid.txt")
        user = provider.tree["home"]["user"]
        assert "beta.py" not in user and user["mid.txt"] == "print('beta')\n"
        # Probe: line replaced in place, point on it, "Move: 1 file done".
        assert h.editor.buffer.lines[4].endswith(" mid.txt")
        assert "beta.py" not in h.editor.buffer.text
        assert h.point() == (4, NAME_COL)
        assert h.message_line().startswith("Move: 1 file done")

    def test_rename_into_directory_removes_line(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("n", "R")  # beta.py
        submit_minibuffer(h, "sub")
        assert provider.tree["home"]["user"]["sub"]["beta.py"] == "print('beta')\n"
        assert "beta.py" not in h.editor.buffer.text

    def test_rename_keeps_mark(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("d", "p", "R")  # flag alpha.txt, return to it, rename
        submit_minibuffer(h, "omega.txt")
        line = next(ln for ln in h.editor.buffer.lines if ln.endswith(" omega.txt"))
        assert line.startswith("D ")

    def test_copy_file_marks_new_line(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("C")  # alpha.txt
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Copy alpha.txt to: "
        submit_minibuffer(h, "copy1.txt")
        user = provider.tree["home"]["user"]
        assert user["copy1.txt"] == "alpha line\n" and "alpha.txt" in user
        # Probe: new line inserted at point's line, marked C, point on it.
        assert h.editor.buffer.lines[3].startswith("C ")
        assert h.editor.buffer.lines[3].endswith(" copy1.txt")
        assert h.editor.buffer.lines[4].endswith(" alpha.txt")
        assert h.point() == (3, NAME_COL)
        assert h.message_line().startswith("Copy: 1 file done")

    def test_copy_directory_asks_recursive(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("n", "n", "C")  # sub
        submit_minibuffer(h, "sub2")
        assert h.editor.minibuffer is not None
        assert (
            h.editor.minibuffer.prompt
            == "Copy /home/user/sub recursively? (yes or no) "
        )
        submit_minibuffer(h, "yes")
        assert provider.tree["home"]["user"]["sub2"] == {"gamma.txt": "gamma\n"}

    def test_copy_directory_declined(self) -> None:
        h, provider = make_dired_harness()
        h.send_keys("n", "n", "C")
        submit_minibuffer(h, "sub2")
        submit_minibuffer(h, "no")
        assert "sub2" not in provider.tree["home"]["user"]

    def test_rename_collision_messages(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("R")  # alpha.txt
        submit_minibuffer(h, "beta.py")
        assert "already exists" in h.message_line()

    def test_transfer_on_header_line_messages(self) -> None:
        h, _ = make_dired_harness()
        h.send_keys("M-<", "R")
        assert h.message_line().startswith("No file on this line")


# ═══════════════════════════════════════════════════════════════════════
# Entry points
# ═══════════════════════════════════════════════════════════════════════


class TestDiredEntryPoints:
    def test_cx_d_prompt(self) -> None:
        h, _ = make_dired_harness(open_listing=False)
        h.send_keys("C-x", "d")
        assert h.editor.minibuffer is not None
        assert h.editor.minibuffer.prompt == "Dired (directory): "
        assert h.editor.minibuffer.text == "/home/user/"

    def test_find_file_on_directory_opens_dired(self) -> None:
        h, _ = make_dired_harness(open_listing=False)
        h.send_keys("C-x", "C-f")
        submit_minibuffer(h, "sub")  # prompt pre-filled with /home/user/
        assert h.editor.buffer.name == "sub"
        assert getattr(h.editor.buffer, "_dired_state", None) is not None

    def test_unavailable_without_provider(self) -> None:
        h = make_harness("x", width=80, height=24)
        h.send_keys("C-x", "d")
        assert h.editor.minibuffer is not None
        submit_minibuffer(h, "/anything")
        assert h.message_line().startswith("Dired not available in this context")

    def test_dired_on_file_path_messages(self) -> None:
        h, _ = make_dired_harness(open_listing=False)
        h.send_keys("C-x", "d")
        submit_minibuffer(h, "alpha.txt")
        assert "Not a directory" in h.message_line()

    def test_dired_on_missing_path_messages(self) -> None:
        h, _ = make_dired_harness(open_listing=False)
        h.send_keys("C-x", "d")
        submit_minibuffer(h, "nope")
        assert "No such file or directory" in h.message_line()

    def test_names_with_spaces_round_trip(self) -> None:
        h, _ = make_dired_harness({"home": {"user": {"my file.txt": "spacey\n"}}})
        assert h.editor.buffer.lines[3].endswith(" my file.txt")
        h.send_keys("Enter")
        assert h.editor.buffer.name == "my file.txt"
        assert h.editor.buffer.text == "spacey\n"
