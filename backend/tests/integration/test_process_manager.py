"""
Integration tests for OllamaProcessManager

Tests the ProcessManager's process lifecycle management.
Uses mocking to avoid actually starting ollama processes during tests.
"""

import pytest
import asyncio
import subprocess
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import psutil

from recursive_neon.services.process_manager import OllamaProcessManager


@pytest.mark.integration
class TestProcessManagerInitialization:
    """Test process manager initialization."""

    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        manager = OllamaProcessManager()

        assert manager.host == "127.0.0.1"
        assert manager.port == 11434
        assert manager.process is None
        assert manager._monitor_task is None

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        manager = OllamaProcessManager(
            binary_path="/custom/path",
            host="192.168.1.100",
            port=8080
        )

        assert manager.host == "192.168.1.100"
        assert manager.port == 8080
        assert manager.binary_path == Path("/custom/path")

    def test_base_url_construction(self):
        """Test that base URL is constructed correctly from host and port."""
        manager = OllamaProcessManager(host="localhost", port=12345)

        # Check internal state (implementation detail)
        assert manager.host == "localhost"
        assert manager.port == 12345


@pytest.mark.integration
class TestProcessManagerBinaryLocation:
    """Test binary location logic."""

    def test_get_ollama_binary_not_found(self):
        """Test error when ollama binary is not found."""
        manager = OllamaProcessManager(binary_path="/nonexistent/path")

        with patch('shutil.which', return_value=None):
            with pytest.raises(FileNotFoundError, match="Ollama binary not found"):
                manager._get_ollama_binary()

    def test_get_ollama_binary_from_system_path(self):
        """Test finding ollama in system PATH when not in binary_path."""
        manager = OllamaProcessManager(binary_path="/nonexistent/path")

        with patch('shutil.which', return_value='/usr/local/bin/ollama'):
            binary = manager._get_ollama_binary()
            assert binary == Path('/usr/local/bin/ollama')

    @patch('platform.system')
    def test_get_ollama_binary_windows(self, mock_system):
        """Test binary path construction on Windows."""
        mock_system.return_value = "Windows"
        manager = OllamaProcessManager(binary_path="./services/ollama")

        # Mock the binary exists check
        with patch.object(Path, 'exists', return_value=True):
            binary = manager._get_ollama_binary()
            assert binary.name == "ollama.exe"

    @patch('platform.system')
    def test_get_ollama_binary_linux(self, mock_system):
        """Test binary path construction on Linux."""
        mock_system.return_value = "Linux"
        manager = OllamaProcessManager(binary_path="./services/ollama")

        with patch.object(Path, 'exists', return_value=True):
            binary = manager._get_ollama_binary()
            assert binary.name == "ollama"


@pytest.mark.integration
class TestProcessManagerStartStop:
    """Test process start and stop operations."""

    @pytest.mark.asyncio
    async def test_start_process_success(self):
        """Test successful process start."""
        manager = OllamaProcessManager()

        # Mock the binary exists
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running

        with patch.object(manager, '_get_ollama_binary', return_value=Path('/fake/ollama')):
            with patch('subprocess.Popen', return_value=mock_process):
                with patch('asyncio.create_task', return_value=Mock()) as mock_create_task:
                    success = await manager.start()

                    assert success is True
                    assert manager.process == mock_process
                    # Should create monitoring task
                    mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting when process is already running."""
        manager = OllamaProcessManager()

        # Mock is_running to return True
        with patch.object(manager, 'is_running', return_value=True):
            success = await manager.start()

            assert success is True
            # Should not create a new process

    @pytest.mark.asyncio
    async def test_start_process_failure(self):
        """Test handling of process start failure."""
        manager = OllamaProcessManager()

        with patch.object(manager, '_get_ollama_binary', side_effect=FileNotFoundError("Binary not found")):
            success = await manager.start()

            assert success is False
            assert manager.process is None

    @pytest.mark.asyncio
    async def test_stop_process_graceful(self):
        """Test graceful process shutdown."""
        manager = OllamaProcessManager()

        # Create a mock process
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate = Mock()
        mock_process.wait = Mock()

        manager.process = mock_process

        # Mock the monitoring task (must be async-compatible)
        mock_task = AsyncMock()
        mock_task.cancel = Mock()
        manager._monitor_task = mock_task

        with patch.object(manager, 'is_running', side_effect=[True, False]):
            success = await manager.stop(timeout=5)

            assert success is True
            mock_process.terminate.assert_called_once()
            mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_process_force_kill(self):
        """Test force kill when graceful shutdown times out."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate = Mock()
        mock_process.kill = Mock()
        mock_process.wait = Mock(side_effect=[subprocess.TimeoutExpired("cmd", 5), None])

        manager.process = mock_process
        manager._monitor_task = None

        with patch.object(manager, 'is_running', side_effect=[True, False]):
            success = await manager.stop(timeout=1)

            assert success is True
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        """Test stop when process is not running."""
        manager = OllamaProcessManager()

        with patch.object(manager, 'is_running', return_value=False):
            success = await manager.stop()

            assert success is True


