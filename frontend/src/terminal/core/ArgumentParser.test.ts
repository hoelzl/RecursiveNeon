/**
 * Tests for ArgumentParser
 */

import { describe, it, expect } from 'vitest';
import { ArgumentParser } from './ArgumentParser';

describe('ArgumentParser', () => {
  const parser = new ArgumentParser();

  describe('parseCommandLine', () => {
    it('should parse simple command with no arguments', () => {
      const result = parser.parseCommandLine('ls');
      expect(result.command).toBe('ls');
      expect(result.args).toEqual([]);
    });

    it('should parse command with simple arguments', () => {
      const result = parser.parseCommandLine('ls -la /home');
      expect(result.command).toBe('ls');
      expect(result.args).toEqual(['-la', '/home']);
    });

    it('should parse command with single-quoted argument', () => {
      const result = parser.parseCommandLine("cat 'file with spaces.txt'");
      expect(result.command).toBe('cat');
      expect(result.args).toEqual(['file with spaces.txt']);
    });

    it('should parse command with double-quoted argument', () => {
      const result = parser.parseCommandLine('cat "file with spaces.txt"');
      expect(result.command).toBe('cat');
      expect(result.args).toEqual(['file with spaces.txt']);
    });

    it('should parse command with escaped space', () => {
      const result = parser.parseCommandLine('cat file\\ with\\ spaces.txt');
      expect(result.command).toBe('cat');
      expect(result.args).toEqual(['file with spaces.txt']);
    });

    it('should parse command with escaped quotes', () => {
      const result = parser.parseCommandLine('echo \\"hello\\" world');
      expect(result.command).toBe('echo');
      expect(result.args).toEqual(['"hello"', 'world']);
    });

    it('should parse command with escaped backslash', () => {
      const result = parser.parseCommandLine('echo back\\\\slash');
      expect(result.command).toBe('echo');
      expect(result.args).toEqual(['back\\slash']);
    });

    it('should parse mixed quoted and unquoted arguments', () => {
      const result = parser.parseCommandLine('cmd arg1 "arg 2" arg3 \'arg 4\'');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(['arg1', 'arg 2', 'arg3', 'arg 4']);
    });

    it('should handle multiple spaces between arguments', () => {
      const result = parser.parseCommandLine('cmd   arg1    arg2     arg3');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(['arg1', 'arg2', 'arg3']);
    });

    it('should handle tabs between arguments', () => {
      const result = parser.parseCommandLine('cmd\targ1\t\targ2');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(['arg1', 'arg2']);
    });

    it('should handle empty quoted strings', () => {
      const result = parser.parseCommandLine('cmd "" \'\'');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(['', '']);
    });

    it('should handle quotes within different quote types', () => {
      const result = parser.parseCommandLine('cmd "it\'s" \'say "hi"\'');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(["it's", 'say "hi"']);
    });

    it('should handle empty command line', () => {
      const result = parser.parseCommandLine('');
      expect(result.command).toBe('');
      expect(result.args).toEqual([]);
    });

    it('should handle whitespace-only command line', () => {
      const result = parser.parseCommandLine('   ');
      expect(result.command).toBe('');
      expect(result.args).toEqual([]);
    });

    it('should parse complex command line', () => {
      const result = parser.parseCommandLine(
        'mv "my file.txt" \'destination folder/\' --force'
      );
      expect(result.command).toBe('mv');
      expect(result.args).toEqual(['my file.txt', 'destination folder/', '--force']);
    });

    it('should handle trailing whitespace', () => {
      const result = parser.parseCommandLine('ls arg1 arg2   ');
      expect(result.command).toBe('ls');
      expect(result.args).toEqual(['arg1', 'arg2']);
    });

    it('should handle leading whitespace', () => {
      const result = parser.parseCommandLine('   ls arg1 arg2');
      expect(result.command).toBe('ls');
      expect(result.args).toEqual(['arg1', 'arg2']);
    });
  });

  describe('parseArguments', () => {
    it('should provide token information', () => {
      const result = parser.parseArguments('cmd "arg 1" arg2');

      expect(result.args).toEqual(['cmd', 'arg 1', 'arg2']);
      expect(result.tokens).toHaveLength(3);

      expect(result.tokens[0].value).toBe('cmd');
      expect(result.tokens[0].quoted).toBe(false);

      expect(result.tokens[1].value).toBe('arg 1');
      expect(result.tokens[1].quoted).toBe(true);
      expect(result.tokens[1].quoteChar).toBe('"');

      expect(result.tokens[2].value).toBe('arg2');
      expect(result.tokens[2].quoted).toBe(false);
    });

    it('should track token positions', () => {
      const result = parser.parseArguments('cmd arg1 arg2');

      expect(result.tokens[0].startIndex).toBe(0);
      expect(result.tokens[0].endIndex).toBe(2);

      expect(result.tokens[1].startIndex).toBe(4);
      expect(result.tokens[1].endIndex).toBe(7);

      expect(result.tokens[2].startIndex).toBe(9);
      expect(result.tokens[2].endIndex).toBe(12);
    });
  });

  describe('getPartialArg', () => {
    it('should get partial argument at cursor position', () => {
      const result = parser.getPartialArg('cmd arg1 arg2', 9);
      expect(result.value).toBe('arg1');
      expect(result.quoted).toBe(false);
    });

    it('should get partial argument in quotes', () => {
      const result = parser.getPartialArg('cmd "arg 1" arg2', 10);
      expect(result.value).toBe('arg 1');
      expect(result.quoted).toBe(true);
      expect(result.quoteChar).toBe('"');
    });

    it('should handle cursor at start of new argument', () => {
      const result = parser.getPartialArg('cmd arg1 ', 9);
      expect(result.value).toBe('');
      expect(result.quoted).toBe(false);
    });

    it('should handle cursor in the middle of argument', () => {
      const result = parser.getPartialArg('cmd argument', 7);
      expect(result.value).toBe('argumen');
    });
  });

  describe('quoteIfNeeded', () => {
    it('should not quote simple strings', () => {
      expect(parser.quoteIfNeeded('simple')).toBe('simple');
      expect(parser.quoteIfNeeded('simple-file.txt')).toBe('simple-file.txt');
    });

    it('should quote strings with spaces', () => {
      expect(parser.quoteIfNeeded('file name.txt')).toBe("'file name.txt'");
    });

    it('should quote strings with tabs', () => {
      expect(parser.quoteIfNeeded('file\tname.txt')).toBe("'file\tname.txt'");
    });

    it('should use double quotes if string contains single quotes', () => {
      expect(parser.quoteIfNeeded("it's a file")).toBe('"it\'s a file"');
    });

    it('should escape double quotes when using double quotes', () => {
      expect(parser.quoteIfNeeded('say "hello"')).toBe("'say \"hello\"'");
    });

    it('should handle strings with both quote types', () => {
      const result = parser.quoteIfNeeded('it\'s "quoted"');
      // Should use double quotes and escape internal double quotes
      expect(result).toBe('"it\'s \\"quoted\\""');
    });

    it('should quote strings with special characters', () => {
      expect(parser.quoteIfNeeded('file*.txt')).toBe("'file*.txt'");
      expect(parser.quoteIfNeeded('file?.txt')).toBe("'file?.txt'");
      expect(parser.quoteIfNeeded('file[1].txt')).toBe("'file[1].txt'");
      expect(parser.quoteIfNeeded('$variable')).toBe("'$variable'");
    });

    it('should quote if forceQuote is true', () => {
      expect(parser.quoteIfNeeded('simple', true)).toBe("'simple'");
    });
  });

  describe('replaceArgAtCursor', () => {
    it('should replace simple argument', () => {
      const result = parser.replaceArgAtCursor('cmd arg1 arg2', 9, 'newarg');
      expect(result.newCommandLine).toBe('cmd newarg arg2');
      expect(result.newCursorPosition).toBe(11); // After 'newarg '
    });

    it('should replace argument with quoted value if needed', () => {
      const result = parser.replaceArgAtCursor('cmd arg1 arg2', 9, 'new arg');
      expect(result.newCommandLine).toBe("cmd 'new arg' arg2");
      expect(result.newCursorPosition).toBe(14); // After "'new arg' "
    });

    it('should replace quoted argument', () => {
      const result = parser.replaceArgAtCursor('cmd "old arg" arg2', 10, 'new value');
      expect(result.newCommandLine).toBe("cmd 'new value' arg2");
    });

    it('should handle replacement at end of line', () => {
      const result = parser.replaceArgAtCursor('cmd arg', 7, 'newarg');
      expect(result.newCommandLine).toBe('cmd newarg ');
    });

    it('should handle replacement without adding space', () => {
      const result = parser.replaceArgAtCursor('cmd arg1 arg2', 9, 'newarg', false);
      expect(result.newCommandLine).toBe('cmd newargarg2');
    });

    it('should handle appending when cursor is at empty position', () => {
      const result = parser.replaceArgAtCursor('cmd ', 4, 'arg');
      expect(result.newCommandLine).toBe('cmd arg ');
    });
  });

  describe('edge cases', () => {
    it('should handle unclosed quotes gracefully', () => {
      // Unclosed quote is treated as part of the argument
      const result = parser.parseCommandLine('cmd "unclosed');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(['unclosed']);
    });

    it('should handle escape at end of string', () => {
      const result = parser.parseCommandLine('cmd arg\\');
      expect(result.command).toBe('cmd');
      // Trailing backslash escapes nothing
      expect(result.args).toEqual(['arg\\']);
    });

    it('should handle consecutive quotes', () => {
      const result = parser.parseCommandLine('cmd ""\'\'');
      expect(result.command).toBe('cmd');
      expect(result.args).toEqual(['', '']);
    });

    it('should handle adjacent quotes and text', () => {
      // When quotes are adjacent to text, they concatenate
      const result = parser.parseCommandLine('cmd prefix"quoted"suffix');
      expect(result.command).toBe('cmd');
      // The behavior here is to concatenate everything as one arg
      expect(result.args).toEqual(['prefixquotedsuffix']);
    });
  });

  describe('real-world scenarios', () => {
    it('should handle file paths with spaces', () => {
      const result = parser.parseCommandLine('cat "/home/user/My Documents/file.txt"');
      expect(result.command).toBe('cat');
      expect(result.args).toEqual(['/home/user/My Documents/file.txt']);
    });

    it('should handle complex mv command', () => {
      const result = parser.parseCommandLine(
        'mv "old file.txt" "new folder/new file.txt"'
      );
      expect(result.command).toBe('mv');
      expect(result.args).toEqual(['old file.txt', 'new folder/new file.txt']);
    });

    it('should handle grep with quoted pattern', () => {
      const result = parser.parseCommandLine('grep "search pattern" file.txt');
      expect(result.command).toBe('grep');
      expect(result.args).toEqual(['search pattern', 'file.txt']);
    });

    it('should handle echo with mixed quotes', () => {
      const result = parser.parseCommandLine('echo "Hello, \'World\'"');
      expect(result.command).toBe('echo');
      expect(result.args).toEqual(["Hello, 'World'"]);
    });

    it('should handle find command with escaped characters', () => {
      const result = parser.parseCommandLine('find . -name "*.txt"');
      expect(result.command).toBe('find');
      expect(result.args).toEqual(['.', '-name', '*.txt']);
    });
  });
});
