/**
 * Unit tests for CompletionEngine
 *
 * Tests tab completion functionality for commands, options, and file paths
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CompletionEngine } from '../CompletionEngine';
import { CommandRegistry } from '../CommandRegistry';
import { TerminalSession } from '../TerminalSession';
import { FileSystemAdapter, FileSystemNode } from '../FileSystemAdapter';
import { AppAPI } from '../../../utils/appApi';

// Helper to create mock AppAPI
function createMockAPI(): AppAPI {
  return {
    initFilesystem: vi.fn().mockResolvedValue({
      id: 'root',
      name: '/',
      type: 'directory',
      mimeType: '',
      content: '',
      size: 0,
      createdAt: new Date().toISOString(),
      modifiedAt: new Date().toISOString(),
    }),
    getFile: vi.fn(),
    listDirectory: vi.fn(),
    createFile: vi.fn(),
    createDirectory: vi.fn(),
    deleteFile: vi.fn(),
    moveFile: vi.fn(),
    copyFile: vi.fn(),
    renameFile: vi.fn(),
  } as any;
}

describe('CompletionEngine', () => {
  let engine: CompletionEngine;
  let registry: CommandRegistry;
  let session: TerminalSession;
  let mockAPI: AppAPI;

  beforeEach(async () => {
    mockAPI = createMockAPI();
    registry = new CommandRegistry();
    session = new TerminalSession(mockAPI, '/');
    engine = new CompletionEngine(registry);

    // Setup file system structure:
    // /
    //   Documents/
    //     readme.txt
    //     welcome.txt
    //   Pictures/
    //     my-pic.png
    const rootFiles: FileSystemNode[] = [
      {
        id: 'documents',
        name: 'Documents',
        type: 'directory',
        mimeType: '',
        content: '',
        size: 0,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
      },
      {
        id: 'pictures',
        name: 'Pictures',
        type: 'directory',
        mimeType: '',
        content: '',
        size: 0,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
      },
    ];

    const documentsFiles: FileSystemNode[] = [
      {
        id: 'readme',
        name: 'readme.txt',
        type: 'file',
        mimeType: 'text/plain',
        content: 'README',
        size: 6,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
      },
      {
        id: 'welcome',
        name: 'welcome.txt',
        type: 'file',
        mimeType: 'text/plain',
        content: 'WELCOME',
        size: 7,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
      },
    ];

    const picturesFiles: FileSystemNode[] = [
      {
        id: 'mypic',
        name: 'my-pic.png',
        type: 'file',
        mimeType: 'image/png',
        content: '',
        size: 1024,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
      },
    ];

    // Mock file system responses
    (mockAPI.listDirectory as any).mockImplementation((dirId: string) => {
      if (dirId === 'root') return Promise.resolve(rootFiles);
      if (dirId === 'documents') return Promise.resolve(documentsFiles);
      if (dirId === 'pictures') return Promise.resolve(picturesFiles);
      return Promise.reject(new Error('Directory not found'));
    });

    (mockAPI.getFile as any).mockImplementation((id: string) => {
      const allFiles = [
        { id: 'root', name: '/', type: 'directory' },
        ...rootFiles,
        ...documentsFiles,
        ...picturesFiles,
      ];
      const file = allFiles.find((f) => f.id === id);
      if (file) return Promise.resolve(file);
      return Promise.reject(new Error('File not found'));
    });

    await session.init();
  });

  describe('Path Completion - Basic', () => {
    it('should complete "Pic" to "Pictures/" (not "Documents")', async () => {
      const result = await engine.complete(session, 'cd Pic', 6);

      expect(result.completions).toEqual(['Pictures/']);
      expect(result.prefix).toBe('Pic');
      expect(result.commonPrefix).toBe('Pictures/');
    });

    it('should complete "Do" to "Documents/"', async () => {
      const result = await engine.complete(session, 'cd Do', 5);

      expect(result.completions).toEqual(['Documents/']);
      expect(result.prefix).toBe('Do');
      expect(result.commonPrefix).toBe('Documents/');
    });

    it('should show both directories when no prefix given', async () => {
      const result = await engine.complete(session, 'cd ', 3);

      expect(result.completions).toContain('Documents/');
      expect(result.completions).toContain('Pictures/');
      expect(result.completions.length).toBe(2);
    });
  });

  describe('Path Completion - With Directory Separator', () => {
    it('should complete "Documents/" to show contents of Documents', async () => {
      const result = await engine.complete(session, 'cd Documents/', 13);

      expect(result.completions).toEqual(['Documents/readme.txt', 'Documents/welcome.txt']);
      expect(result.prefix).toBe('Documents/');
      // Common prefix should be "Documents/" since there's no common suffix beyond that
      expect(result.commonPrefix).toBe('Documents/');
    });

    it('should complete "Documents/we" to "Documents/welcome.txt"', async () => {
      const result = await engine.complete(session, 'cat Documents/we', 16);

      expect(result.completions).toEqual(['Documents/welcome.txt']);
      expect(result.prefix).toBe('Documents/we');
      expect(result.commonPrefix).toBe('Documents/welcome.txt');
    });

    it('should complete "Documents/r" to "Documents/readme.txt"', async () => {
      const result = await engine.complete(session, 'cat Documents/r', 15);

      expect(result.completions).toEqual(['Documents/readme.txt']);
      expect(result.prefix).toBe('Documents/r');
      expect(result.commonPrefix).toBe('Documents/readme.txt');
    });

    it('should show all files in Documents when completing "Documents/" with no additional prefix', async () => {
      const result = await engine.complete(session, 'ls Documents/', 13);

      expect(result.completions).toContain('Documents/readme.txt');
      expect(result.completions).toContain('Documents/welcome.txt');
      expect(result.completions.length).toBe(2);
    });
  });

  describe('Path Completion - Edge Cases', () => {
    it('should return empty when no matches found', async () => {
      const result = await engine.complete(session, 'cd Nonexistent', 14);

      expect(result.completions).toEqual([]);
      expect(result.prefix).toBe('Nonexistent');
    });

    it('should handle multiple words and complete the last argument', async () => {
      const result = await engine.complete(session, 'cat Documents/readme.txt Pic', 28);

      expect(result.completions).toEqual(['Pictures/']);
      expect(result.prefix).toBe('Pic');
    });

    it('should find common prefix when multiple completions share prefix', async () => {
      const result = await engine.complete(session, 'cat Documents/', 14);

      // Both files start with "Documents/"
      expect(result.commonPrefix).toBe('Documents/');
      expect(result.completions.length).toBe(2);
    });
  });

  describe('Command Completion', () => {
    it('should complete command names', async () => {
      // Register a test command
      registry.register({
        name: 'test',
        description: 'Test command',
        execute: vi.fn(),
      });

      const result = await engine.complete(session, 'te', 2);

      expect(result.completions).toContain('test');
    });

    it('should not show path completions when completing command name', async () => {
      const result = await engine.complete(session, 'Pi', 2);

      // Should not complete to "Pictures/" - that's a path, not a command
      expect(result.completions).not.toContain('Pictures/');
    });
  });

  describe('Integration - CompletionEngine.completePath()', () => {
    it('should filter by prefix correctly', async () => {
      // Directly test the path completion logic
      const result = await engine.complete(session, 'ls P', 4);

      expect(result.completions).toEqual(['Pictures/']);
      expect(result.completions).not.toContain('Documents/');
    });

    it('should resolve paths with directory separators', async () => {
      const result = await engine.complete(session, 'cat Pictures/m', 14);

      expect(result.completions).toEqual(['Pictures/my-pic.png']);
    });
  });

  describe('Path Completion - Spaces in Paths', () => {
    beforeEach(async () => {
      // Add directories and files with spaces to the mock file system
      const spacedDirs: FileSystemNode[] = [
        {
          id: 'my-docs',
          name: 'My Documents',
          type: 'directory',
          mimeType: '',
          content: '',
          size: 0,
          createdAt: new Date().toISOString(),
          modifiedAt: new Date().toISOString(),
        },
        {
          id: 'important-files',
          name: 'Important Files',
          type: 'directory',
          mimeType: '',
          content: '',
          size: 0,
          createdAt: new Date().toISOString(),
          modifiedAt: new Date().toISOString(),
        },
      ];

      const spacedFiles: FileSystemNode[] = [
        {
          id: 'my-notes',
          name: 'my notes.txt',
          type: 'file',
          mimeType: 'text/plain',
          content: 'Notes',
          size: 5,
          createdAt: new Date().toISOString(),
          modifiedAt: new Date().toISOString(),
        },
        {
          id: 'project-plan',
          name: 'project plan.md',
          type: 'file',
          mimeType: 'text/markdown',
          content: 'Plan',
          size: 4,
          createdAt: new Date().toISOString(),
          modifiedAt: new Date().toISOString(),
        },
      ];

      // Update mock to include spaced directories at root
      (mockAPI.listDirectory as any).mockImplementation((dirId: string) => {
        if (dirId === 'root') {
          const allDirs = [
            {
              id: 'documents',
              name: 'Documents',
              type: 'directory',
              mimeType: '',
              content: '',
              size: 0,
              createdAt: new Date().toISOString(),
              modifiedAt: new Date().toISOString(),
            },
            {
              id: 'pictures',
              name: 'Pictures',
              type: 'directory',
              mimeType: '',
              content: '',
              size: 0,
              createdAt: new Date().toISOString(),
              modifiedAt: new Date().toISOString(),
            },
            ...spacedDirs,
          ];
          return Promise.resolve(allDirs);
        }
        if (dirId === 'my-docs') return Promise.resolve(spacedFiles);
        if (dirId === 'important-files') return Promise.resolve([]);
        if (dirId === 'documents') {
          return Promise.resolve([
            {
              id: 'readme',
              name: 'readme.txt',
              type: 'file',
              mimeType: 'text/plain',
              content: 'README',
              size: 6,
              createdAt: new Date().toISOString(),
              modifiedAt: new Date().toISOString(),
            },
            {
              id: 'welcome',
              name: 'welcome.txt',
              type: 'file',
              mimeType: 'text/plain',
              content: 'WELCOME',
              size: 7,
              createdAt: new Date().toISOString(),
              modifiedAt: new Date().toISOString(),
            },
          ]);
        }
        return Promise.reject(new Error('Directory not found'));
      });

      (mockAPI.getFile as any).mockImplementation((id: string) => {
        const allFiles = [
          { id: 'root', name: '/', type: 'directory' },
          { id: 'documents', name: 'Documents', type: 'directory' },
          { id: 'pictures', name: 'Pictures', type: 'directory' },
          ...spacedDirs,
          ...spacedFiles,
        ];
        const file = allFiles.find((f) => f.id === id);
        if (file) return Promise.resolve(file);
        return Promise.reject(new Error('File not found'));
      });
    });

    it('should complete paths with spaces and wrap in quotes', async () => {
      const result = await engine.complete(session, 'cd My', 5);

      // Should complete to "My Documents/" with quotes
      expect(result.completions).toContain('"My Documents/"');
      expect(result.completions).not.toContain('My Documents/');
    });

    it('should complete partial quoted path', async () => {
      const result = await engine.complete(session, 'cd "My Doc', 10);

      // Should complete the quoted path
      expect(result.completions).toContain('"My Documents/"');
    });

    it('should handle multiple directories with spaces', async () => {
      const result = await engine.complete(session, 'cd ', 3);

      // Should include both directories with spaces, quoted
      expect(result.completions).toContain('"My Documents/"');
      expect(result.completions).toContain('"Important Files/"');
      expect(result.completions).toContain('Documents/');
      expect(result.completions).toContain('Pictures/');
    });

    it('should complete files with spaces inside quoted directory path', async () => {
      const result = await engine.complete(session, 'cat "My Documents/', 18);

      expect(result.completions).toContain('"My Documents/my notes.txt"');
      expect(result.completions).toContain('"My Documents/project plan.md"');
    });

    it('should filter files with spaces by prefix', async () => {
      const result = await engine.complete(session, 'cat "My Documents/my', 20);

      expect(result.completions).toContain('"My Documents/my notes.txt"');
      expect(result.completions).not.toContain('"My Documents/project plan.md"');
    });
  });
});