@pytest.mark.integration
class TestProcessManagerStatus:
    """Test process status checking."""

    def test_is_running_no_process(self):
        """Test is_running when no process exists."""
        manager = OllamaProcessManager()
        assert manager.is_running() is False

    def test_is_running_process_ended(self):
        """Test is_running when process has ended."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = 0  # Process has ended

        manager.process = mock_process

        assert manager.is_running() is False

    def test_is_running_process_active(self):
        """Test is_running when process is active."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Still running

        # Mock psutil Process
        mock_psutil_process = Mock()
        mock_psutil_process.is_running.return_value = True
        mock_psutil_process.status.return_value = psutil.STATUS_RUNNING

        manager.process = mock_process

        with patch('psutil.Process', return_value=mock_psutil_process):
            assert manager.is_running() is True

    def test_is_running_zombie_process(self):
        """Test is_running with zombie process."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        mock_psutil_process = Mock()
        mock_psutil_process.is_running.return_value = True
        mock_psutil_process.status.return_value = psutil.STATUS_ZOMBIE

        manager.process = mock_process

        with patch('psutil.Process', return_value=mock_psutil_process):
            assert manager.is_running() is False

    def test_is_running_no_such_process(self):
        """Test is_running when psutil can't find process."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        manager.process = mock_process

        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(12345)):
            assert manager.is_running() is False

    def test_get_status_not_running(self):
        """Test get_status when process is not running."""
        manager = OllamaProcessManager()

        with patch.object(manager, 'is_running', return_value=False):
            status = manager.get_status()

            assert status["running"] is False
            assert status["pid"] is None
            assert status["memory_mb"] == 0
            assert status["cpu_percent"] == 0

    def test_get_status_running(self):
        """Test get_status when process is running."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345

        # Mock psutil Process with memory and CPU info
        mock_psutil_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 100  # 100 MB in bytes
        mock_psutil_process.memory_info.return_value = mock_memory_info
        mock_psutil_process.cpu_percent.return_value = 25.5

        manager.process = mock_process

        with patch.object(manager, 'is_running', return_value=True):
            with patch('psutil.Process', return_value=mock_psutil_process):
                status = manager.get_status()

                assert status["running"] is True
                assert status["pid"] == 12345
                assert status["memory_mb"] == 100.0
                assert status["cpu_percent"] == 25.5

    def test_get_status_error_accessing_process(self):
        """Test get_status when error occurs accessing process info."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        manager.process = mock_process

        with patch.object(manager, 'is_running', return_value=True):
            with patch('psutil.Process', side_effect=psutil.AccessDenied(12345)):
                status = manager.get_status()

                assert status["running"] is False
                assert status["pid"] is None


