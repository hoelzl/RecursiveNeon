/**
 * Window component - Draggable and resizable window container
 */

import { Rnd } from 'react-rnd';
import { useGameStore } from '../stores/gameStore';
import { WindowState } from '../types';

interface WindowProps {
  window: WindowState;
}

export function Window({ window }: WindowProps) {
  const { closeWindow, minimizeWindow, focusWindow, updateWindow } = useGameStore();

  const handleDragStop = (_e: any, data: { x: number; y: number }) => {
    updateWindow(window.id, {
      position: { x: data.x, y: data.y },
    });
  };

  const handleResizeStop = (
    _e: any,
    _direction: any,
    ref: HTMLElement,
    _delta: any,
    position: { x: number; y: number }
  ) => {
    updateWindow(window.id, {
      size: {
        width: ref.offsetWidth,
        height: ref.offsetHeight,
      },
      position,
    });
  };

  if (window.minimized) {
    return null;
  }

  return (
    <Rnd
      size={{ width: window.size.width, height: window.size.height }}
      position={{ x: window.position.x, y: window.position.y }}
      onDragStop={handleDragStop}
      onResizeStop={handleResizeStop}
      minWidth={300}
      minHeight={200}
      bounds="parent"
      dragHandleClassName="window-titlebar"
      style={{ zIndex: window.zIndex }}
    >
      <div
        className="window"
        style={{ width: '100%', height: '100%' }}
        onMouseDown={() => focusWindow(window.id)}
      >
        <div className="window-titlebar" onMouseDown={() => focusWindow(window.id)}>
          <div className="window-title">{window.title}</div>
          <div className="window-controls">
            <button
              className="window-control-btn"
              onClick={() => minimizeWindow(window.id)}
              title="Minimize"
            >
              −
            </button>
            <button
              className="window-control-btn close"
              onClick={() => closeWindow(window.id)}
              title="Close"
            >
              ×
            </button>
          </div>
        </div>
        <div className="window-content">{window.content}</div>
      </div>
    </Rnd>
  );
}
