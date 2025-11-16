import React, { useState, useCallback, useReducer, useEffect } from 'react';
import { CircuitBreakerGame, type Difficulty, type Tile, type GameStatus } from './CircuitBreakerGame';
import './circuitbreaker.css';

export function CircuitBreakerApp() {
  const [game, setGame] = useState<CircuitBreakerGame | null>(null);
  const [, forceUpdate] = useReducer(x => x + 1, 0);

  useEffect(() => {
    const newGame = new CircuitBreakerGame('medium');
    newGame.onUpdate = () => forceUpdate();
    setGame(newGame);

    return () => {
      if (newGame) {
        newGame.destroy();
      }
    };
  }, []);

  const startNewGame = useCallback((difficulty: Difficulty) => {
    if (game) {
      game.destroy();
    }

    const newGame = new CircuitBreakerGame(difficulty);
    newGame.onUpdate = () => forceUpdate();
    newGame.startTimer();
    setGame(newGame);
  }, [game]);

  const handleStart = useCallback(() => {
    if (game && game.getState().gameStatus === 'idle') {
      game.startTimer();
    }
  }, [game]);

  const handleTileClick = useCallback((row: number, col: number) => {
    if (!game) return;
    game.rotateTile(row, col);
  }, [game]);

  const handleReset = useCallback(() => {
    if (!game) return;
    game.reset();
  }, [game]);

  if (!game) {
    return <div className="circuit-breaker-loading">Initializing...</div>;
  }

  const state = game.getState();

  return (
    <div className="circuit-breaker-app">
      <GameHeader
        timeRemaining={state.timeRemaining}
        maxTime={state.maxTime}
        moves={state.moves}
        isComplete={state.isComplete}
        gameStatus={state.gameStatus}
        difficulty={state.difficulty}
        onStart={handleStart}
        onReset={handleReset}
        onDifficultyChange={startNewGame}
      />

      <CircuitGrid
        grid={state.grid}
        startPos={state.startPos}
        endPos={state.endPos}
        onTileClick={handleTileClick}
        gameStatus={state.gameStatus}
      />

      {state.gameStatus === 'won' && (
        <GameOverModal
          won={true}
          moves={state.moves}
          timeRemaining={state.timeRemaining}
          onRestart={handleReset}
        />
      )}

      {state.gameStatus === 'lost' && (
        <GameOverModal
          won={false}
          moves={state.moves}
          timeRemaining={state.timeRemaining}
          onRestart={handleReset}
        />
      )}
    </div>
  );
}

interface GameHeaderProps {
  timeRemaining: number;
  maxTime: number;
  moves: number;
  isComplete: boolean;
  gameStatus: GameStatus;
  difficulty: Difficulty;
  onStart: () => void;
  onReset: () => void;
  onDifficultyChange: (difficulty: Difficulty) => void;
}

function GameHeader({
  timeRemaining,
  maxTime,
  moves,
  isComplete,
  gameStatus,
  difficulty,
  onStart,
  onReset,
  onDifficultyChange,
}: GameHeaderProps) {
  const getTimerClass = () => {
    if (timeRemaining <= 5) return 'timer danger';
    if (timeRemaining <= 15) return 'timer warning';
    return 'timer';
  };

  return (
    <div className="circuit-header">
      <div className="header-title">
        <span className="title-icon">⚡</span>
        <span className="title-text">CircuitBreaker v1.0</span>
      </div>

      <div className="header-stats">
        <div className={getTimerClass()}>
          <span className="timer-label">Time:</span>
          <span className="timer-value">{timeRemaining}s</span>
        </div>

        <div className="moves">
          <span className="moves-label">Moves:</span>
          <span className="moves-value">{moves}</span>
        </div>

        <div className="status">
          <span className="status-label">Status:</span>
          <span className={`status-value ${isComplete ? 'complete' : 'incomplete'}`}>
            {isComplete ? 'COMPLETE' : 'INCOMPLETE'}
          </span>
        </div>
      </div>

      <div className="header-controls">
        {gameStatus === 'idle' && (
          <button onClick={onStart} className="btn-start">
            Start
          </button>
        )}

        <button onClick={onReset} className="btn-reset">
          Reset
        </button>

        <select
          value={difficulty}
          onChange={(e) => onDifficultyChange(e.target.value as Difficulty)}
          className="difficulty-select"
        >
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>
    </div>
  );
}

interface CircuitGridProps {
  grid: Tile[][];
  startPos: { row: number; col: number };
  endPos: { row: number; col: number };
  onTileClick: (row: number, col: number) => void;
  gameStatus: GameStatus;
}

function CircuitGrid({ grid, startPos, endPos, onTileClick, gameStatus }: CircuitGridProps) {
  return (
    <div className="circuit-grid">
      {grid.map((row, rowIndex) => (
        <div key={rowIndex} className="grid-row">
          {row.map((tile, colIndex) => (
            <CircuitTile
              key={`${rowIndex}-${colIndex}`}
              tile={tile}
              isStart={rowIndex === startPos.row && colIndex === startPos.col}
              isEnd={rowIndex === endPos.row && colIndex === endPos.col}
              onClick={() => onTileClick(tile.row, tile.col)}
              disabled={gameStatus !== 'playing'}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

interface CircuitTileProps {
  tile: Tile;
  isStart: boolean;
  isEnd: boolean;
  onClick: () => void;
  disabled: boolean;
}

function CircuitTile({ tile, isStart, isEnd, onClick, disabled }: CircuitTileProps) {
  const getTileSymbol = () => {
    if (isStart) return '◉';
    if (isEnd) return '◎';

    const symbols = {
      straight: '═',
      corner: '╔',
      empty: '',
      start: '◉',
      end: '◎',
    };

    return symbols[tile.type] || '';
  };

  const getTileClass = () => {
    const classes = ['circuit-tile', tile.type];

    if (tile.isPowered) {
      classes.push('powered');
    }

    if (isStart) classes.push('start-node');
    if (isEnd) classes.push('end-node');

    return classes.join(' ');
  };

  const canClick = !isStart && !isEnd && !disabled;

  return (
    <button
      className={getTileClass()}
      onClick={onClick}
      disabled={!canClick}
      style={{
        transform: `rotate(${tile.rotation}deg)`,
      }}
    >
      {getTileSymbol()}
    </button>
  );
}

interface GameOverModalProps {
  won: boolean;
  moves: number;
  timeRemaining: number;
  onRestart: () => void;
}

function GameOverModal({ won, moves, timeRemaining, onRestart }: GameOverModalProps) {
  return (
    <div className="game-over-modal">
      <div className="modal-content">
        <h2 className={won ? 'win-title' : 'lose-title'}>
          {won ? '⚡ CIRCUITS CONNECTED ⚡' : '⌛ CONNECTION TIMEOUT ⌛'}
        </h2>

        <div className="modal-message">
          {won ? 'All nodes powered successfully!' : 'Circuit incomplete. System offline.'}
        </div>

        <div className="modal-stats">
          {won && <div>Time remaining: {timeRemaining}s</div>}
          <div>Moves: {moves}</div>
        </div>

        <div className="modal-buttons">
          <button onClick={onRestart} className="btn-modal btn-primary">
            {won ? 'Play Again' : 'Try Again'}
          </button>
        </div>
      </div>
    </div>
  );
}
