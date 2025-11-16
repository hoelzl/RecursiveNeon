/**
 * Core terminal types and interfaces
 */

import { AppAPI } from '../utils/appApi';

// ============================================================================
// Text Styling
// ============================================================================

export interface TextStyle {
  color?: string;
  backgroundColor?: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  strikethrough?: boolean;
  dim?: boolean;
  inverse?: boolean;
  blink?: boolean;
}

export interface StyledSpan {
  text: string;
  style: TextStyle;
}

// ============================================================================
// Output Lines
// ============================================================================

export type OutputLineType = 'output' | 'error' | 'input' | 'system';

export interface OutputLine {
  id: string;
  content: string;
  style?: TextStyle;
  timestamp: number;
  type: OutputLineType;
  spans?: StyledSpan[]; // For ANSI-parsed content
}

// ============================================================================
// Command System
// ============================================================================

export interface CommandOption {
  flag: string;
  description: string;
  takesValue?: boolean;
}

export interface CommandContext {
  session: any; // TerminalSession (circular dependency, use 'any' for now)
  args: string[];
  options: Map<string, string | boolean>;
  rawInput: string;
  api: AppAPI;
}

export type CommandExecutor = (context: CommandContext) => Promise<void> | void;

export interface CompletionContext {
  session: any; // TerminalSession
  commandLine: string;
  cursorPosition: number;
  api: AppAPI;
  partialArg: string;
}

export type CompletionFunction = (context: CompletionContext) => Promise<string[]> | string[];

export interface Command {
  name: string;
  description: string;
  usage: string;
  options?: CommandOption[];
  execute: CommandExecutor;
  complete?: CompletionFunction;
}

export interface CompletionResult {
  completions: string[];
  prefix: string;
  commonPrefix: string;
  replaceStart?: number;
  replaceEnd?: number;
}

// ============================================================================
// Terminal Applications
// ============================================================================

export interface KeyModifiers {
  ctrl: boolean;
  alt: boolean;
  shift: boolean;
  meta: boolean;
}

export interface TerminalApplication {
  name: string;
  onMount(session: any): Promise<void>; // TerminalSession
  onUnmount(): Promise<void>;
  onKeyPress(key: string, modifiers: KeyModifiers): Promise<boolean>;
  onResize?(width: number, height: number): void;
  render(): string;
}

// ============================================================================
// Terminal Theme
// ============================================================================

export interface TerminalTheme {
  name: string;

  // Base colors
  background: string;
  foreground: string;
  cursor: string;
  cursorAccent: string;
  selection: string;

  // ANSI colors (0-15)
  black: string;
  red: string;
  green: string;
  yellow: string;
  blue: string;
  magenta: string;
  cyan: string;
  white: string;
  brightBlack: string;
  brightRed: string;
  brightGreen: string;
  brightYellow: string;
  brightBlue: string;
  brightMagenta: string;
  brightCyan: string;
  brightWhite: string;

  // Font
  fontFamily: string;
  fontSize: number;
  lineHeight: number;

  // Cursor
  cursorStyle: 'block' | 'underline' | 'bar';
  cursorBlink: boolean;

  // Effects
  opacity: number;
  blur?: number;
}

// ============================================================================
// File System
// ============================================================================

export interface FileStats {
  name: string;
  type: 'file' | 'directory';
  size: number;
  created: string;
  modified: string;
}

export interface PathResolution {
  absolute: string;
  exists: boolean;
  isDirectory: boolean;
}
