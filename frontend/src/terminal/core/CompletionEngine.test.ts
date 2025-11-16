/**
 * Tests for CompletionEngine with quoted filename support
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { CompletionEngine } from './CompletionEngine';
import { CommandRegistry } from './CommandRegistry';
import { ArgumentParser } from './ArgumentParser';
import { TerminalSession } from './TerminalSession';
import { FileSystemAdapter } from './FileSystemAdapter';
import type { FileNode } from '../../types/models';

// Mock FileSystemAdapter
vi.mock('./FileSystemAdapter');

describe('CompletionEngine - Quoted Filenames', () => {
  let completionEngine: CompletionEngine;
  let registry: CommandRegistry;
  let argParser: ArgumentParser;
  let session: TerminalSession;
  let mockFs: any;

  beforeEach(() => {
    registry = new CommandRegistry();
    argParser = new ArgumentParser();
    completionEngine = new CompletionEngine(registry, argParser);

    // Create mock session
    session = {
      getFileSystem: vi.fn(),
      getWorkingDirectory: vi.fn().mockReturnValue('/'),
      getAPI: vi.fn(),
    } as any;

    // Create mock filesystem
    mockFs = {
      listDirectory: vi.fn(),
      resolvePath: vi.fn((path: string) => path),
    };

    (session.getFileSystem as any).mockReturnValue(mockFs);
  });

  describe('filename completion with spaces', () => {
    it('should quote filenames with spaces when completing', async () => {
      // Setup: directory contains files with spaces
      const files: FileNode[] = [
        { id: '1', name: 'my file.txt', type: 'file' } as FileNode,
        { id: '2', name: 'another file.txt', type: 'file' } as FileNode,
        { id: '3', name: 'no-spaces.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat my"
      const result = await completionEngine.complete(session, 'cat my', 6);

      // Should have one completion: 'my file.txt'
      expect(result.completions).toHaveLength(1);
      // Should be quoted because it has a space
      expect(result.completions[0]).toBe("'my file.txt'");
    });

    it('should not quote filenames without special characters', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'simple.txt', type: 'file' } as FileNode,
        { id: '2', name: 'another-simple.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat sim"
      const result = await completionEngine.complete(session, 'cat sim', 7);

      expect(result.completions).toHaveLength(1);
      // Should NOT be quoted
      expect(result.completions[0]).toBe('simple.txt');
    });

    it('should handle completion with existing quotes', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'my file.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat 'my"
      const result = await completionEngine.complete(session, "cat 'my", 7);

      // Should complete the filename
      expect(result.completions).toHaveLength(1);
      // The completion should be quoted
      expect(result.completions[0]).toBe("'my file.txt'");
    });

    it('should handle multiple files with spaces', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'file one.txt', type: 'file' } as FileNode,
        { id: '2', name: 'file two.txt', type: 'file' } as FileNode,
        { id: '3', name: 'file three.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat file"
      const result = await completionEngine.complete(session, 'cat file', 8);

      // Should have three completions, all quoted
      expect(result.completions).toHaveLength(3);
      expect(result.completions).toContain("'file one.txt'");
      expect(result.completions).toContain("'file two.txt'");
      expect(result.completions).toContain("'file three.txt'");
    });

    it('should handle directory paths with spaces', async () => {
      const dirs: FileNode[] = [
        { id: '1', name: 'my folder', type: 'directory' } as FileNode,
        { id: '2', name: 'my other folder', type: 'directory' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(dirs);

      // Complete "cd my"
      registry.register({
        name: 'cd',
        description: 'Change directory',
        usage: 'cd <path>',
        execute: async () => {},
      });

      const result = await completionEngine.complete(session, 'cd my', 5);

      // Should have two completions with trailing slashes
      expect(result.completions).toHaveLength(2);
      expect(result.completions).toContain("'my folder/'");
      expect(result.completions).toContain("'my other folder/'");
    });

    it('should use double quotes for filenames with single quotes', async () => {
      const files: FileNode[] = [
        { id: '1', name: "it's a file.txt", type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat it"
      const result = await completionEngine.complete(session, 'cat it', 6);

      expect(result.completions).toHaveLength(1);
      // Should use double quotes because filename contains single quote
      expect(result.completions[0]).toBe('"it\'s a file.txt"');
    });

    it('should handle files with special characters', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'file*.txt', type: 'file' } as FileNode,
        { id: '2', name: 'file?.txt', type: 'file' } as FileNode,
        { id: '3', name: 'file$var.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat file"
      const result = await completionEngine.complete(session, 'cat file', 8);

      // All should be quoted due to special characters
      expect(result.completions).toHaveLength(3);
      result.completions.forEach((completion) => {
        expect(completion.startsWith("'") || completion.startsWith('"')).toBe(true);
      });
    });
  });

  describe('command completion', () => {
    it('should not quote command names', async () => {
      registry.register({
        name: 'my-command',
        description: 'Test',
        usage: 'my-command',
        execute: async () => {},
      });

      const result = await completionEngine.complete(session, 'my', 2);

      expect(result.completions).toContain('my-command');
      // Should not be quoted even though it has a dash
      expect(result.completions[0]).toBe('my-command');
    });
  });

  describe('option completion', () => {
    it('should not quote option flags', async () => {
      registry.register({
        name: 'test',
        description: 'Test',
        usage: 'test',
        execute: async () => {},
        options: [
          { flag: '--verbose', description: 'Verbose output' },
          { flag: '-v', description: 'Short verbose' },
        ],
      });

      const result = await completionEngine.complete(session, 'test --v', 8);

      expect(result.completions).toContain('--verbose');
      // Should not be quoted
      expect(result.completions[0]).toBe('--verbose');
    });
  });

  describe('path completion with quotes', () => {
    it('should handle path with directory separator', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'file with spaces.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);
      mockFs.resolvePath.mockReturnValue('/home/');

      // Complete "cat /home/file"
      const result = await completionEngine.complete(session, 'cat /home/file', 14);

      expect(result.completions).toHaveLength(1);
      // Should preserve path and quote filename
      expect(result.completions[0]).toContain('/home/');
      expect(result.completions[0]).toMatch(/^'.*'$/); // Should be quoted
    });
  });

  describe('completion result replacement', () => {
    it('should provide correct replacement positions', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'test.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat te"
      const result = await completionEngine.complete(session, 'cat te', 6);

      expect(result.replaceStart).toBeDefined();
      expect(result.replaceEnd).toBeDefined();
      // replaceStart should point to start of 'te'
      expect(result.replaceStart).toBe(4);
      // replaceEnd should point to end of 'te'
      expect(result.replaceEnd).toBe(6);
    });

    it('should provide replacement positions for quoted args', async () => {
      const files: FileNode[] = [
        { id: '1', name: 'test file.txt', type: 'file' } as FileNode,
      ];

      mockFs.listDirectory.mockResolvedValue(files);

      // Complete "cat 'te"
      const result = await completionEngine.complete(session, "cat 'te", 7);

      expect(result.replaceStart).toBeDefined();
      expect(result.replaceEnd).toBeDefined();
    });
  });
});
