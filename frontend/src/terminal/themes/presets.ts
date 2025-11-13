/**
 * Built-in terminal themes
 */

import { TerminalTheme } from '../types';

export const cyberpunkTheme: TerminalTheme = {
  name: 'Cyberpunk',

  // Base colors
  background: '#0a0e27',
  foreground: '#00ffff',
  cursor: '#ff00ff',
  cursorAccent: '#00ffff',
  selection: 'rgba(0, 255, 255, 0.3)',

  // ANSI colors (0-15)
  black: '#0a0e27',
  red: '#ff0055',
  green: '#00ff9f',
  yellow: '#ffcc00',
  blue: '#0099ff',
  magenta: '#ff00ff',
  cyan: '#00ffff',
  white: '#e0e0e0',
  brightBlack: '#555577',
  brightRed: '#ff5588',
  brightGreen: '#55ffbb',
  brightYellow: '#ffee55',
  brightBlue: '#55bbff',
  brightMagenta: '#ff55ff',
  brightCyan: '#55ffff',
  brightWhite: '#ffffff',

  // Font
  fontFamily: '"Courier New", "Consolas", monospace',
  fontSize: 14,
  lineHeight: 1.5,

  // Cursor
  cursorStyle: 'block',
  cursorBlink: true,

  // Effects
  opacity: 0.95,
  blur: 2,
};

export const matrixTheme: TerminalTheme = {
  name: 'Matrix',

  // Base colors
  background: '#000000',
  foreground: '#00ff00',
  cursor: '#00ff00',
  cursorAccent: '#00ff00',
  selection: 'rgba(0, 255, 0, 0.3)',

  // ANSI colors (0-15)
  black: '#000000',
  red: '#008800',
  green: '#00ff00',
  yellow: '#88ff00',
  blue: '#008800',
  magenta: '#00ff00',
  cyan: '#00ffaa',
  white: '#00ff00',
  brightBlack: '#003300',
  brightRed: '#00aa00',
  brightGreen: '#00ff00',
  brightYellow: '#aaff00',
  brightBlue: '#00aa00',
  brightMagenta: '#00ff00',
  brightCyan: '#00ffcc',
  brightWhite: '#ccffcc',

  // Font
  fontFamily: '"Courier New", "Consolas", monospace',
  fontSize: 14,
  lineHeight: 1.5,

  // Cursor
  cursorStyle: 'block',
  cursorBlink: true,

  // Effects
  opacity: 1.0,
  blur: 0,
};

export const retroTheme: TerminalTheme = {
  name: 'Retro',

  // Base colors
  background: '#000000',
  foreground: '#33ff33',
  cursor: '#33ff33',
  cursorAccent: '#33ff33',
  selection: 'rgba(51, 255, 51, 0.3)',

  // ANSI colors (0-15)
  black: '#000000',
  red: '#ff5555',
  green: '#33ff33',
  yellow: '#ffff55',
  blue: '#5555ff',
  magenta: '#ff55ff',
  cyan: '#55ffff',
  white: '#cccccc',
  brightBlack: '#333333',
  brightRed: '#ff8888',
  brightGreen: '#88ff88',
  brightYellow: '#ffff88',
  brightBlue: '#8888ff',
  brightMagenta: '#ff88ff',
  brightCyan: '#88ffff',
  brightWhite: '#ffffff',

  // Font
  fontFamily: '"Courier New", "Consolas", monospace',
  fontSize: 16,
  lineHeight: 1.4,

  // Cursor
  cursorStyle: 'block',
  cursorBlink: true,

  // Effects
  opacity: 1.0,
  blur: 0,
};

export const falloutTheme: TerminalTheme = {
  name: 'Fallout',

  // Base colors
  background: '#0c0c0c',
  foreground: '#00ff00',
  cursor: '#00ff00',
  cursorAccent: '#00ff00',
  selection: 'rgba(0, 255, 0, 0.3)',

  // ANSI colors (0-15)
  black: '#0c0c0c',
  red: '#00aa00',
  green: '#00ff00',
  yellow: '#88ff00',
  blue: '#008800',
  magenta: '#00ff00',
  cyan: '#00ffaa',
  white: '#00ff00',
  brightBlack: '#004400',
  brightRed: '#00cc00',
  brightGreen: '#00ff00',
  brightYellow: '#aaff00',
  brightBlue: '#00aa00',
  brightMagenta: '#00ff00',
  brightCyan: '#00ffcc',
  brightWhite: '#aaffaa',

  // Font
  fontFamily: '"Courier New", "Consolas", monospace',
  fontSize: 14,
  lineHeight: 1.5,

  // Cursor
  cursorStyle: 'block',
  cursorBlink: false,

  // Effects
  opacity: 1.0,
  blur: 0,
};

export const darkTheme: TerminalTheme = {
  name: 'Dark',

  // Base colors
  background: '#1e1e1e',
  foreground: '#d4d4d4',
  cursor: '#aeafad',
  cursorAccent: '#ffffff',
  selection: 'rgba(255, 255, 255, 0.2)',

  // ANSI colors (0-15) - VS Code Dark+ theme colors
  black: '#000000',
  red: '#cd3131',
  green: '#0dbc79',
  yellow: '#e5e510',
  blue: '#2472c8',
  magenta: '#bc3fbc',
  cyan: '#11a8cd',
  white: '#e5e5e5',
  brightBlack: '#666666',
  brightRed: '#f14c4c',
  brightGreen: '#23d18b',
  brightYellow: '#f5f543',
  brightBlue: '#3b8eea',
  brightMagenta: '#d670d6',
  brightCyan: '#29b8db',
  brightWhite: '#ffffff',

  // Font
  fontFamily: '"Courier New", "Consolas", monospace',
  fontSize: 14,
  lineHeight: 1.5,

  // Cursor
  cursorStyle: 'block',
  cursorBlink: true,

  // Effects
  opacity: 1.0,
  blur: 0,
};

export const themes: Record<string, TerminalTheme> = {
  cyberpunk: cyberpunkTheme,
  matrix: matrixTheme,
  retro: retroTheme,
  fallout: falloutTheme,
  dark: darkTheme,
};

export const defaultTheme = cyberpunkTheme;
