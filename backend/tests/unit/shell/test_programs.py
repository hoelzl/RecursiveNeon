"""Tests for shell programs (filesystem and utility)."""

import pytest

from recursive_neon.shell.programs.filesystem import (
    prog_cat,
    prog_cp,
    prog_ls,
    prog_mkdir,
    prog_mv,
    prog_pwd,
    prog_rm,
    prog_touch,
)
from recursive_neon.shell.programs.utility import (
    _expand_vars,
    prog_echo,
    prog_env,
    prog_hostname,
    prog_whoami,
)


@pytest.mark.unit
class TestPwd:
    async def test_pwd_at_root(self, make_ctx, output):
        ctx = make_ctx(["pwd"])
        result = await prog_pwd(ctx)
        assert result == 0
        assert output.text.strip() == "/"

    async def test_pwd_in_subdirectory(self, make_ctx, test_container, output):
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        docs = resolve_path("/Documents", root_id, test_container.app_service)
        ctx = make_ctx(["pwd"], cwd_id=docs.id)
        result = await prog_pwd(ctx)
        assert result == 0
        assert output.text.strip() == "/Documents"


@pytest.mark.unit
class TestLs:
    async def test_ls_root(self, make_ctx, output):
        ctx = make_ctx(["ls"])
        result = await prog_ls(ctx)
        assert result == 0
        text = output.text
        assert "Documents" in text
        assert "welcome.txt" in text

    async def test_ls_specific_directory(self, make_ctx, output):
        ctx = make_ctx(["ls", "/Documents"])
        result = await prog_ls(ctx)
        assert result == 0
        assert "readme.txt" in output.text

    async def test_ls_long_format(self, make_ctx, output):
        ctx = make_ctx(["ls", "-l"])
        result = await prog_ls(ctx)
        assert result == 0
        # Long format should have type indicators
        assert "drw" in output.text or "Documents" in output.text

    async def test_ls_nonexistent(self, make_ctx, output):
        ctx = make_ctx(["ls", "/nonexistent"])
        result = await prog_ls(ctx)
        assert result == 1
        assert "No such file or directory" in output.error_text

    async def test_ls_file(self, make_ctx, output):
        ctx = make_ctx(["ls", "/welcome.txt"])
        result = await prog_ls(ctx)
        assert result == 0
        assert "welcome.txt" in output.text


@pytest.mark.unit
class TestCat:
    async def test_cat_file(self, make_ctx, output):
        ctx = make_ctx(["cat", "/welcome.txt"])
        result = await prog_cat(ctx)
        assert result == 0
        assert len(output.text) > 0

    async def test_cat_missing_operand(self, make_ctx, output):
        ctx = make_ctx(["cat"])
        result = await prog_cat(ctx)
        assert result == 1
        assert "missing file operand" in output.error_text

    async def test_cat_nonexistent(self, make_ctx, output):
        ctx = make_ctx(["cat", "/nonexistent.txt"])
        result = await prog_cat(ctx)
        assert result == 1
        assert "No such file or directory" in output.error_text

    async def test_cat_directory(self, make_ctx, output):
        ctx = make_ctx(["cat", "/Documents"])
        result = await prog_cat(ctx)
        assert result == 1
        assert "Is a directory" in output.error_text

    async def test_cat_multiple_files(self, make_ctx, output):
        ctx = make_ctx(["cat", "/Documents/readme.txt", "/Documents/sample.txt"])
        result = await prog_cat(ctx)
        assert result == 0
        assert len(output.text) > 0


