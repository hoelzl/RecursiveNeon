import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TerminalApp } from '../TerminalApp';
import { WebSocketProvider } from '../../../contexts/WebSocketContext';
import type { TerminalSession } from '../../../terminal/core/TerminalSession';
import type { CommandRegistry } from '../../../terminal/core/CommandRegistry';
import type { CompletionEngine } from '../../../terminal/core/CompletionEngine';
import type { ArgumentParser } from '../../../terminal/core/ArgumentParser';

// Mock terminal modules
vi.mock('../../../terminal/core/TerminalSession', () => ({
  TerminalSession: vi.fn(),
}));
vi.mock('../../../terminal/core/CommandRegistry', () => ({
  CommandRegistry: vi.fn(),
}));
vi.mock('../../../terminal/core/CompletionEngine', () => ({
  CompletionEngine: vi.fn(),
}));
vi.mock('../../../terminal/core/ArgumentParser', () => ({
  ArgumentParser: vi.fn(),
}));

// Mock WebSocket client
const mockWebSocketClient = {
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  sendMessage: vi.fn(),
  readyState: 1,
} as any;

// Helper to render with WebSocket context
const renderTerminalApp = (props = {}) => {
  return render(
    <WebSocketProvider client={mockWebSocketClient}>
      <TerminalApp {...props} />
    </WebSocketProvider>
  );
};

