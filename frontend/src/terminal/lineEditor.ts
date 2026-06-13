/**
 * Cooked-mode line editor.
 *
 * The /ws/terminal protocol puts line editing on the client (the
 * Python reference client uses prompt_toolkit): the server only sees
 * complete `input` lines and `complete` requests. This is a small
 * readline: insertion point movement, kill commands, history and tab
 * completion, mirroring the bindings the in-game shell's CLI offers.
 *
 * The editor is a pure state machine — `handleKey` returns what to
 * echo / send rather than doing I/O — so it is unit-testable without
 * xterm.js (src/terminal/__tests__/lineEditor.test.ts).
 */

export interface EditorAction {
  /** Terminal output to render (control sequences included). */
  echo?: string;
  /** A finished line the caller should send as an `input` message. */
  submit?: string;
  /** Text the caller should send as a `complete` request. */
  complete?: string;
  /** The line was cancelled (C-c) — caller re-issues the prompt. */
  cancel?: boolean;
}

const CSI = '\u001b[';

export class LineEditor {
  prompt = '';
  buffer = '';
  cursor = 0;
  /** True between a `prompt` message and the line's submission. */
  active = false;

  private history: string[] = [];
  private histIdx = -1; // -1 = not navigating
  private savedInput = '';

  /** Begin editing under *prompt*. Returns the text to echo. */
  start(prompt: string): string {
    this.prompt = prompt;
    this.buffer = '';
    this.cursor = 0;
    this.histIdx = -1;
    this.savedInput = '';
    this.active = true;
    return prompt;
  }

  /** Re-render the whole edit line (prompt + buffer + cursor). */
  redraw(): string {
    let out = `\r${CSI}K` + this.prompt + this.buffer;
    const back = this.buffer.length - this.cursor;
    if (back > 0) {
      out += `${CSI}${back}D`;
    }
    return out;
  }

  /** Insert literal text at the cursor (typing, paste). */
  insertText(text: string): EditorAction {
    if (!text) {
      return {};
    }
    this.buffer =
      this.buffer.slice(0, this.cursor) + text + this.buffer.slice(this.cursor);
    this.cursor += text.length;
    return { echo: this.redraw() };
  }

  /** Handle a protocol-encoded key. */
  handleKey(key: string): EditorAction {
    if (!this.active) {
      return {};
    }
    switch (key) {
      case 'Enter': {
        const line = this.buffer;
        if (line.trim() && this.history[this.history.length - 1] !== line) {
          this.history.push(line);
        }
        this.active = false;
        return { echo: '\r\n', submit: line };
      }
      case 'C-c': {
        this.buffer = '';
        this.cursor = 0;
        this.histIdx = -1;
        return { echo: '^C\r\n', cancel: true };
      }
      case 'Backspace':
        if (this.cursor > 0) {
          this.buffer =
            this.buffer.slice(0, this.cursor - 1) + this.buffer.slice(this.cursor);
          this.cursor -= 1;
          return { echo: this.redraw() };
        }
        return {};
      case 'Delete':
      case 'C-d':
        if (this.cursor < this.buffer.length) {
          this.buffer =
            this.buffer.slice(0, this.cursor) + this.buffer.slice(this.cursor + 1);
          return { echo: this.redraw() };
        }
        return {};
      case 'ArrowLeft':
      case 'C-b':
        if (this.cursor > 0) {
          this.cursor -= 1;
          return { echo: `${CSI}1D` };
        }
        return {};
      case 'ArrowRight':
      case 'C-f':
        if (this.cursor < this.buffer.length) {
          this.cursor += 1;
          return { echo: `${CSI}1C` };
        }
        return {};
      case 'Home':
      case 'C-a':
        this.cursor = 0;
        return { echo: this.redraw() };
      case 'End':
      case 'C-e':
        this.cursor = this.buffer.length;
        return { echo: this.redraw() };
      case 'C-k':
        this.buffer = this.buffer.slice(0, this.cursor);
        return { echo: this.redraw() };
      case 'C-u':
        this.buffer = this.buffer.slice(this.cursor);
        this.cursor = 0;
        return { echo: this.redraw() };
      case 'ArrowUp':
      case 'C-p':
        return this.historyMove(-1);
      case 'ArrowDown':
      case 'C-n':
        return this.historyMove(1);
      case 'Tab':
        return { complete: this.buffer.slice(0, this.cursor) };
      default:
        if (key.length === 1) {
          return this.insertText(key);
        }
        return {}; // unhandled chords are ignored in cooked mode
    }
  }

  /**
   * Apply a `completions` reply: a single candidate replaces the
   * `replace` characters before the cursor; several extend to their
   * common prefix and, when nothing extends, list the candidates.
   * Mirrors the shell's own TAB handler (shell_mode._shell_complete).
   */
  applyCompletions(items: string[], replace: number): EditorAction {
    if (items.length === 0) {
      return {};
    }
    if (items.length === 1) {
      return this.replaceBeforeCursor(replace, items[0]);
    }
    const common = commonPrefix(items);
    if (common.length > replace) {
      return this.replaceBeforeCursor(replace, common);
    }
    const listing = items.join('  ');
    return { echo: '\r\n' + listing + '\r\n' + this.redraw() };
  }

  private replaceBeforeCursor(count: number, text: string): EditorAction {
    const start = Math.max(0, this.cursor - count);
    this.buffer =
      this.buffer.slice(0, start) + text + this.buffer.slice(this.cursor);
    this.cursor = start + text.length;
    return { echo: this.redraw() };
  }

  private historyMove(delta: number): EditorAction {
    if (this.history.length === 0) {
      return {};
    }
    if (this.histIdx === -1) {
      if (delta > 0) {
        return {}; // nothing newer
      }
      this.savedInput = this.buffer;
      this.histIdx = this.history.length;
    }
    const next = this.histIdx + delta;
    if (next < 0) {
      return {};
    }
    if (next >= this.history.length) {
      // Walked past the newest entry — restore what was being typed.
      this.histIdx = -1;
      this.buffer = this.savedInput;
      this.cursor = this.buffer.length;
      return { echo: this.redraw() };
    }
    this.histIdx = next;
    this.buffer = this.history[next];
    this.cursor = this.buffer.length;
    return { echo: this.redraw() };
  }
}

function commonPrefix(items: string[]): string {
  let prefix = items[0];
  for (const item of items.slice(1)) {
    let i = 0;
    while (i < prefix.length && i < item.length && prefix[i] === item[i]) {
      i += 1;
    }
    prefix = prefix.slice(0, i);
  }
  return prefix;
}
