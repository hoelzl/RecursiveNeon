/**
 * WebSocket terminal protocol types.
 *
 * Mirrors the backend's /ws/terminal message schema exactly
 * (backend/src/recursive_neon/terminal.py); the Python reference client
 * lives in backend/src/recursive_neon/wsclient/.
 */

// ── Server → client ────────────────────────────────────────────────

export interface OutputMessage {
  type: 'output';
  text: string;
}

export interface PromptMessage {
  type: 'prompt';
  text: string;
}

export interface CompletionsMessage {
  type: 'completions';
  items: string[];
  /** How many characters before the cursor the completion replaces. */
  replace: number;
}

export interface ModeMessage {
  type: 'mode';
  mode: 'raw' | 'cooked';
}

export interface ScreenMessage {
  type: 'screen';
  /** Full screen rows, top to bottom; may contain ANSI SGR codes. */
  lines: string[];
  /** [row, col], 0-indexed. */
  cursor: [number, number];
  cursor_visible: boolean;
}

export interface ExitMessage {
  type: 'exit';
}

export interface ErrorMessage {
  type: 'error';
  message: string;
}

export type ServerMessage =
  | OutputMessage
  | PromptMessage
  | CompletionsMessage
  | ModeMessage
  | ScreenMessage
  | ExitMessage
  | ErrorMessage;

// ── Client → server ────────────────────────────────────────────────

export interface InputMessage {
  type: 'input';
  line: string;
}

export interface KeyMessage {
  type: 'key';
  /** Protocol key string: "a", "Enter", "ArrowUp", "C-c", "M-f", … */
  key: string;
}

export interface ResizeMessage {
  type: 'resize';
  width: number;
  height: number;
}

export interface CompleteMessage {
  type: 'complete';
  line: string;
}

export type ClientMessage =
  | InputMessage
  | KeyMessage
  | ResizeMessage
  | CompleteMessage;