describe('TerminalApp', () => {
  let mockSession: any;
  let mockRegistry: any;
  let mockCompletionEngine: any;
  let mockArgParser: any;
  let outputChangeCallback: (() => void) | null = null;

  beforeEach(() => {
    // Mock TerminalSession
    mockSession = {
      init: vi.fn().mockResolvedValue(undefined),
      writeLine: vi.fn(),
      writeError: vi.fn(),
      getPrompt: vi.fn().mockReturnValue('user@neon:~$ '),
      addToHistory: vi.fn(),
      navigateHistory: vi.fn().mockReturnValue(null),
      isWaitingForReadLine: vi.fn().mockReturnValue(false),
      getReadLinePrompt: vi.fn().mockReturnValue('> '),
      resolveReadLine: vi.fn(),
      getCurrentApp: vi.fn().mockReturnValue(null),
      handleKeyPress: vi.fn().mockResolvedValue(true),
      outputBuffer: [],
      onOutputChange: vi.fn((callback) => {
        outputChangeCallback = callback;
        return () => {
          outputChangeCallback = null;
        };
      }),
    };

    // Mock CommandRegistry
    mockRegistry = {
      registerAll: vi.fn(),
      execute: vi.fn().mockResolvedValue(0),
    };

    // Mock CompletionEngine
    mockCompletionEngine = {
      complete: vi.fn().mockResolvedValue({
        prefix: '',
        commonPrefix: '',
        completions: [],
        replaceStart: 0,
        replaceEnd: 0,
      }),
    };

    // Mock ArgumentParser
    mockArgParser = {
      parseCommandLine: vi.fn((cmd: string) => ({
        command: cmd.split(' ')[0],
        args: cmd.split(' ').slice(1),
      })),
    };

    // Setup mocks using vi.mocked
    const { TerminalSession: MockTerminalSession } = await import('../../../terminal/core/TerminalSession');
    const { CommandRegistry: MockCommandRegistry } = await import('../../../terminal/core/CommandRegistry');
    const { CompletionEngine: MockCompletionEngine } = await import('../../../terminal/core/CompletionEngine');
    const { ArgumentParser: MockArgumentParser } = await import('../../../terminal/core/ArgumentParser');

    vi.mocked(MockTerminalSession).mockImplementation(() => mockSession as any);
    vi.mocked(MockCommandRegistry).mockImplementation(() => mockRegistry as any);
    vi.mocked(MockCompletionEngine).mockImplementation(() => mockCompletionEngine as any);
    vi.mocked(MockArgumentParser).mockImplementation(() => mockArgParser as any);

    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    it('should initialize terminal session', async () => {
      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });
    });

    it('should display welcome message', async () => {
      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.writeLine).toHaveBeenCalledWith(
          expect.stringContaining('Welcome to RecursiveNeon Terminal'),
          expect.any(Object)
        );
      });
    });

    it('should display help hint', async () => {
      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.writeLine).toHaveBeenCalledWith(
          expect.stringContaining('help')
        );
      });
    });

    it('should handle initialization errors', async () => {
      mockSession.init.mockRejectedValueOnce(new Error('Init failed'));

      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.writeError).toHaveBeenCalledWith(
          expect.stringContaining('Failed to initialize')
        );
      });

      consoleError.mockRestore();
    });

    it('should register builtin commands', async () => {
      renderTerminalApp();

      await waitFor(() => {
        expect(mockRegistry.registerAll).toHaveBeenCalled();
      });
    });

    it('should register custom commands if provided', async () => {
      const customCommands = [
        {
          name: 'custom',
          description: 'Custom command',
          usage: 'custom',
          execute: vi.fn(),
        },
      ];

      renderTerminalApp({ customCommands });

      await waitFor(() => {
        expect(mockRegistry.registerAll).toHaveBeenCalledWith(customCommands);
      });
    });

    it('should set initial directory if provided', async () => {
      renderTerminalApp({ initialDirectory: '/home/user' });

      await waitFor(() => {
        expect(TerminalSession).toHaveBeenCalledWith(
          expect.any(Object),
          '/home/user'
        );
      });
    });
  });

  describe('Command Execution', () => {
    it('should execute command when submitted', async () => {
      const user = userEvent.setup();

      // Set up output buffer with welcome message
      mockSession.outputBuffer = [
        { text: 'Welcome to RecursiveNeon Terminal v1.0', style: {} },
      ];

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      // Find input field
      const input = screen.getByRole('textbox');

      // Type and submit command
      await user.type(input, 'ls{Enter}');

      await waitFor(() => {
        expect(mockRegistry.execute).toHaveBeenCalledWith(
          'ls',
          expect.any(Object)
        );
      });
    });

    it('should add command to history', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, 'pwd{Enter}');

      await waitFor(() => {
        expect(mockSession.addToHistory).toHaveBeenCalledWith('pwd');
      });
    });

    it('should echo command with prompt', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, 'echo test{Enter}');

      await waitFor(() => {
        expect(mockSession.writeLine).toHaveBeenCalledWith(
          expect.stringContaining('user@neon:~$ echo test'),
          expect.any(Object)
        );
      });
    });

    it('should handle empty command', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, '{Enter}');

      // Should write empty line but not execute
      await waitFor(() => {
        expect(mockSession.writeLine).toHaveBeenCalledWith('');
        expect(mockRegistry.execute).not.toHaveBeenCalled();
      });
    });

    it('should handle command execution errors', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      mockRegistry.execute.mockRejectedValueOnce(new Error('Command failed'));

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, 'badcommand{Enter}');

      await waitFor(() => {
        expect(mockSession.writeError).toHaveBeenCalledWith(
          expect.stringContaining('badcommand')
        );
      });
    });
  });

  describe('History Navigation', () => {
    it('should navigate history on arrow up', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      mockSession.navigateHistory.mockReturnValueOnce('previous command');

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, '{ArrowUp}');

      await waitFor(() => {
        expect(mockSession.navigateHistory).toHaveBeenCalledWith('up');
      });
    });

    it('should navigate history on arrow down', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      mockSession.navigateHistory.mockReturnValueOnce('next command');

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, '{ArrowDown}');

      await waitFor(() => {
        expect(mockSession.navigateHistory).toHaveBeenCalledWith('down');
      });
    });
  });

  describe('Tab Completion', () => {
    it('should handle tab completion with single match', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      mockCompletionEngine.complete.mockResolvedValueOnce({
        prefix: 'ls',
        commonPrefix: 'ls',
        completions: ['ls'],
        replaceStart: 0,
        replaceEnd: 2,
      });

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox') as HTMLInputElement;
      await user.type(input, 'ls');
      await user.keyboard('{Tab}');

      await waitFor(() => {
        expect(mockCompletionEngine.complete).toHaveBeenCalled();
      });
    });

    it('should handle tab completion with multiple matches', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      mockCompletionEngine.complete.mockResolvedValueOnce({
        prefix: 'l',
        commonPrefix: 'ls',
        completions: ['ls', 'ln', 'lsof'],
        replaceStart: 0,
        replaceEnd: 1,
      });

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, 'l');
      await user.keyboard('{Tab}');

      await waitFor(() => {
        expect(mockCompletionEngine.complete).toHaveBeenCalled();
      });
    });

    it('should handle tab completion errors', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Welcome', style: {} },
      ];

      mockCompletionEngine.complete.mockRejectedValueOnce(
        new Error('Completion failed')
      );

      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, 'test');
      await user.keyboard('{Tab}');

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          'Tab completion error:',
          expect.any(Error)
        );
      });

      consoleError.mockRestore();
    });
  });

  describe('Interactive Mode', () => {
    it('should handle readline input in interactive mode', async () => {
      const user = userEvent.setup();

      mockSession.outputBuffer = [
        { text: 'Enter your name:', style: {} },
      ];

      mockSession.isWaitingForReadLine.mockReturnValue(true);
      mockSession.getReadLinePrompt.mockReturnValue('Name: ');

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.init).toHaveBeenCalled();
      });

      const input = screen.getByRole('textbox');
      await user.type(input, 'Alice{Enter}');

      await waitFor(() => {
        expect(mockSession.resolveReadLine).toHaveBeenCalledWith('Alice');
      });
    });

    it('should show readline prompt when waiting for input', async () => {
      mockSession.outputBuffer = [
        { text: 'Enter your name:', style: {} },
      ];

      mockSession.isWaitingForReadLine.mockReturnValue(true);
      mockSession.getReadLinePrompt.mockReturnValue('Name: ');

      renderTerminalApp();

      await waitFor(() => {
        expect(screen.getByText(/Name:/)).toBeInTheDocument();
      });
    });
  });

  describe('Theme Application', () => {
    it('should apply custom theme', async () => {
      const customTheme = {
        background: '#000000',
        foreground: '#00ff00',
        cursor: '#ff0000',
        cursorAccent: '#ffffff',
        selection: '#333333',
        fontFamily: 'Courier New',
        fontSize: 14,
        lineHeight: 1.5,
        opacity: 0.9,
        blur: 2,
        cyan: '#00ffff',
        red: '#ff0000',
        yellow: '#ffff00',
      };

      renderTerminalApp({ theme: customTheme });

      await waitFor(() => {
        const terminalApp = document.querySelector('.terminal-app') as HTMLElement;
        expect(terminalApp).toBeTruthy();

        const styles = terminalApp?.style;
        expect(styles?.getPropertyValue('--terminal-bg')).toBe('#000000');
        expect(styles?.getPropertyValue('--terminal-fg')).toBe('#00ff00');
      });
    });
  });

  describe('Output Updates', () => {
    it('should update output when session buffer changes', async () => {
      mockSession.outputBuffer = [
        { text: 'Initial output', style: {} },
      ];

      renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.onOutputChange).toHaveBeenCalled();
      });

      // Trigger output change
      mockSession.outputBuffer.push({ text: 'New output', style: {} });

      if (outputChangeCallback) {
        outputChangeCallback();
      }

      await waitFor(() => {
        // Component should re-render with new output
        expect(screen.getByText('New output')).toBeInTheDocument();
      });
    });

    it('should cleanup output change subscription on unmount', async () => {
      const unsubscribe = vi.fn();
      mockSession.onOutputChange.mockReturnValue(unsubscribe);

      const { unmount } = renderTerminalApp();

      await waitFor(() => {
        expect(mockSession.onOutputChange).toHaveBeenCalled();
      });

      unmount();

      expect(unsubscribe).toHaveBeenCalled();
    });
  });
});
