/**
 * Unit tests for ShellParser
 *
 * Tests shell-like argument parsing respecting quotes and escaping
 */

import { describe, it, expect } from 'vitest';
import { ShellParser } from '../ShellParser';

describe('ShellParser', () => {
  describe('parseArguments', () => {
    it('should parse simple arguments', () => {
      const result = ShellParser.parseArguments('cd Documents Pictures');

      expect(result).toEqual(['cd', 'Documents', 'Pictures']);
    });

    it('should handle multiple spaces between arguments', () => {
      const result = ShellParser.parseArguments('cd    Documents    Pictures');

      expect(result).toEqual(['cd', 'Documents', 'Pictures']);
    });

    it('should parse double-quoted arguments with spaces', () => {
      const result = ShellParser.parseArguments('cd "My Documents"');

      expect(result).toEqual(['cd', 'My Documents']);
    });

    it('should parse single-quoted arguments with spaces', () => {
      const result = ShellParser.parseArguments("cd 'My Documents'");

      expect(result).toEqual(['cd', 'My Documents']);
    });

    it('should handle escaped spaces', () => {
      const result = ShellParser.parseArguments('cd My\\ Documents');

      expect(result).toEqual(['cd', 'My Documents']);
    });

    it('should handle mixed quoted and unquoted arguments', () => {
      const result = ShellParser.parseArguments('cp "My Documents/file.txt" destination');

      expect(result).toEqual(['cp', 'My Documents/file.txt', 'destination']);
    });

    it('should handle quotes within quoted strings', () => {
      const result = ShellParser.parseArguments('echo "He said \\"hello\\""');

      expect(result).toEqual(['echo', 'He said "hello"']);
    });

    it('should handle empty quotes', () => {
      const result = ShellParser.parseArguments('echo "" test');

      expect(result).toEqual(['echo', '', 'test']);
    });

    it('should handle partial quotes at end of string', () => {
      const result = ShellParser.parseArguments('cd "My Doc');

      expect(result).toEqual(['cd', 'My Doc']);
    });

    it('should handle trailing space', () => {
      const result = ShellParser.parseArguments('cd Documents ');

      expect(result).toEqual(['cd', 'Documents', '']);
    });
  });

  describe('getPartialArgument', () => {
    it('should get last argument when no trailing space', () => {
      const result = ShellParser.getPartialArgument('cd Doc');

      expect(result).toEqual({
        partial: 'Doc',
        isQuoted: false,
        quoteChar: null,
        startIndex: 3,
      });
    });

    it('should return empty string with trailing space', () => {
      const result = ShellParser.getPartialArgument('cd Documents ');

      expect(result).toEqual({
        partial: '',
        isQuoted: false,
        quoteChar: null,
        startIndex: 13,
      });
    });

    it('should detect partial argument inside double quotes', () => {
      const result = ShellParser.getPartialArgument('cd "My Doc');

      expect(result).toEqual({
        partial: 'My Doc',
        isQuoted: true,
        quoteChar: '"',
        startIndex: 4,
      });
    });

    it('should detect partial argument inside single quotes', () => {
      const result = ShellParser.getPartialArgument("cd 'My Doc");

      expect(result).toEqual({
        partial: 'My Doc',
        isQuoted: true,
        quoteChar: "'",
        startIndex: 4,
      });
    });

    it('should handle escaped spaces in partial argument', () => {
      const result = ShellParser.getPartialArgument('cd My\\ Doc');

      expect(result).toEqual({
        partial: 'My Doc',
        isQuoted: false,
        quoteChar: null,
        startIndex: 3,
      });
    });

    it('should handle completed quoted argument followed by partial', () => {
      const result = ShellParser.getPartialArgument('cp "My Documents/file.txt" dest');

      expect(result).toEqual({
        partial: 'dest',
        isQuoted: false,
        quoteChar: null,
        startIndex: 28,
      });
    });
  });

  describe('quoteIfNeeded', () => {
    it('should not quote paths without spaces', () => {
      const result = ShellParser.quoteIfNeeded('Documents/file.txt');

      expect(result).toBe('Documents/file.txt');
    });

    it('should quote paths with spaces', () => {
      const result = ShellParser.quoteIfNeeded('My Documents/file.txt');

      expect(result).toBe('"My Documents/file.txt"');
    });

    it('should not quote if already quoted', () => {
      const result = ShellParser.quoteIfNeeded('"My Documents"', true);

      expect(result).toBe('"My Documents"');
    });

    it('should escape existing quotes when quoting', () => {
      const result = ShellParser.quoteIfNeeded('My "Important" Documents');

      expect(result).toBe('"My \\"Important\\" Documents"');
    });

    it('should handle paths with special characters', () => {
      const result = ShellParser.quoteIfNeeded('file (1).txt');

      expect(result).toBe('"file (1).txt"');
    });
  });

  describe('Integration with command parsing', () => {
    it('should correctly parse: cd "My Documents"', () => {
      const args = ShellParser.parseArguments('cd "My Documents"');

      expect(args).toEqual(['cd', 'My Documents']);
      expect(args.length).toBe(2);
    });

    it('should correctly parse: cp "My Documents/file.txt" "Other Folder/"', () => {
      const args = ShellParser.parseArguments('cp "My Documents/file.txt" "Other Folder/"');

      expect(args).toEqual(['cp', 'My Documents/file.txt', 'Other Folder/']);
      expect(args.length).toBe(3);
    });

    it('should correctly parse mixed: cat file1.txt "My Documents/file2.txt" file3.txt', () => {
      const args = ShellParser.parseArguments('cat file1.txt "My Documents/file2.txt" file3.txt');

      expect(args).toEqual(['cat', 'file1.txt', 'My Documents/file2.txt', 'file3.txt']);
      expect(args.length).toBe(4);
    });
  });
});