@pytest.mark.integration
class TestProcessManagerMonitoring:
    """Test process monitoring functionality."""

    @pytest.mark.asyncio
    async def test_monitor_process_reads_output(self):
        """Test that monitor reads process output."""
        manager = OllamaProcessManager()

        # Create a mock process with stderr
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, None, 0]  # Running, running, then ended

        # Mock stderr with some output
        mock_stderr = Mock()
        mock_stderr.readline.side_effect = [
            b"Ollama starting...\n",
            b"Listening on :11434\n",
            b""  # End of output
        ]
        mock_process.stderr = mock_stderr
        mock_process.returncode = 0

        manager.process = mock_process

        # Run monitor for a short time
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await manager._monitor_process()

            # Should have read from stderr
            assert mock_stderr.readline.called

    @pytest.mark.asyncio
    async def test_monitor_process_handles_no_process(self):
        """Test monitor handles case when process is None."""
        manager = OllamaProcessManager()
        manager.process = None

        # Should return early without error
        await manager._monitor_process()

    @pytest.mark.asyncio
    async def test_monitor_process_handles_exception(self):
        """Test monitor handles exceptions during monitoring."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.side_effect = Exception("Unexpected error")

        manager.process = mock_process

        # Should handle exception gracefully
        await manager._monitor_process()


@pytest.mark.integration
class TestProcessManagerLifecycle:
    """Test complete lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_start_stop_cycle(self):
        """Test complete start-stop cycle."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_process.terminate = Mock()
        mock_process.wait = Mock()

        with patch.object(manager, '_get_ollama_binary', return_value=Path('/fake/ollama')):
            with patch('subprocess.Popen', return_value=mock_process):
                with patch('asyncio.create_task', return_value=AsyncMock()):
                    # Start
                    start_success = await manager.start()
                    assert start_success is True
                    assert manager.process is not None

                    # Stop
                    mock_task = AsyncMock()
                    mock_task.cancel = Mock()
                    manager._monitor_task = mock_task

                    with patch.object(manager, 'is_running', side_effect=[True, False]):
                        stop_success = await manager.stop()
                        assert stop_success is True

    @pytest.mark.asyncio
    async def test_multiple_start_attempts(self):
        """Test that multiple start attempts don't create multiple processes."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345

        with patch.object(manager, '_get_ollama_binary', return_value=Path('/fake/ollama')):
            with patch('subprocess.Popen', return_value=mock_process):
                with patch('asyncio.create_task', return_value=Mock()):
                    # First start
                    await manager.start()

                    # Simulate process running
                    with patch.object(manager, 'is_running', return_value=True):
                        # Second start should return immediately
                        success = await manager.start()
                        assert success is True

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test stop without starting process."""
        manager = OllamaProcessManager()

        # Should handle gracefully
        success = await manager.stop()
        assert success is True


@pytest.mark.integration
class TestProcessManagerEnvironmentConfiguration:
    """Test environment variable configuration."""

    @pytest.mark.asyncio
    async def test_environment_variables_set(self):
        """Test that OLLAMA_HOST environment variable is set correctly."""
        manager = OllamaProcessManager(host="192.168.1.100", port=8888)

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345

        with patch.object(manager, '_get_ollama_binary', return_value=Path('/fake/ollama')):
            with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
                with patch('asyncio.create_task', return_value=AsyncMock()):
                    await manager.start()

                    # Check that Popen was called with correct environment
                    call_kwargs = mock_popen.call_args.kwargs
                    assert 'env' in call_kwargs
                    env = call_kwargs['env']
                    assert env['OLLAMA_HOST'] == "192.168.1.100:8888"

    @pytest.mark.asyncio
    @patch('platform.system')
    async def test_windows_creation_flags(self, mock_system):
        """Test that Windows-specific creation flags are used."""
        mock_system.return_value = "Windows"
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345

        with patch.object(manager, '_get_ollama_binary', return_value=Path('/fake/ollama')):
            with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
                with patch('asyncio.create_task', return_value=AsyncMock()):
                    await manager.start()

                    # Check that creation flags were set
                    call_kwargs = mock_popen.call_args.kwargs
                    assert 'creationflags' in call_kwargs
                    assert call_kwargs['creationflags'] == subprocess.CREATE_NO_WINDOW


@pytest.mark.integration
class TestProcessManagerErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_start_subprocess_error(self):
        """Test handling of subprocess creation error."""
        manager = OllamaProcessManager()

        with patch.object(manager, '_get_ollama_binary', return_value=Path('/fake/ollama')):
            with patch('subprocess.Popen', side_effect=OSError("Permission denied")):
                success = await manager.start()

                assert success is False
                assert manager.process is None

    @pytest.mark.asyncio
    async def test_stop_error_during_terminate(self):
        """Test handling of error during process termination."""
        manager = OllamaProcessManager()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.pid = 12345
        mock_process.terminate.side_effect = Exception("Termination error")

        manager.process = mock_process
        manager._monitor_task = None

        with patch.object(manager, 'is_running', return_value=True):
            success = await manager.stop()

            # Should handle error and return False
            assert success is False
