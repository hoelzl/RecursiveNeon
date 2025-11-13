/**
 * Terminal output display component
 * Renders the output buffer with proper styling
 */

import React, { useEffect, useRef } from 'react';
import { OutputLine } from '../../terminal/types';
import { OutputRenderer } from '../../terminal/core/OutputRenderer';

interface TerminalOutputProps {
  lines: OutputLine[];
  currentApp?: any; // TerminalApplication
}

const renderer = new OutputRenderer();

export function TerminalOutput({ lines, currentApp }: TerminalOutputProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new lines are added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines.length]);

  // If there's a current app, render its output instead
  if (currentApp) {
    const appOutput = currentApp.render();
    return (
      <div className="terminal-output" ref={scrollRef}>
        <pre className="terminal-app-output">{appOutput}</pre>
      </div>
    );
  }

  return (
    <div className="terminal-output" ref={scrollRef}>
      {lines.map((line) => {
        const spans = renderer.parseLine(line);

        return (
          <div key={line.id} className={`terminal-line terminal-line-${line.type}`}>
            {spans.map((span, index) => {
              const style = renderer.buildStyles(span.style);
              const color = renderer.getLineTypeColor(line.type);

              return (
                <span
                  key={index}
                  style={{
                    ...style,
                    color: style.color || color || 'inherit',
                  }}
                >
                  {span.text}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
