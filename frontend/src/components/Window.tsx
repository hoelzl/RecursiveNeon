/**
 * Window component - Draggable window container
 */

import { useRef } from 'react';
import Draggable from 'react-draggable';
import { useGameStore } from '../stores/gameStore';
import { WindowState } from '../types';

interface WindowProps {
  window: WindowState;
}

export function Window({ window }: WindowProps) {
  const nodeRef = useRef(null);
  const { closeWindow, minimizeWindow, focusWindow, updateWindow } = useGameStore();

  const handleDragStop = (_e: any, data: { x: number; y: number }) => {
    updateWindow(window.id, {
      position: { x: data.x, y: data.y },
    });
  };

  if (window.minimized) {
    return null;
  }

  return (
    <Draggable
      nodeRef={nodeRef}
      handle=".window-titlebar"
      position={window.position}
      onStop={handleDragStop}
    >
      <div
        ref={nodeRef}
        className="window"
        style={{
          width: window.size.width,
          height: window.size.height,
          zIndex: window.zIndex,
        }}
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
    </Draggable>
  );
}
