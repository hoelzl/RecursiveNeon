import { beforeEach, describe, expect, it } from 'vitest';

import { LineEditor } from '../lineEditor';

const ESC = '\u001b';

describe('LineEditor', () => {
  let ed: LineEditor;

  beforeEach(() => {
    ed = new LineEditor();
    ed.start('$ ');
  });

  function type(text: string): void {
    for (const ch of text) {
      ed.handleKey(ch);
    }
  }

  it('echoes the prompt on start and activates', () => {
    expect(ed.start('neon$ ')).toBe('neon$ ');
    expect(ed.active).toBe(true);
  });

  it('inserts typed characters and submits on Enter', () => {
    type('ls -la');
    expect(ed.buffer).toBe('ls -la');
    const action = ed.handleKey('Enter');
    expect(action.submit).toBe('ls -la');
    expect(action.echo).toBe('\r\n');
    expect(ed.active).toBe(false);
  });

  it('redraw places the cursor mid-line', () => {
    type('abc');
    ed.handleKey('ArrowLeft');
    expect(ed.cursor).toBe(2);
    expect(ed.redraw()).toBe(`\r${ESC}[K$ abc${ESC}[1D`);
  });

  it('backspace and delete edit around the cursor', () => {
    type('abcd');
    ed.handleKey('ArrowLeft');
    ed.handleKey('Backspace'); // removes "c"
    expect(ed.buffer).toBe('abd');
    ed.handleKey('C-a');
    ed.handleKey('Delete'); // removes "a"
    expect(ed.buffer).toBe('bd');
  });

  it('C-a/C-e/Home/End jump to the line edges', () => {
    type('hello');
    ed.handleKey('C-a');
    expect(ed.cursor).toBe(0);
    ed.handleKey('End');
    expect(ed.cursor).toBe(5);
  });

  it('C-k kills to end, C-u kills the head', () => {
    type('hello world');
    ed.handleKey('C-a');
    for (let i = 0; i < 5; i++) ed.handleKey('ArrowRight');
    ed.handleKey('C-k');
    expect(ed.buffer).toBe('hello');
    type(' again');
    ed.handleKey('C-u');
    expect(ed.buffer).toBe('');
  });

  it('mid-line insertion goes through the cursor position', () => {
    type('ac');
    ed.handleKey('ArrowLeft');
    type('b');
    expect(ed.buffer).toBe('abc');
    expect(ed.cursor).toBe(2);
  });

  it('C-c cancels the line', () => {
    type('rm -rf /');
    const action = ed.handleKey('C-c');
    expect(action.cancel).toBe(true);
    expect(action.echo).toBe('^C\r\n');
    expect(ed.buffer).toBe('');
  });

  describe('history', () => {
    function submit(line: string): void {
      type(line);
      ed.handleKey('Enter');
      ed.start('$ ');
    }

    it('walks back and forward with ArrowUp/ArrowDown', () => {
      submit('first');
      submit('second');
      ed.handleKey('ArrowUp');
      expect(ed.buffer).toBe('second');
      ed.handleKey('ArrowUp');
      expect(ed.buffer).toBe('first');
      ed.handleKey('ArrowDown');
      expect(ed.buffer).toBe('second');
    });

    it('restores the partially-typed line past the newest entry', () => {
      submit('old');
      type('part');
      ed.handleKey('ArrowUp');
      expect(ed.buffer).toBe('old');
      ed.handleKey('ArrowDown');
      expect(ed.buffer).toBe('part');
    });

    it('stays put at the oldest entry', () => {
      submit('only');
      ed.handleKey('ArrowUp');
      ed.handleKey('ArrowUp');
      expect(ed.buffer).toBe('only');
    });

    it('skips blank lines and consecutive duplicates', () => {
      submit('cmd');
      submit('cmd');
      submit('   ');
      ed.handleKey('ArrowUp');
      expect(ed.buffer).toBe('cmd');
      ed.handleKey('ArrowUp');
      expect(ed.buffer).toBe('cmd'); // only one entry recorded
    });
  });

  describe('completion', () => {
    it('Tab requests completion of the text before the cursor', () => {
      type('cat fi');
      const action = ed.handleKey('Tab');
      expect(action.complete).toBe('cat fi');
    });

    it('a single candidate replaces the prefix', () => {
      type('cat fi');
      ed.applyCompletions(['file.txt'], 2);
      expect(ed.buffer).toBe('cat file.txt');
      expect(ed.cursor).toBe(12);
    });

    it('several candidates extend to the common prefix', () => {
      type('no');
      ed.applyCompletions(['note', 'notes-old'], 2);
      expect(ed.buffer).toBe('note');
    });

    it('lists candidates when nothing extends', () => {
      type('note');
      const action = ed.applyCompletions(['note', 'notes-old'], 4);
      expect(ed.buffer).toBe('note');
      expect(action.echo).toContain('note  notes-old');
      expect(action.echo).toContain('$ note'); // re-drawn prompt line
    });

    it('no candidates is a no-op', () => {
      type('zz');
      expect(ed.applyCompletions([], 2)).toEqual({});
    });
  });
});
