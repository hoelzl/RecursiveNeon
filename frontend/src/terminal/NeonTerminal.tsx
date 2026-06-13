/**
 * NeonTerminal — xterm.js bound to the /ws/terminal protocol.
 *
 * The component owns the I/O plumbing only; all protocol behaviour
 * (cooked line editing, raw-mode frames, mode switching) lives in
 * TerminalSession, which is unit-tested without a browser.
 *
 * Keyboard handling: every keydown is encoded and fed to the session
 * (xterm's own input processing is bypassed), so the in-game shell and
 * TUI apps see the same key names the CLI client sends. Pasted text
 * still arrives through onData. Like a real terminal, chords the apps
 * use (C-v, C-p, …) are claimed from the browser; use Ctrl+Shift+V to
 * paste.
 */

import { useEffect, useRef } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

import { TerminalSession } from './session';
import { encodeKey } from './keys';
import type { ServerMessage } from './protocol';

const THEME = {
  background: '#0a0e14',
  foreground: '#b3f0c8',
  cursor: '#00ff9c',
  cursorAccent: '#0a0e14',
  selectionBackground: '#1f3d2e',
  black: '#0a0e14',
  red: '#ff5f56',
  green: '#00ff9c',
  yellow: '#ffd866',
  blue: '#56c9ff',
  magenta: '#ff7ae0',
  cyan: '#43e8d8',
  white: '#d8e8df',
  brightBlack: '#3a4a42',
  brightRed: '#ff8a80',
  brightGreen: '#7dffc4',
  brightYellow: '#ffe9a3',
  brightBlue: '#9adfff',
  brightMagenta: '#ffb1ec',
  brightCyan: '#8cf2e7',
  brightWhite: '#f4fff8',
};

export function NeonTerminal() {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: '"Cascadia Mono", "Fira Code", "DejaVu Sans Mono", monospace',
      fontSize: 15,
      theme: THEME,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(container);
    fit.fit();

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/terminal`);
    const session = new TerminalSession(
      { write: (data) => term.write(data) },
      (msg) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify(msg));
        }
      },
    );

    ws.onopen = () => {
      // Resize-on-connect: the server sizes the session from the first
      // resize message (same as the CLI client).
      session.handleResize(term.cols, term.rows);
    };
    ws.onmessage = (event) => {
      session.handleServer(JSON.parse(event.data as string) as ServerMessage);
    };
    ws.onclose = () => {
      if (!session.exited) {
        term.write('\r\n[Connection closed]\r\n');
      }
    };
    ws.onerror = () => {
      term.write('\r\n[Connection error]\r\n');
    };

    term.attachCustomKeyEventHandler((ev) => {
      if (ev.type !== 'keydown') {
        return false;
      }
      if (encodeKey(ev) !== null) {
        ev.preventDefault();
        session.handleKeyEvent(ev);
      }
      return false; // never let xterm double-process keys
    });
    const dataSub = term.onData((data) => session.handlePaste(data));

    const resizeSub = term.onResize(({ cols, rows }) =>
      session.handleResize(cols, rows),
    );
    const observer = new ResizeObserver(() => fit.fit());
    observer.observe(container);

    term.focus();

    return () => {
      observer.disconnect();
      dataSub.dispose();
      resizeSub.dispose();
      ws.close();
      term.dispose();
    };
  }, []);

  return <div ref={containerRef} className="neon-terminal" />;
}
