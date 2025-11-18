import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TerminalSession } from '../TerminalSession';
import { AppAPI } from '../../../utils/appApi';
import type { TerminalApplication } from '../../types';

// Mock AppAPI
vi.mock('../../../utils/appApi');
vi.mock('../FileSystemAdapter');
vi.mock('../AnsiParser');

describe('TerminalSession', () => {
  let mockApi: any;
  let session: TerminalSession;

  beforeEach(() => {
    mockApi = {
      initFilesystem: vi.fn().mockResolvedValue({
        id: 'root-id',
        name: 'root',
        type: 'directory',
      }),
      listDirectory: vi.fn().mockResolvedValue([]),
    } as any;

    session = new TerminalSession(mockApi, '/');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Initialization', () => {
    it('should create session with unique ID', () => {
      const session1 = new TerminalSession(mockApi);
      const session2 = new TerminalSession(mockApi);

      expect(session1.id).toBeTruthy();
      expect(session2.id).toBeTruthy();
      expect(session1.id).not.toBe(session2.id);
    });

    it('should set initial working directory', () => {
      const session1 = new TerminalSession(mockApi, '/home/user');
      expect(session1.currentPath).toBe('/home/user');
    });

    it('should default to root directory', () => {
      const session1 = new TerminalSession(mockApi);
      expect(session1.currentPath).toBe('/');
    });

    it('should set default environment variables', () => {
      expect(session.getEnv('USER')).toBe('user');
      expect(session.getEnv('HOME')).toBe('/');
      expect(session.getEnv('PATH')).toBe('/bin:/usr/bin');
      expect(session.getEnv('TERM')).toBe('xterm-256color');
    });

    it('should initialize empty output buffer', () => {
      expect(session.outputBuffer).toEqual([]);
    });

    it('should initialize empty command history', () => {
      expect(session.commandHistory).toEqual([]);
    });
  });

  describe('Output Management', () => {
    it('should write line to output buffer', () => {
      session.writeLine('Hello, world!');

      expect(session.outputBuffer.length).toBe(1);
      expect(session.outputBuffer[0].content).toBe('Hello, world!');
      expect(session.outputBuffer[0].type).toBe('output');
    });

    it('should write styled line', () => {
      session.writeLine('Styled text', { color: '#ff0000', bold: true });

      expect(session.outputBuffer.length).toBe(1);
      expect(session.outputBuffer[0].style).toEqual({ color: '#ff0000', bold: true });
    });

    it('should write error line with error style', () => {
      session.writeError('Error message');

      expect(session.outputBuffer.length).toBe(1);
      expect(session.outputBuffer[0].content).toBe('Error message');
      expect(session.outputBuffer[0].style?.color).toContain('error');
    });

    it('should write system line with system style', () => {
      session.writeSystem('System message');

      expect(session.outputBuffer.length).toBe(1);
      expect(session.outputBuffer[0].content).toBe('System message');
      expect(session.outputBuffer[0].style?.color).toContain('system');
    });

    it('should clear screen', () => {
      session.writeLine('Line 1');
      session.writeLine('Line 2');
      session.writeLine('Line 3');

      expect(session.outputBuffer.length).toBe(3);

      session.clearScreen();

      expect(session.outputBuffer.length).toBe(0);
    });

    it('should update last line', () => {
      session.writeLine('Original line');
      session.updateLastLine('Updated line');

      expect(session.outputBuffer.length).toBe(1);
      expect(session.outputBuffer[0].content).toBe('Updated line');
    });

    it('should create new line if updating when buffer is empty', () => {
      session.updateLastLine('New line');

      expect(session.outputBuffer.length).toBe(1);
      expect(session.outputBuffer[0].content).toBe('New line');
    });

    it('should limit output buffer size', () => {
      // Add more than max lines (1000)
      for (let i = 0; i < 1100; i++) {
        session.writeLine(`Line ${i}`);
      }

      expect(session.outputBuffer.length).toBe(1000);
      // Should keep the most recent lines
      expect(session.outputBuffer[0].content).toBe('Line 100');
      expect(session.outputBuffer[999].content).toBe('Line 1099');
    });

    it('should notify listeners on output change', () => {
      const listener = vi.fn();
      session.onOutputChange(listener);

      session.writeLine('Test');

      expect(listener).toHaveBeenCalled();
    });

    it('should unsubscribe listener', () => {
      const listener = vi.fn();
      const unsubscribe = session.onOutputChange(listener);

      session.writeLine('Test 1');
      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();

      session.writeLine('Test 2');
      expect(listener).toHaveBeenCalledTimes(1); // Not called again
    });
  });

  describe('Command History', () => {
    it('should add command to history', () => {
      session.addToHistory('ls -la');

      expect(session.commandHistory).toEqual(['ls -la']);
    });

    it('should not add empty commands to history', () => {
      session.addToHistory('');
      session.addToHistory('   ');

      expect(session.commandHistory).toEqual([]);
    });

    it('should not add duplicate consecutive commands', () => {
      session.addToHistory('ls');
      session.addToHistory('ls');

      expect(session.commandHistory).toEqual(['ls']);
    });

    it('should allow same command after different command', () => {
      session.addToHistory('ls');
      session.addToHistory('pwd');
      session.addToHistory('ls');

      expect(session.commandHistory).toEqual(['ls', 'pwd', 'ls']);
    });

    it('should limit history size', () => {
      // Add more than max history (500)
      for (let i = 0; i < 550; i++) {
        session.addToHistory(`command ${i}`);
      }

      expect(session.commandHistory.length).toBe(500);
      // Should keep the most recent commands
      expect(session.commandHistory[0]).toBe('command 50');
      expect(session.commandHistory[499]).toBe('command 549');
    });

    it('should navigate history up', () => {
      session.addToHistory('cmd1');
      session.addToHistory('cmd2');
      session.addToHistory('cmd3');

      expect(session.navigateHistory('up')).toBe('cmd3');
      expect(session.navigateHistory('up')).toBe('cmd2');
      expect(session.navigateHistory('up')).toBe('cmd1');
      expect(session.navigateHistory('up')).toBeNull(); // At beginning
    });

    it('should navigate history down', () => {
      session.addToHistory('cmd1');
      session.addToHistory('cmd2');
      session.addToHistory('cmd3');

      session.navigateHistory('up'); // cmd3
      session.navigateHistory('up'); // cmd2

      expect(session.navigateHistory('down')).toBe('cmd3');
      expect(session.navigateHistory('down')).toBe(''); // Past end
    });

    it('should return null when navigating empty history', () => {
      expect(session.navigateHistory('up')).toBeNull();
      expect(session.navigateHistory('down')).toBeNull();
    });

    it('should get history copy', () => {
      session.addToHistory('cmd1');
      session.addToHistory('cmd2');

      const history = session.getHistory();

      expect(history).toEqual(['cmd1', 'cmd2']);

      // Should be a copy
      history.push('cmd3');
      expect(session.commandHistory.length).toBe(2);
    });
  });

  describe('Working Directory', () => {
    it('should get working directory', () => {
      expect(session.getWorkingDirectory()).toBe('/');
    });

    it('should change directory', async () => {
      // Mock FileSystemAdapter methods
      const mockFs = session.getFileSystem() as any;
      mockFs.resolvePath = vi.fn().mockReturnValue('/home/user');
      mockFs.findByPath = vi.fn().mockResolvedValue({
        id: 'user-dir',
        name: 'user',
        type: 'directory',
      });
      mockFs.setCurrentDirId = vi.fn();

      await session.changeDirectory('/home/user');

      expect(session.currentPath).toBe('/home/user');
      expect(mockFs.setCurrentDirId).toHaveBeenCalledWith('user-dir');
    });

    it('should throw error if directory not found', async () => {
      const mockFs = session.getFileSystem() as any;
      mockFs.resolvePath = vi.fn().mockReturnValue('/nonexistent');
      mockFs.findByPath = vi.fn().mockResolvedValue(null);

      await expect(session.changeDirectory('/nonexistent')).rejects.toThrow(
        'Directory not found'
      );
    });

    it('should throw error if path is not a directory', async () => {
      const mockFs = session.getFileSystem() as any;
      mockFs.resolvePath = vi.fn().mockReturnValue('/file.txt');
      mockFs.findByPath = vi.fn().mockResolvedValue({
        id: 'file-id',
        name: 'file.txt',
        type: 'file',
      });

      await expect(session.changeDirectory('/file.txt')).rejects.toThrow(
        'Not a directory'
      );
    });
  });

  describe('Prompt', () => {
    it('should get default prompt', () => {
      expect(session.getPrompt()).toBe('user@neon:/$ ');
    });

    it('should replace tilde in prompt', () => {
      session.currentPath = '/home/user';
      expect(session.getPrompt()).toBe('user@neon:/home/user$ ');
    });

    it('should set custom prompt', () => {
      session.setPrompt('$ ');
      expect(session.getPrompt()).toBe('$  '); // Extra space added
    });
  });

  describe('Environment Variables', () => {
    it('should get environment variable', () => {
      expect(session.getEnv('USER')).toBe('user');
    });

    it('should return empty string for undefined variable', () => {
      expect(session.getEnv('UNDEFINED')).toBe('');
    });

    it('should set environment variable', () => {
      session.setEnv('MY_VAR', 'my_value');
      expect(session.getEnv('MY_VAR')).toBe('my_value');
    });

    it('should delete environment variable', () => {
      session.setEnv('TEMP', 'value');
      expect(session.getEnv('TEMP')).toBe('value');

      session.deleteEnv('TEMP');
      expect(session.getEnv('TEMP')).toBe('');
    });

    it('should get all environment variables', () => {
      const env = session.getEnv() as Map<string, string>;

      expect(env).toBeInstanceOf(Map);
      expect(env.get('USER')).toBe('user');
      expect(env.get('HOME')).toBe('/');
    });
  });

  describe('Application Mode', () => {
    let mockApp: TerminalApplication;

    beforeEach(() => {
      mockApp = {
        onMount: vi.fn(),
        onUnmount: vi.fn(),
        onKeyPress: vi.fn().mockResolvedValue(true),
        render: vi.fn(),
      };
    });

    it('should launch app', async () => {
      await session.launchApp(mockApp);

      expect(mockApp.onMount).toHaveBeenCalledWith(session);
      expect(session.getCurrentApp()).toBe(mockApp);
    });

    it('should exit app', async () => {
      await session.launchApp(mockApp);
      await session.exitApp();

      expect(mockApp.onUnmount).toHaveBeenCalled();
      expect(session.getCurrentApp()).toBeNull();
    });

    it('should handle key press in app mode', async () => {
      await session.launchApp(mockApp);

      const continueRunning = await session.handleKeyPress('a', {
        ctrl: false,
        alt: false,
        shift: false,
        meta: false,
      });

      expect(mockApp.onKeyPress).toHaveBeenCalledWith('a', expect.any(Object));
      expect(continueRunning).toBe(true);
    });

    it('should exit app when key press returns false', async () => {
      mockApp.onKeyPress = vi.fn().mockResolvedValue(false);
      await session.launchApp(mockApp);

      const continueRunning = await session.handleKeyPress('q', {
        ctrl: false,
        alt: false,
        shift: false,
        meta: false,
      });

      expect(continueRunning).toBe(false);
      expect(mockApp.onUnmount).toHaveBeenCalled();
      expect(session.getCurrentApp()).toBeNull();
    });

    it('should return false when handling key press without app', async () => {
      const result = await session.handleKeyPress('a', {
        ctrl: false,
        alt: false,
        shift: false,
        meta: false,
      });

      expect(result).toBe(false);
    });
  });

  describe('Interactive Input', () => {
    it('should wait for readline input', async () => {
      const promise = session.readLine('Enter name: ');

      expect(session.isWaitingForReadLine()).toBe(true);
      expect(session.getReadLinePrompt()).toBe('Enter name: ');

      session.resolveReadLine('Alice');

      const result = await promise;
      expect(result).toBe('Alice');
      expect(session.isWaitingForReadLine()).toBe(false);
    });

    it('should readline without prompt', async () => {
      const promise = session.readLine();

      expect(session.isWaitingForReadLine()).toBe(true);
      expect(session.getReadLinePrompt()).toBe('');

      session.resolveReadLine('input');

      await expect(promise).resolves.toBe('input');
    });

    it('should write readline input to output', async () => {
      const promise = session.readLine('> ');

      session.resolveReadLine('test input');

      await promise;

      // Should have written the input to output
      const lastLine = session.outputBuffer[session.outputBuffer.length - 1];
      expect(lastLine.content).toBe('test input');
    });
  });

  describe('Accessors', () => {
    it('should get file system adapter', () => {
      const fs = session.getFileSystem();
      expect(fs).toBeTruthy();
    });

    it('should get API instance', () => {
      const api = session.getAPI();
      expect(api).toBe(mockApi);
    });
  });
});
