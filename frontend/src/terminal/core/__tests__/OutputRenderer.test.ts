import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OutputRenderer } from '../OutputRenderer';
import type { OutputLine, TextStyle, StyledSpan } from '../../types';

// Mock AnsiParser
vi.mock('../AnsiParser');

describe('OutputRenderer', () => {
  let renderer: OutputRenderer;

  beforeEach(() => {
    renderer = new OutputRenderer();
  });

  describe('Line Parsing', () => {
    it('should use existing spans if available', () => {
      const existingSpans: StyledSpan[] = [
        { text: 'Hello ', style: { color: '#ff0000' } },
        { text: 'World', style: { bold: true } },
      ];

      const line: OutputLine = {
        id: 'line-1',
        content: 'Hello World',
        type: 'output',
        timestamp: Date.now(),
        spans: existingSpans,
      };

      const result = renderer.parseLine(line);

      expect(result).toBe(existingSpans);
    });

    it('should return single span with line style for plain text', () => {
      const line: OutputLine = {
        id: 'line-1',
        content: 'Plain text',
        type: 'output',
        timestamp: Date.now(),
        style: { color: '#00ff00' },
      };

      const result = renderer.parseLine(line);

      expect(result.length).toBe(1);
      expect(result[0].text).toBe('Plain text');
      expect(result[0].style?.color).toBe('#00ff00');
    });

    it('should return empty style for line without style', () => {
      const line: OutputLine = {
        id: 'line-1',
        content: 'No style',
        type: 'output',
        timestamp: Date.now(),
      };

      const result = renderer.parseLine(line);

      expect(result.length).toBe(1);
      expect(result[0].text).toBe('No style');
      expect(result[0].style).toEqual({});
    });
  });

  describe('Style Building', () => {
    it('should build color style', () => {
      const style: TextStyle = { color: '#ff0000' };
      const css = renderer.buildStyles(style);

      expect(css.color).toBe('#ff0000');
    });

    it('should build background color style', () => {
      const style: TextStyle = { backgroundColor: '#0000ff' };
      const css = renderer.buildStyles(style);

      expect(css.backgroundColor).toBe('#0000ff');
    });

    it('should build bold style', () => {
      const style: TextStyle = { bold: true };
      const css = renderer.buildStyles(style);

      expect(css.fontWeight).toBe('bold');
    });

    it('should build italic style', () => {
      const style: TextStyle = { italic: true };
      const css = renderer.buildStyles(style);

      expect(css.fontStyle).toBe('italic');
    });

    it('should build underline style', () => {
      const style: TextStyle = { underline: true };
      const css = renderer.buildStyles(style);

      expect(css.textDecoration).toBe('underline');
    });

    it('should build strikethrough style', () => {
      const style: TextStyle = { strikethrough: true };
      const css = renderer.buildStyles(style);

      expect(css.textDecoration).toBe('line-through');
    });

    it('should combine underline and strikethrough', () => {
      const style: TextStyle = { underline: true, strikethrough: true };
      const css = renderer.buildStyles(style);

      expect(css.textDecoration).toBe('underline line-through');
    });

    it('should build dim style', () => {
      const style: TextStyle = { dim: true };
      const css = renderer.buildStyles(style);

      expect(css.opacity).toBe(0.6);
    });

    it('should build inverse style', () => {
      const style: TextStyle = { inverse: true, color: '#ffffff', backgroundColor: '#000000' };
      const css = renderer.buildStyles(style);

      // Inverse swaps foreground and background
      expect(css.color).toBe('#000000');
      expect(css.backgroundColor).toBe('#ffffff');
    });

    it('should build inverse style with default colors', () => {
      const style: TextStyle = { inverse: true };
      const css = renderer.buildStyles(style);

      // Should use CSS variables when colors not specified
      expect(css.color).toBe('var(--terminal-bg)');
      expect(css.backgroundColor).toBe('var(--terminal-fg)');
    });

    it('should build blink style', () => {
      const style: TextStyle = { blink: true };
      const css = renderer.buildStyles(style);

      expect(css.animation).toBe('terminal-blink 1s infinite');
    });

    it('should combine multiple styles', () => {
      const style: TextStyle = {
        color: '#ff0000',
        backgroundColor: '#000000',
        bold: true,
        italic: true,
        underline: true,
      };
      const css = renderer.buildStyles(style);

      expect(css.color).toBe('#ff0000');
      expect(css.backgroundColor).toBe('#000000');
      expect(css.fontWeight).toBe('bold');
      expect(css.fontStyle).toBe('italic');
      expect(css.textDecoration).toBe('underline');
    });

    it('should return empty object for empty style', () => {
      const style: TextStyle = {};
      const css = renderer.buildStyles(style);

      expect(Object.keys(css).length).toBe(0);
    });

    it('should not set bold when false', () => {
      const style: TextStyle = { bold: false };
      const css = renderer.buildStyles(style);

      expect(css.fontWeight).toBeUndefined();
    });

    it('should not set italic when false', () => {
      const style: TextStyle = { italic: false };
      const css = renderer.buildStyles(style);

      expect(css.fontStyle).toBeUndefined();
    });
  });

  describe('Line Type Colors', () => {
    it('should return error color for error type', () => {
      const color = renderer.getLineTypeColor('error');
      expect(color).toBe('var(--terminal-error, #ff5555)');
    });

    it('should return system color for system type', () => {
      const color = renderer.getLineTypeColor('system');
      expect(color).toBe('var(--terminal-system, #ffcc00)');
    });

    it('should return input color for input type', () => {
      const color = renderer.getLineTypeColor('input');
      expect(color).toBe('var(--terminal-input, var(--terminal-fg))');
    });

    it('should return undefined for output type', () => {
      const color = renderer.getLineTypeColor('output');
      expect(color).toBeUndefined();
    });

    it('should return undefined for unknown type', () => {
      const color = renderer.getLineTypeColor('unknown');
      expect(color).toBeUndefined();
    });

    it('should return undefined for empty type', () => {
      const color = renderer.getLineTypeColor('');
      expect(color).toBeUndefined();
    });
  });

  describe('Edge Cases', () => {
    it('should handle line with empty content', () => {
      const line: OutputLine = {
        id: 'line-1',
        content: '',
        type: 'output',
        timestamp: Date.now(),
      };

      const result = renderer.parseLine(line);

      expect(result.length).toBe(1);
      expect(result[0].text).toBe('');
    });

    it('should handle line with whitespace content', () => {
      const line: OutputLine = {
        id: 'line-1',
        content: '   ',
        type: 'output',
        timestamp: Date.now(),
      };

      const result = renderer.parseLine(line);

      expect(result.length).toBe(1);
      expect(result[0].text).toBe('   ');
    });

    it('should handle line with special characters', () => {
      const line: OutputLine = {
        id: 'line-1',
        content: '<>&"\'',
        type: 'output',
        timestamp: Date.now(),
      };

      const result = renderer.parseLine(line);

      expect(result.length).toBe(1);
      expect(result[0].text).toBe('<>&"\'');
    });

    it('should handle empty spans array', () => {
      const line: OutputLine = {
        id: 'line-1',
        content: 'Content',
        type: 'output',
        timestamp: Date.now(),
        spans: [],
      };

      const result = renderer.parseLine(line);

      // Empty spans array should fall back to parsing content
      expect(result.length).toBeGreaterThan(0);
    });

    it('should handle style with undefined values', () => {
      const style: TextStyle = {
        color: undefined,
        bold: undefined,
        italic: undefined,
      };

      const css = renderer.buildStyles(style);

      // Undefined values should not create CSS properties
      expect(css.color).toBeUndefined();
      expect(css.fontWeight).toBeUndefined();
      expect(css.fontStyle).toBeUndefined();
    });
  });

  describe('Complex Styling Scenarios', () => {
    it('should handle multiple spans with different styles', () => {
      const spans: StyledSpan[] = [
        { text: 'Error: ', style: { color: '#ff0000', bold: true } },
        { text: 'File not found: ', style: { color: '#ffff00' } },
        { text: '/path/to/file', style: { color: '#00ff00', underline: true } },
      ];

      const line: OutputLine = {
        id: 'line-1',
        content: 'Error: File not found: /path/to/file',
        type: 'error',
        timestamp: Date.now(),
        spans,
      };

      const result = renderer.parseLine(line);

      expect(result.length).toBe(3);
      expect(result[0].style?.color).toBe('#ff0000');
      expect(result[0].style?.bold).toBe(true);
      expect(result[1].style?.color).toBe('#ffff00');
      expect(result[2].style?.color).toBe('#00ff00');
      expect(result[2].style?.underline).toBe(true);
    });

    it('should build styles for complex combinations', () => {
      const style: TextStyle = {
        color: '#ff00ff',
        backgroundColor: '#00ffff',
        bold: true,
        italic: true,
        underline: true,
        dim: true,
      };

      const css = renderer.buildStyles(style);

      expect(css.color).toBe('#ff00ff');
      expect(css.backgroundColor).toBe('#00ffff');
      expect(css.fontWeight).toBe('bold');
      expect(css.fontStyle).toBe('italic');
      expect(css.textDecoration).toBe('underline');
      expect(css.opacity).toBe(0.6);
    });

    it('should handle inverse with only foreground color', () => {
      const style: TextStyle = { inverse: true, color: '#ff0000' };
      const css = renderer.buildStyles(style);

      expect(css.color).toBe('var(--terminal-bg)');
      expect(css.backgroundColor).toBe('#ff0000');
    });

    it('should handle inverse with only background color', () => {
      const style: TextStyle = { inverse: true, backgroundColor: '#0000ff' };
      const css = renderer.buildStyles(style);

      expect(css.color).toBe('#0000ff');
      expect(css.backgroundColor).toBe('var(--terminal-fg)');
    });
  });
});
