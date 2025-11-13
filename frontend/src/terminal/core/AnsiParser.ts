/**
 * ANSI escape code parser
 * Parses ANSI color codes and text formatting
 */

import { TextStyle, StyledSpan } from '../types';

// ANSI color mapping (standard 16 colors)
const ansiColors = [
  // Normal colors (30-37, 40-47)
  '#000000', // 0: Black
  '#cd3131', // 1: Red
  '#0dbc79', // 2: Green
  '#e5e510', // 3: Yellow
  '#2472c8', // 4: Blue
  '#bc3fbc', // 5: Magenta
  '#11a8cd', // 6: Cyan
  '#e5e5e5', // 7: White
  // Bright colors (90-97, 100-107)
  '#666666', // 8: Bright Black
  '#f14c4c', // 9: Bright Red
  '#23d18b', // 10: Bright Green
  '#f5f543', // 11: Bright Yellow
  '#3b8eea', // 12: Bright Blue
  '#d670d6', // 13: Bright Magenta
  '#29b8db', // 14: Bright Cyan
  '#ffffff', // 15: Bright White
];

export class AnsiParser {
  /**
   * Parse ANSI escape sequences and return styled spans
   */
  parse(text: string): StyledSpan[] {
    const spans: StyledSpan[] = [];
    let currentStyle: TextStyle = {};
    let currentText = '';

    // Remove or parse ANSI codes
    const ansiRegex = /\x1b\[([0-9;]*)m/g;
    let lastIndex = 0;
    let match;

    while ((match = ansiRegex.exec(text)) !== null) {
      // Add text before the ANSI code
      if (match.index > lastIndex) {
        currentText += text.substring(lastIndex, match.index);
      }

      // Parse the ANSI code
      const codes = match[1].split(';').map((c) => parseInt(c, 10) || 0);
      currentStyle = this.applyAnsiCodes(codes, currentStyle);

      // If we have accumulated text, add it as a span
      if (currentText) {
        spans.push({
          text: currentText,
          style: { ...currentStyle },
        });
        currentText = '';
      }

      lastIndex = ansiRegex.lastIndex;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      currentText += text.substring(lastIndex);
    }

    if (currentText) {
      spans.push({
        text: currentText,
        style: { ...currentStyle },
      });
    }

    // If no ANSI codes found, return the whole text as one span
    if (spans.length === 0) {
      spans.push({
        text: text,
        style: {},
      });
    }

    return spans;
  }

  /**
   * Apply ANSI codes to the current style
   */
  private applyAnsiCodes(codes: number[], currentStyle: TextStyle): TextStyle {
    const style = { ...currentStyle };

    for (const code of codes) {
      if (code === 0) {
        // Reset all
        return {};
      } else if (code === 1) {
        style.bold = true;
      } else if (code === 2) {
        style.dim = true;
      } else if (code === 3) {
        style.italic = true;
      } else if (code === 4) {
        style.underline = true;
      } else if (code === 5 || code === 6) {
        style.blink = true;
      } else if (code === 7) {
        style.inverse = true;
      } else if (code === 9) {
        style.strikethrough = true;
      } else if (code === 22) {
        style.bold = false;
        style.dim = false;
      } else if (code === 23) {
        style.italic = false;
      } else if (code === 24) {
        style.underline = false;
      } else if (code === 25) {
        style.blink = false;
      } else if (code === 27) {
        style.inverse = false;
      } else if (code === 29) {
        style.strikethrough = false;
      } else if (code >= 30 && code <= 37) {
        // Foreground color
        style.color = ansiColors[code - 30];
      } else if (code === 39) {
        // Default foreground color
        delete style.color;
      } else if (code >= 40 && code <= 47) {
        // Background color
        style.backgroundColor = ansiColors[code - 40];
      } else if (code === 49) {
        // Default background color
        delete style.backgroundColor;
      } else if (code >= 90 && code <= 97) {
        // Bright foreground color
        style.color = ansiColors[code - 90 + 8];
      } else if (code >= 100 && code <= 107) {
        // Bright background color
        style.backgroundColor = ansiColors[code - 100 + 8];
      }
    }

    return style;
  }

  /**
   * Strip ANSI codes from text
   */
  strip(text: string): string {
    return text.replace(/\x1b\[[0-9;]*m/g, '');
  }

  /**
   * Check if text contains ANSI codes
   */
  hasAnsiCodes(text: string): boolean {
    return /\x1b\[[0-9;]*m/.test(text);
  }
}
