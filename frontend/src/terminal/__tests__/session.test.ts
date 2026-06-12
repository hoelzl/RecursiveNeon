import { beforeEach, describe, expect, it } from 'vitest';

import type { ClientMessage, ServerMessage } from '../protocol';
import { TerminalSession, normalizeNewlines } from '../session';
import type { KeyEventLike } from '../keys';

const ESC = '';

function key(k: string, mods: Partial<KeyEventLike> = {}): KeyEventLike {
  return { key: k, ctrlKey: false, altKey: false, metaKey: false, ...mods };
}

describe('TerminalSession', () => {
  let written: string[];
  let sent: ClientMessage[];
  let session: TerminalSession;

  beforeEach(() => {
    written = [];
    sent = [];
    session = new TerminalSession(
      { write: (d) => written.push(d) },
      (m) => sent.push(m),
    );
  });

  function serve(msg: ServerMessage): void {
    session.handleServer(msg);
  }

  function output(): string {
    return written.join('');
  }

  it('normalizes newlines for the terminal', () => {
    expect(normalizeNewlines('a\nb\r\nc')).toBe('a\r\nb\r\nc');
  });

  it('appends output text in cooked mode', () => {
    serve({ type: 'output', text: 'hello\nworld\n' });
    expect(output()).toBe('hello\r\nworld\r\n');
  });

  it('prompt starts the line editor', () => {
    serve({ type: 'prompt', text: 'neon$ ' });
    expect(output()).toContain('neon$ ');
    expect(session.editor.active).toBe(true);
  });

  it('typing then Enter sends an input message', () => {
    serve({ type: 'prompt', text: '$ ' });
    for (const ch of 'echo hi') {
      session.handleKeyEvent(key(ch));
    }
    session.handleKeyEvent(key('Enter'));
    expect(sent).toContainEqual({ type: 'input', line: 'echo hi' });
  });

  it('Tab round-trips through complete/completions', () => {
    serve({ type: 'prompt', text: '$ ' });
    for (const ch of 'cat fi') {
      session.handleKeyEvent(key(ch));
    }
    session.handleKeyEvent(key('Tab'));
    expect(sent).toContainEqual({ type: 'complete', line: 'cat fi' });
    serve({ type: 'completions', items: ['file.txt'], replace: 2 });
    expect(session.editor.buffer).toBe('cat file.txt');
  });

  it('C-c cancels the line and re-issues the prompt locally', () => {
    serve({ type: 'prompt', text: '$ ' });
    session.handleKeyEvent(key('x'));
    session.handleKeyEvent(key('c', { ctrlKey: true }));
    expect(output()).toContain('^C');
    expect(session.editor.buffer).toBe('');
    expect(session.editor.active).toBe(true);
    expect(sent.filter((m) => m.type === 'input')).toHaveLength(0);
  });

  it('mode raw switches to the alternate screen', () => {
    serve({ type: 'mode', mode: 'raw' });
    expect(session.mode).toBe('raw');
    expect(output()).toContain(`${ESC}[?1049h`);
  });

  it('raw mode forwards every key as a key message', () => {
    serve({ type: 'mode', mode: 'raw' });
    session.handleKeyEvent(key('a'));
    session.handleKeyEvent(key('x', { ctrlKey: true }));
    session.handleKeyEvent(key('ArrowUp'));
    session.handleKeyEvent(key('s', { ctrlKey: true })); // C-s reaches the app
    expect(sent).toEqual([
      { type: 'key', key: 'a' },
      { type: 'key', key: 'C-x' },
      { type: 'key', key: 'ArrowUp' },
      { type: 'key', key: 'C-s' },
    ]);
  });

  it('renders screen frames with cursor positioning', () => {
    serve({ type: 'mode', mode: 'raw' });
    written.length = 0;
    serve({
      type: 'screen',
      lines: ['row one', 'row two'],
      cursor: [1, 3],
      cursor_visible: true,
    });
    const frame = output();
    expect(frame).toContain(`${ESC}[2J`);
    expect(frame).toContain(`${ESC}[1;1Hrow one`);
    expect(frame).toContain(`${ESC}[2;1Hrow two`);
    expect(frame).toContain(`${ESC}[2;4H`); // cursor at row 1, col 3 (1-based)
    expect(frame).toContain(`${ESC}[?25h`); // cursor visible
  });

  it('hides the cursor when the frame says so', () => {
    serve({ type: 'mode', mode: 'raw' });
    written.length = 0;
    serve({
      type: 'screen',
      lines: ['x'],
      cursor: [0, 0],
      cursor_visible: false,
    });
    const frame = output();
    expect(frame).toContain(`${ESC}[?25l`);
    expect(frame.endsWith(`${ESC}[?25h`)).toBe(false);
  });

  it('mode cooked leaves the alternate screen', () => {
    serve({ type: 'mode', mode: 'raw' });
    serve({ type: 'mode', mode: 'cooked' });
    expect(session.mode).toBe('cooked');
    expect(output()).toContain(`${ESC}[?1049l`);
  });

  it('resize sends width/height', () => {
    session.handleResize(120, 40);
    expect(sent).toContainEqual({ type: 'resize', width: 120, height: 40 });
  });

  it('paste types into the editor in cooked mode', () => {
    serve({ type: 'prompt', text: '$ ' });
    session.handlePaste('ls\nDocuments');
    expect(session.editor.buffer).toBe('ls Documents');
  });

  it('paste forwards keys in raw mode', () => {
    serve({ type: 'mode', mode: 'raw' });
    session.handlePaste('hi\n');
    expect(sent).toEqual([
      { type: 'key', key: 'h' },
      { type: 'key', key: 'i' },
      { type: 'key', key: 'Enter' },
    ]);
  });

  it('exit message ends the session and ignores further keys', () => {
    serve({ type: 'exit' });
    expect(session.exited).toBe(true);
    expect(output()).toContain('[Session ended]');
    session.handleKeyEvent(key('a'));
    expect(sent).toEqual([]);
  });

  it('error messages render in red', () => {
    serve({ type: 'error', message: 'bad message' });
    expect(output()).toContain('bad message');
    expect(output()).toContain(`${ESC}[31m`);
  });
});
