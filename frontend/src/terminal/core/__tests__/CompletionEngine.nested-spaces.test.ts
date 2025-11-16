/**
 * Unit tests for CompletionEngine with nested directories containing spaces
 *
 * Tests the specific bug where completing paths like:
 * Documents/My Folder/Another Folder
 * produces incorrect results
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CompletionEngine } from '../CompletionEngine';
import { CommandRegistry } from '../CommandRegistry';
import { ArgumentParser } from '../ArgumentParser';
import { TerminalSession } from '../TerminalSession';
import { FileSystemNode } from '../FileSystemAdapter';
import { AppAPI } from '../../../utils/appApi';

// Helper to create mock AppAPI
function createMockAPI(): AppAPI {
  return {
    initFilesystem: vi.fn().mockResolvedValue({
      id: 'root',
      name: '/',
      type: 'directory',
      mime_type: '',
      content: '',
      size: 0,
      parent_id: null,
      created_at: new Date().toISOString(),
      modified_at: new Date().toISOString(),
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

describe('CompletionEngine - Nested Directories with Spaces', () => {
  let engine: CompletionEngine;
  let registry: CommandRegistry;
  let argParser: ArgumentParser;
  let session: TerminalSession;
  let mockAPI: AppAPI;

  beforeEach(async () => {
    mockAPI = createMockAPI();
    registry = new CommandRegistry();
    argParser = new ArgumentParser();
    session = new TerminalSession(mockAPI, '/');
    engine = new CompletionEngine(registry, argParser);

    // Setup file system structure:
    // /
    //   Documents/
    //     My Folder/
    //       Another Folder/
    //         file.txt
    //       test.txt
    //     Simple/
    //       data.txt

    const rootFiles: FileSystemNode[] = [
      {
        id: 'documents',
        name: 'Documents',
        type: 'directory',
        mime_type: '',
        content: '',
        size: 0,
        parent_id: 'root',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
    ];

    const documentsFiles: FileSystemNode[] = [
      {
        id: 'my-folder',
        name: 'My Folder',
        type: 'directory',
        mime_type: '',
        content: '',
        size: 0,
        parent_id: 'documents',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
      {
        id: 'simple',
        name: 'Simple',
        type: 'directory',
        mime_type: '',
        content: '',
        size: 0,
        parent_id: 'documents',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
    ];

    const myFolderFiles: FileSystemNode[] = [
      {
        id: 'another-folder',
        name: 'Another Folder',
        type: 'directory',
        mime_type: '',
        content: '',
        size: 0,
        parent_id: 'my-folder',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
      {
        id: 'test-txt',
        name: 'test.txt',
        type: 'file',
        mime_type: 'text/plain',
        content: 'test',
        size: 4,
        parent_id: 'my-folder',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
    ];

    const anotherFolderFiles: FileSystemNode[] = [
      {
        id: 'file-txt',
        name: 'file.txt',
        type: 'file',
        mime_type: 'text/plain',
        content: 'content',
        size: 7,
        parent_id: 'another-folder',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
    ];

    const simpleFiles: FileSystemNode[] = [
      {
        id: 'data-txt',
        name: 'data.txt',
        type: 'file',
        mime_type: 'text/plain',
        content: 'data',
        size: 4,
        parent_id: 'simple',
        created_at: new Date().toISOString(),
        modified_at: new Date().toISOString(),
      },
    ];

    // Mock file system responses
    (mockAPI.listDirectory as any).mockImplementation((dirId: string) => {
      if (dirId === 'root') return Promise.resolve(rootFiles);
      if (dirId === 'documents') return Promise.resolve(documentsFiles);
      if (dirId === 'my-folder') return Promise.resolve(myFolderFiles);
      if (dirId === 'another-folder') return Promise.resolve(anotherFolderFiles);
      if (dirId === 'simple') return Promise.resolve(simpleFiles);
      return Promise.reject(new Error('Directory not found'));
    });

    (mockAPI.getFile as any).mockImplementation((id: string) => {
      const allFiles = [
        { id: 'root', name: '/', type: 'directory' },
        ...rootFiles,
        ...documentsFiles,
        ...myFolderFiles,
        ...anotherFolderFiles,
        ...simpleFiles,
      ];
      const file = allFiles.find((f) => f.id === id);
      if (file) return Promise.resolve(file);
      return Promise.reject(new Error('File not found'));
    });

    await session.init();
  });

  describe('Single level completion with spaces', () => {
    it('should complete "Documents/My" to "Documents/My Folder/"', async () => {
      const commandLine = 'cd Documents/My';
      const cursorPos = commandLine.length;

      const result = await engine.complete(session, commandLine, cursorPos);

      expect(result.completions).toEqual(["'Documents/My Folder/'"]);
      expect(result.prefix).toBe('Documents/My');
    });

    it('should list contents of "Documents/My Folder/"', async () => {
      const commandLine = "cd 'Documents/My Folder/'";
      const cursorPos = commandLine.length;

      const result = await engine.complete(session, commandLine, cursorPos);

      expect(result.completions).toContain("'Documents/My Folder/Another Folder/'");
      expect(result.completions).toContain("'Documents/My Folder/test.txt'");
    });
  });

  describe('Nested level completion with spaces - THE BUG', () => {
    it('should complete "Documents/My Folder/A" to "Documents/My Folder/Another Folder/"', async () => {
      // This is the problematic case!
      // Input: cd 'Documents/My Folder/A
      // Expected completion: 'Documents/My Folder/Another Folder/'
      // Bug produces: 'Documents My 'Documents/My Folder/Another Folder/'

      const commandLine = "cd 'Documents/My Folder/A";
      const cursorPos = commandLine.length;

      const result = await engine.complete(session, commandLine, cursorPos);

      // Should complete to the full quoted path
      expect(result.completions).toEqual(["'Documents/My Folder/Another Folder/'"]);

      // The prefix should be the partial path (without the quote since ArgumentParser strips it)
      expect(result.prefix).toBe("Documents/My Folder/A");

      // Common prefix should be the full completion
      expect(result.commonPrefix).toBe("'Documents/My Folder/Another Folder/'");
    });

    it('should complete nested path without quotes when no spaces in current segment', async () => {
      const commandLine = "cd Documents/Simple/d";
      const cursorPos = commandLine.length;

      const result = await engine.complete(session, commandLine, cursorPos);

      expect(result.completions).toEqual(['Documents/Simple/data.txt']);
      expect(result.prefix).toBe('Documents/Simple/d');
    });

    it('should handle completion in the middle of nested quoted path', async () => {
      const commandLine = "cd 'Documents/My Folder/Ano";
      const cursorPos = commandLine.length;

      const result = await engine.complete(session, commandLine, cursorPos);

      expect(result.completions).toEqual(["'Documents/My Folder/Another Folder/'"]);
    });
  });

  describe('Integration test - successive completions', () => {
    it('should handle two successive completions correctly', async () => {
      // Simulate the exact user scenario:
      // 1. Type: cd Documents/My<TAB>
      // 2. Completes to: cd 'Documents/My Folder/'
      // 3. Type more: cd 'Documents/My Folder/A<TAB>
      // 4. Should complete to: cd 'Documents/My Folder/Another Folder/'

      // First completion
      const input1 = 'cd Documents/My';
      const result1 = await engine.complete(session, input1, input1.length);

      expect(result1.completions).toEqual(["'Documents/My Folder/'"]);

      // Simulate what TerminalApp would do
      const replaceStart1 = result1.replaceStart ?? (input1.length - result1.prefix.length);
      const replaceEnd1 = result1.replaceEnd ?? input1.length;
      const completed1 =
        input1.substring(0, replaceStart1) +
        result1.completions[0] +
        input1.substring(replaceEnd1);

      // After first completion
      expect(completed1).toBe("cd 'Documents/My Folder/'");

      // User types 'A'
      const input2 = completed1.slice(0, -1) + 'A'; // Remove trailing / and add A
      // input2 should be: "cd 'Documents/My Folder/A"

      // Second completion
      const result2 = await engine.complete(session, input2, input2.length);

      expect(result2.completions).toEqual(["'Documents/My Folder/Another Folder/'"]);

      // Simulate what TerminalApp would do
      const replaceStart2 = result2.replaceStart ?? (input2.length - result2.prefix.length);
      const replaceEnd2 = result2.replaceEnd ?? input2.length;
      const completed2 =
        input2.substring(0, replaceStart2) +
        result2.completions[0] +
        input2.substring(replaceEnd2);

      // Final result should be correct
      expect(completed2).toBe("cd 'Documents/My Folder/Another Folder/'");

      // NOT: 'Documents My 'Documents/My Folder/Another Folder/'
    });

    it('should handle Tab cycling through multiple suggestions correctly', async () => {
      // This tests the bug where Tab cycling duplicates the prefix
      // Scenario: cd Documents/<TAB> shows both "My Folder/" and "Simple/"
      // Pressing Tab again should cycle, not duplicate

      const input = 'cd Documents/';
      const result = await engine.complete(session, input, input.length);

      // Should show both directories
      expect(result.completions).toContain("'Documents/My Folder/'");
      expect(result.completions).toContain('Documents/Simple/');
      expect(result.completions.length).toBe(2);

      // Get replace indices
      const replaceStart = result.replaceStart ?? (input.length - result.prefix.length);
      const replaceEnd = result.replaceEnd ?? input.length;

      // First Tab: complete to common prefix (should be "Documents/")
      const completed1 = result.commonPrefix.length > result.prefix.length
        ? input.substring(0, replaceStart) + result.commonPrefix + input.substring(replaceEnd)
        : input;

      // Simulate cycling to first suggestion
      const cycled1 =
        completed1.substring(0, replaceStart) +
        result.completions[0] +
        completed1.substring(replaceEnd);

      // Should NOT have duplicate prefix
      expect(cycled1).not.toContain("Documents Documents");
      expect(cycled1).not.toContain("'Documents/'Documents/");

      // Simulate cycling to second suggestion
      const cycled2 =
        completed1.substring(0, replaceStart) +
        result.completions[1] +
        completed1.substring(replaceEnd);

      // Should NOT have duplicate prefix
      expect(cycled2).not.toContain("Documents Documents");
      expect(cycled2).toBe("cd Documents/Simple/");
    });
  });

  describe('ReplaceStart and ReplaceEnd indices', () => {
    it('should provide correct replace indices for unquoted path', async () => {
      const commandLine = 'cd Documents/My';
      const cursorPos = commandLine.length;

      const result = await engine.complete(session, commandLine, cursorPos);

      // replaceStart should be at the beginning of "Documents/My" (after "cd ")
      expect(result.replaceStart).toBe(3);
      // replaceEnd should be at the end of the partial path
      expect(result.replaceEnd).toBe(15);
    });

    it('should provide correct replace indices for quoted path', async () => {
      const commandLine = "cd 'Documents/My Folder/A";
      const cursorPos = commandLine.length; // 26

      const result = await engine.complete(session, commandLine, cursorPos);

      // replaceStart should include the opening quote
      expect(result.replaceStart).toBe(3);
      // replaceEnd should be at cursor (but ArgumentParser returns endIndex of last parsed char, which is cursorPos - 1)
      expect(result.replaceEnd).toBe(25);
    });
  });
});
