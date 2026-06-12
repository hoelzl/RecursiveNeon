/**
 * DOM keyboard events → protocol key strings.
 *
 * The backend's raw-mode key encoding (backend/src/recursive_neon/
 * shell/keys.py) names keys the way DOM `KeyboardEvent.key` already
 * does ("ArrowUp", "Enter", "Backspace", …), with Emacs-style modifier
 * prefixes: "C-x" (Ctrl), "M-f" (Alt/Meta), "C-M-v" (both). Printable
 * characters are sent as themselves; `key` carries the shifted value,
 * so Shift needs no prefix.
 */

export interface KeyEventLike {
  key: string;
  ctrlKey: boolean;
  altKey: boolean;
  metaKey: boolean;
}

/** Named keys the protocol understands verbatim. */
const NAMED_KEYS = new Set([
  'Enter',
  'Tab',
  'Backspace',
  'Escape',
  'Delete',
  'Insert',
  'Home',
  'End',
  'PageUp',
  'PageDown',
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'F1',
  'F2',
  'F3',
  'F4',
]);

/** Bare modifier presses and keys the protocol has no name for. */
const IGNORED_KEYS = new Set([
  'Shift',
  'Control',
  'Alt',
  'Meta',
  'AltGraph',
  'CapsLock',
  'NumLock',
  'ScrollLock',
  'ContextMenu',
  'Dead',
  'Unidentified',
]);

/**
 * Encode a keyboard event as a protocol key string, or null when the
 * event should be ignored (bare modifiers, unsupported function keys).
 */
export function encodeKey(ev: KeyEventLike): string | null {
  if (IGNORED_KEYS.has(ev.key)) {
    return null;
  }

  const named = NAMED_KEYS.has(ev.key);
  const printable = !named && ev.key.length === 1;
  if (!named && !printable) {
    return null; // F5+, media keys, …
  }

  const ctrl = ev.ctrlKey;
  // Browsers report the macOS Command key as metaKey; treat it like
  // Meta so M-x works on every platform.
  const meta = ev.altKey || ev.metaKey;

  if (!ctrl && !meta) {
    return ev.key;
  }

  let base = ev.key;
  if (printable) {
    if (base === ' ') {
      base = 'space'; // keys.py: NUL → "C-space"
    } else if (ctrl) {
      // Ctrl chords are case-insensitive at the terminal level;
      // keys.py decodes control bytes to lowercase letters.
      base = base.toLowerCase();
    }
  }

  let prefix = '';
  if (ctrl) prefix += 'C-';
  if (meta) prefix += 'M-';
  return prefix + base;
}
