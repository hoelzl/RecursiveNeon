/**
 * Output renderer for terminal
 * Converts styled text into CSS styles
 */

import React from 'react';
import { TextStyle, OutputLine, StyledSpan } from '../types';
import { AnsiParser } from './AnsiParser';

export class OutputRenderer {
  private ansiParser: AnsiParser;

  constructor() {
    this.ansiParser = new AnsiParser();
  }

  /**
   * Parse a line and return styled spans
   */
  parseLine(line: OutputLine): StyledSpan[] {
    // If the line already has parsed spans, use them
    if (line.spans && line.spans.length > 0) {
      return line.spans;
    }

    // Check if content has ANSI codes
    if (this.ansiParser.hasAnsiCodes(line.content)) {
      return this.ansiParser.parse(line.content);
    }

    // No ANSI codes, return single span with line style
    return [
      {
        text: line.content,
        style: line.style || {},
      },
    ];
  }

  /**
   * Build CSS styles from TextStyle
   */
  buildStyles(style: TextStyle): React.CSSProperties {
    const cssStyle: React.CSSProperties = {};

    if (style.color) {
      cssStyle.color = style.color;
    }

    if (style.backgroundColor) {
      cssStyle.backgroundColor = style.backgroundColor;
    }

    if (style.bold) {
      cssStyle.fontWeight = 'bold';
    }

    if (style.italic) {
      cssStyle.fontStyle = 'italic';
    }

    if (style.underline && style.strikethrough) {
      cssStyle.textDecoration = 'underline line-through';
    } else if (style.underline) {
      cssStyle.textDecoration = 'underline';
    } else if (style.strikethrough) {
      cssStyle.textDecoration = 'line-through';
    }

    if (style.dim) {
      cssStyle.opacity = 0.6;
    }

    if (style.inverse) {
      // Swap foreground and background
      const fg = style.color || 'var(--terminal-fg)';
      const bg = style.backgroundColor || 'var(--terminal-bg)';
      cssStyle.color = bg;
      cssStyle.backgroundColor = fg;
    }

    if (style.blink) {
      cssStyle.animation = 'terminal-blink 1s infinite';
    }

    return cssStyle;
  }

  /**
   * Get line color based on type
   */
  getLineTypeColor(type: string): string | undefined {
    switch (type) {
      case 'error':
        return 'var(--terminal-error, #ff5555)';
      case 'system':
        return 'var(--terminal-system, #ffcc00)';
      case 'input':
        return 'var(--terminal-input, var(--terminal-fg))';
      default:
        return undefined;
    }
  }
}