@pytest.mark.unit
class TestMkdir:
    async def test_mkdir_creates_directory(self, make_ctx, output, test_container):
        ctx = make_ctx(["mkdir", "/newdir"])
        result = await prog_mkdir(ctx)
        assert result == 0
        # Verify it exists
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/newdir", root_id, test_container.app_service)
        assert node.type == "directory"

    async def test_mkdir_parents(self, make_ctx, output, test_container):
        ctx = make_ctx(["mkdir", "-p", "/a/b/c"])
        result = await prog_mkdir(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/a/b/c", root_id, test_container.app_service)
        assert node.type == "directory"

    async def test_mkdir_missing_operand(self, make_ctx, output):
        ctx = make_ctx(["mkdir"])
        result = await prog_mkdir(ctx)
        assert result == 1
        assert "missing operand" in output.error_text

    async def test_mkdir_already_exists(self, make_ctx, output):
        ctx = make_ctx(["mkdir", "/Documents"])
        result = await prog_mkdir(ctx)
        assert result == 1
        assert "File exists" in output.error_text


@pytest.mark.unit
class TestTouch:
    async def test_touch_creates_file(self, make_ctx, output, test_container):
        ctx = make_ctx(["touch", "/newfile.txt"])
        result = await prog_touch(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/newfile.txt", root_id, test_container.app_service)
        assert node.type == "file"
        assert node.content == ""

    async def test_touch_existing_file(self, make_ctx, output):
        ctx = make_ctx(["touch", "/welcome.txt"])
        result = await prog_touch(ctx)
        assert result == 0

    async def test_touch_missing_operand(self, make_ctx, output):
        ctx = make_ctx(["touch"])
        result = await prog_touch(ctx)
        assert result == 1
        assert "missing file operand" in output.error_text


@pytest.mark.unit
class TestRm:
    async def test_rm_file(self, make_ctx, output, test_container):
        # Create a file to remove
        ctx = make_ctx(["touch", "/to_delete.txt"])
        await prog_touch(ctx)
        # Remove it
        ctx = make_ctx(["rm", "/to_delete.txt"])
        result = await prog_rm(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        with pytest.raises(FileNotFoundError):
            resolve_path("/to_delete.txt", root_id, test_container.app_service)

    async def test_rm_directory_without_r(self, make_ctx, output):
        ctx = make_ctx(["rm", "/Documents"])
        result = await prog_rm(ctx)
        assert result == 1
        assert "Is a directory" in output.error_text

    async def test_rm_directory_with_r(self, make_ctx, output, test_container):
        # Create a test directory to remove
        make_ctx_fn = make_ctx  # avoid name collision
        ctx = make_ctx_fn(["mkdir", "/to_delete"])
        await prog_mkdir(ctx)
        ctx = make_ctx_fn(["rm", "-r", "/to_delete"])
        result = await prog_rm(ctx)
        assert result == 0

    async def test_rm_root_denied(self, make_ctx, output):
        ctx = make_ctx(["rm", "-r", "/"])
        result = await prog_rm(ctx)
        assert result == 1
        assert "cannot remove root" in output.error_text

    async def test_rm_nonexistent(self, make_ctx, output):
        ctx = make_ctx(["rm", "/nonexistent"])
        result = await prog_rm(ctx)
        assert result == 1

    async def test_rm_missing_operand(self, make_ctx, output):
        ctx = make_ctx(["rm"])
        result = await prog_rm(ctx)
        assert result == 1
        assert "missing operand" in output.error_text


@pytest.mark.unit
class TestCp:
    async def test_cp_file(self, make_ctx, output, test_container):
        ctx = make_ctx(["cp", "/welcome.txt", "/welcome_copy.txt"])
        result = await prog_cp(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/welcome_copy.txt", root_id, test_container.app_service)
        assert node.type == "file"

    async def test_cp_into_directory(self, make_ctx, output, test_container):
        ctx = make_ctx(["cp", "/welcome.txt", "/Documents"])
        result = await prog_cp(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path(
            "/Documents/welcome.txt", root_id, test_container.app_service
        )
        assert node.type == "file"

    async def test_cp_missing_operand(self, make_ctx, output):
        ctx = make_ctx(["cp", "/welcome.txt"])
        result = await prog_cp(ctx)
        assert result == 1
        assert "missing operand" in output.error_text


@pytest.mark.unit
class TestMv:
    async def test_mv_rename(self, make_ctx, output, test_container):
        # Create a file to move
        ctx = make_ctx(["touch", "/moveme.txt"])
        await prog_touch(ctx)
        ctx = make_ctx(["mv", "/moveme.txt", "/moved.txt"])
        result = await prog_mv(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path("/moved.txt", root_id, test_container.app_service)
        assert node.type == "file"

    async def test_mv_into_directory(self, make_ctx, output, test_container):
        ctx = make_ctx(["touch", "/moveme2.txt"])
        await prog_touch(ctx)
        ctx = make_ctx(["mv", "/moveme2.txt", "/Documents"])
        result = await prog_mv(ctx)
        assert result == 0
        from recursive_neon.shell.path_resolver import resolve_path

        root_id = test_container.game_state.filesystem.root_id
        node = resolve_path(
            "/Documents/moveme2.txt", root_id, test_container.app_service
        )
        assert node.type == "file"

    async def test_mv_root_denied(self, make_ctx, output):
        ctx = make_ctx(["mv", "/", "/somewhere"])
        result = await prog_mv(ctx)
        assert result == 1
        assert "cannot move root" in output.error_text


@pytest.mark.unit
class TestEcho:
    async def test_echo_simple(self, make_ctx, output):
        ctx = make_ctx(["echo", "hello", "world"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "hello world"

    async def test_echo_variable_expansion(self, make_ctx, output):
        ctx = make_ctx(["echo", "$USER"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "test"

    async def test_echo_no_args(self, make_ctx, output):
        ctx = make_ctx(["echo"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == ""

    async def test_echo_inline_variable_expansion(self, make_ctx, output):
        ctx = make_ctx(["echo", "Hello$USER"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "Hellotest"

    async def test_echo_multiple_vars_in_one_arg(self, make_ctx, output):
        ctx = make_ctx(["echo", "$USER@$HOSTNAME"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "test@test-host"

    async def test_echo_undefined_var_preserved(self, make_ctx, output):
        ctx = make_ctx(["echo", "$UNDEFINED"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "$UNDEFINED"


@pytest.mark.unit
class TestEnv:
    async def test_env_lists_variables(self, make_ctx, output):
        ctx = make_ctx(["env"])
        result = await prog_env(ctx)
        assert result == 0
        assert "USER=test" in output.text
        assert "HOSTNAME=test-host" in output.text


@pytest.mark.unit
class TestWhoami:
    async def test_whoami(self, make_ctx, output):
        ctx = make_ctx(["whoami"])
        result = await prog_whoami(ctx)
        assert result == 0
        assert output.text.strip() == "test"


@pytest.mark.unit
class TestHostname:
    async def test_hostname(self, make_ctx, output):
        ctx = make_ctx(["hostname"])
        result = await prog_hostname(ctx)
        assert result == 0
        assert output.text.strip() == "test-host"


@pytest.mark.unit
class TestExpandVarsBrace:
    """Tests for ${VAR} syntax in _expand_vars (fix #12)."""

    def test_brace_syntax(self):
        assert _expand_vars("${HOME}/foo", {"HOME": "/root"}) == "/root/foo"

    def test_mixed_syntax(self):
        result = _expand_vars("$USER at ${HOME}", {"USER": "neo", "HOME": "/root"})
        assert result == "neo at /root"

    def test_unset_brace_preserved(self):
        assert _expand_vars("${UNDEFINED}", {}) == "${UNDEFINED}"

    def test_brace_and_dollar_same_var(self):
        env = {"X": "val"}
        assert _expand_vars("$X ${X}", env) == "val val"

    def test_empty_env(self):
        assert _expand_vars("${A} $B", {}) == "${A} $B"


@pytest.mark.unit
class TestEchoBraceExpansion:
    """Integration test for echo with ${VAR} syntax."""

    async def test_echo_brace_var(self, make_ctx, output):
        ctx = make_ctx(["echo", "${USER}"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "test"

    async def test_echo_mixed_vars(self, make_ctx, output):
        ctx = make_ctx(["echo", "${USER}@$HOSTNAME"])
        result = await prog_echo(ctx)
        assert result == 0
        assert output.text.strip() == "test@test-host"


@pytest.mark.unit
class TestTouchErrors:
    """Tests for error paths in prog_touch (fix #16)."""

    async def test_touch_not_a_directory_parent(self, make_ctx, test_container, output):
        """touch existingfile/newfile should fail with NotADirectoryError."""
        root_id = test_container.game_state.filesystem.root_id
        test_container.app_service.create_file(
            {"name": "existingfile", "parent_id": root_id, "content": ""}
        )
        ctx = make_ctx(["touch", "existingfile/newfile"])
        result = await prog_touch(ctx)
        assert result == 1
        assert output.error_text


@pytest.mark.unit
class TestMkdirErrors:
    """Tests for error paths in prog_mkdir (fix #16)."""

    async def test_mkdir_p_non_directory_segment(
        self, make_ctx, test_container, output
    ):
        """mkdir -p existingfile/subdir should fail when segment is a file."""
        root_id = test_container.game_state.filesystem.root_id
        test_container.app_service.create_file(
            {"name": "blocker", "parent_id": root_id, "content": ""}
        )
        ctx = make_ctx(["mkdir", "-p", "blocker/subdir"])
        result = await prog_mkdir(ctx)
        assert result == 1
        assert output.error_text
