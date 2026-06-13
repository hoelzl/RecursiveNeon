/**
 * TerminalSession — the protocol brain of the browser terminal.
 *
 * Sits between a terminal surface (xterm.js in production, a fake in
 * tests) and the /ws/terminal transport. Cooked mode appends output
 * and runs the local line editor; raw mode switches to the alternate
 * screen and renders full `screen` frames, forwarding every keystroke.
 *
 * No xterm.js or WebSocket imports here — both sides are injected, so
 * the whole protocol flow is unit-testable
 * (src/terminal/__tests__/session.test.ts).
 */

import type { ClientMessage, ServerMessage } from './protocol';
import { encodeKey, type KeyEventLike } from './keys';
import { LineEditor, type EditorAction } from './lineEditor';

export interface TerminalIO {
  write(data: string): void;
}

const ESC = '\u001b';
const ALT_SCREEN_ON = `${ESC}[?1049h${ESC}[2J${ESC}[H`;
const ALT_SCREEN_OFF = `${ESC}[?25h${ESC}[?1049l`;
const HIDE_CURSOR = `${ESC}[?25l`;
const SHOW_CURSOR = `${ESC}[?25h`;

/** The server emits bare \n; terminals need \r\n. */
export function normalizeNewlines(text: string): string {
  return text.replace(/\r?\n/g, '\r\n');
}

export class TerminalSession {
  mode: 'cooked' | 'raw' = 'cooked';
  exited = false;
  readonly editor = new LineEditor();

  constructor(
    private readonly io: TerminalIO,
    private readonly sendMessage: (msg: ClientMessage) => void,
  ) {}

  // ── Server → terminal ────────────────────────────────────────────

  handleServer(msg: ServerMessage): void {
    switch (msg.type) {
      case 'output':
        this.io.write(normalizeNewlines(msg.text));
        break;
      case 'prompt':
        this.io.write(this.editor.start(msg.text));
        break;
      case 'completions':
        this.applyAction(this.editor.applyCompletions(msg.items, msg.replace));
        break;
      case 'mode':
        if (msg.mode === 'raw' && this.mode !== 'raw') {
          this.mode = 'raw';
          this.editor.active = false;
          this.io.write(ALT_SCREEN_ON);
        } else if (msg.mode === 'cooked' && this.mode !== 'cooked') {
          this.mode = 'cooked';
          this.io.write(ALT_SCREEN_OFF);
        }
        break;
      case 'screen':
        this.renderScreen(msg.lines, msg.cursor, msg.cursor_visible);
        break;
      case 'exit':
        this.exited = true;
        if (this.mode === 'raw') {
          this.io.write(ALT_SCREEN_OFF);
        }
        this.io.write('\r\n[Session ended]\r\n');
        break;
      case 'error':
        this.io.write(`\r\n${ESC}[31m${msg.message}${ESC}[0m\r\n`);
        break;
    }
  }

  private renderScreen(
    lines: string[],
    cursor: [number, number],
    cursorVisible: boolean,
  ): void {
    let out = HIDE_CURSOR + `${ESC}[2J${ESC}[H`;
    lines.forEach((line, i) => {
      out += `${ESC}[${i + 1};1H${line}`;
    });
    out += `${ESC}[${cursor[0] + 1};${cursor[1] + 1}H`;
    if (cursorVisible) {
      out += SHOW_CURSOR;
    }
    this.io.write(out);
  }

  // ── Keyboard / paste → server ────────────────────────────────────

  handleKeyEvent(ev: KeyEventLike): void {
    const key = encodeKey(ev);
    if (key === null || this.exited) {
      return;
    }
    if (this.mode === 'raw') {
      this.sendMessage({ type: 'key', key });
      return;
    }
    this.applyAction(this.editor.handleKey(key));
  }

  /** Pasted text: typed into the editor in cooked mode, forwarded one
   * key at a time in raw mode. */
  handlePaste(text: string): void {
    if (this.exited || !text) {
      return;
    }
    if (this.mode === 'raw') {
      for (const ch of text) {
        this.sendMessage({ type: 'key', key: ch === '\n' ? 'Enter' : ch });
      }
      return;
    }
    const printable = text.replace(/[\r\n]+/g, ' ');
    this.applyAction(this.editor.insertText(printable));
  }

  handleResize(cols: number, rows: number): void {
    this.sendMessage({ type: 'resize', width: cols, height: rows });
  }

  private applyAction(action: EditorAction): void {
    if (action.echo) {
      this.io.write(action.echo);
    }
    if (action.submit !== undefined) {
      this.sendMessage({ type: 'input', line: action.submit });
    }
    if (action.complete !== undefined) {
      this.sendMessage({ type: 'complete', line: action.complete });
    }
    if (action.cancel) {
      // bash-style: ^C abandons the line and the prompt returns.
      this.io.write(this.editor.start(this.editor.prompt));
    }
  }
}
