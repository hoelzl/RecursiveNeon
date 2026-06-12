import { describe, expect, it } from 'vitest';

import { encodeKey, type KeyEventLike } from '../keys';

function ev(key: string, mods: Partial<KeyEventLike> = {}): KeyEventLike {
  return { key, ctrlKey: false, altKey: false, metaKey: false, ...mods };
}

describe('encodeKey', () => {
  it('passes printable characters through (shift already applied)', () => {
    expect(encodeKey(ev('a'))).toBe('a');
    expect(encodeKey(ev('Z'))).toBe('Z');
    expect(encodeKey(ev(' '))).toBe(' ');
    expect(encodeKey(ev('%'))).toBe('%');
  });

  it('passes named keys through with protocol names', () => {
    for (const k of [
      'Enter',
      'Tab',
      'Backspace',
      'Escape',
      'Delete',
      'Home',
      'End',
      'PageUp',
      'PageDown',
      'ArrowUp',
      'ArrowDown',
      'ArrowLeft',
      'ArrowRight',
      'F1',
    ]) {
      expect(encodeKey(ev(k))).toBe(k);
    }
  });

  it('encodes ctrl chords lowercased', () => {
    expect(encodeKey(ev('x', { ctrlKey: true }))).toBe('C-x');
    expect(encodeKey(ev('C', { ctrlKey: true }))).toBe('C-c');
  });

  it('encodes C-space like the CLI key reader', () => {
    expect(encodeKey(ev(' ', { ctrlKey: true }))).toBe('C-space');
  });

  it('encodes meta chords (Alt and macOS Command alike)', () => {
    expect(encodeKey(ev('x', { altKey: true }))).toBe('M-x');
    expect(encodeKey(ev('f', { metaKey: true }))).toBe('M-f');
    expect(encodeKey(ev('%', { altKey: true }))).toBe('M-%');
  });

  it('encodes combined ctrl-meta chords C-M-', () => {
    expect(encodeKey(ev('v', { ctrlKey: true, altKey: true }))).toBe('C-M-v');
  });

  it('prefixes named keys with modifiers', () => {
    expect(encodeKey(ev('ArrowUp', { altKey: true }))).toBe('M-ArrowUp');
    expect(encodeKey(ev('Enter', { ctrlKey: true }))).toBe('C-Enter');
  });

  it('ignores bare modifier presses', () => {
    for (const k of ['Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'Dead']) {
      expect(encodeKey(ev(k))).toBeNull();
    }
  });

  it('ignores keys the protocol has no name for', () => {
    expect(encodeKey(ev('F5'))).toBeNull();
    expect(encodeKey(ev('F12'))).toBeNull();
    expect(encodeKey(ev('MediaPlayPause'))).toBeNull();
  });
});
