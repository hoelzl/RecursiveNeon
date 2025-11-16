import React, { useState, useCallback, useReducer, useEffect } from 'react';
import { PortScannerGame, type Difficulty, type GridCell, type GameStatus } from './PortScannerGame';
import './portscanner.css';

export function PortScannerApp() {
  const [game, setGame] = useState<PortScannerGame | null>(null);
  const [, forceUpdate] = useReducer(x => x + 1, 0);

  useEffect(() => {
    startNewGame('medium');
  }, []);

  const startNewGame = useCallback((difficulty: Difficulty) => {
    const newGame = new PortScannerGame(difficulty);
    newGame.onUpdate = () => forceUpdate();
    setGame(newGame);
  }, []);

  const handleCellClick = useCallback((row: number, col: number) => {
    if (!game) return;
    game.revealCell(row, col);
  }, [game]);

  const handleCellRightClick = useCallback((
    e: React.MouseEvent,
    row: number,
    col: number
  ) => {
    e.preventDefault();
    if (!game) return;
    game.toggleFlag(row, col);
  }, [game]);

  const handleReset = useCallback(() => {
    if (!game) return;
    game.reset();
  }, [game]);

  if (!game) {
    return <div className="port-scanner-loading">Initializing...</div>;
  }

  const state = game.getState();

  return (
    <div className="port-scanner-app">
      <GameHeader
        score={state.score}
        difficulty={state.difficulty}
        gameStatus={state.gameStatus}
        onReset={handleReset}
        onDifficultyChange={startNewGame}
      />

      <GameGrid
        grid={state.grid}
        onCellClick={handleCellClick}
        onCellRightClick={handleCellRightClick}
        gameStatus={state.gameStatus}
      />

      <GameStats
        portsFound={countFoundPorts(state.grid)}
        totalPorts={state.openPorts}
        flagged={state.flaggedCount}
      />

      {state.gameStatus === 'won' && (
        <GameOverModal
          won={true}
          score={state.score}
          onRestart={handleReset}
          onNewGame={() => startNewGame(state.difficulty)}
        />
      )}
    </div>
  );
}

interface GameHeaderProps {
  score: number;
  difficulty: Difficulty;
  gameStatus: GameStatus;
  onReset: () => void;
  onDifficultyChange: (difficulty: Difficulty) => void;
}

function GameHeader({ score, difficulty, gameStatus, onReset, onDifficultyChange }: GameHeaderProps) {
  return (
    <div className="game-header">
      <div className="header-title">
        <span className="title-icon">🔍</span>
        <span className="title-text">PortScanner v1.0</span>
      </div>

      <div className="header-stats">
        <div className="stat">
          <span className="stat-label">Score:</span>
          <span className="stat-value">{score}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Difficulty:</span>
          <span className="stat-value">{difficulty.toUpperCase()}</span>
        </div>
      </div>

      <div className="header-controls">
        <button onClick={onReset} className="btn-reset">
          Reset
        </button>
        <select
          value={difficulty}
          onChange={(e) => onDifficultyChange(e.target.value as Difficulty)}
          className="difficulty-select"
          disabled={gameStatus === 'playing'}
        >
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>
    </div>
  );
}

interface GameGridProps {
  grid: GridCell[][];
  onCellClick: (row: number, col: number) => void;
  onCellRightClick: (e: React.MouseEvent, row: number, col: number) => void;
  gameStatus: GameStatus;
}

function GameGrid({ grid, onCellClick, onCellRightClick, gameStatus }: GameGridProps) {
  return (
    <div className="game-grid">
      {grid.map((row, rowIndex) => (
        <div key={rowIndex} className="grid-row">
          {row.map((cell, colIndex) => (
            <GridCellComponent
              key={`${rowIndex}-${colIndex}`}
              cell={cell}
              onClick={() => onCellClick(cell.row, cell.col)}
              onContextMenu={(e) => onCellRightClick(e, cell.row, cell.col)}
              gameOver={gameStatus === 'won' || gameStatus === 'lost'}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

interface GridCellProps {
  cell: GridCell;
  onClick: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
  gameOver: boolean;
}

function GridCellComponent({ cell, onClick, onContextMenu, gameOver }: GridCellProps) {
  const getCellContent = () => {
    if (cell.isFlagged) {
      return <span className="flag-icon">⚑</span>;
    }

    if (!cell.isRevealed) {
      return gameOver && cell.isOpenPort ? '●' : '';
    }

    if (cell.isOpenPort) {
      return <span className="port-icon">●</span>;
    }

    return cell.adjacentPorts > 0 ? cell.adjacentPorts : '';
  };

  const getCellClassName = () => {
    const classes = ['grid-cell'];

    if (cell.isFlagged) {
      classes.push('flagged');
    } else if (cell.isRevealed) {
      if (cell.isOpenPort) {
        classes.push('open-port');
      } else {
        classes.push('revealed');
        if (cell.adjacentPorts > 0) {
          classes.push(`adjacent-${cell.adjacentPorts}`);
        }
      }
    } else {
      classes.push('unrevealed');
    }

    return classes.join(' ');
  };

  return (
    <button
      className={getCellClassName()}
      onClick={onClick}
      onContextMenu={onContextMenu}
      disabled={cell.isRevealed || gameOver}
    >
      {getCellContent()}
    </button>
  );
}

interface GameStatsProps {
  portsFound: number;
  totalPorts: number;
  flagged: number;
}

function GameStats({ portsFound, totalPorts, flagged }: GameStatsProps) {
  return (
    <div className="game-stats">
      <div className="stat-item">
        <span className="stat-icon">🎯</span>
        <span>Ports found: {portsFound}/{totalPorts}</span>
      </div>
      <div className="stat-item">
        <span className="stat-icon">⚑</span>
        <span>Flags: {flagged}</span>
      </div>
    </div>
  );
}

interface GameOverModalProps {
  won: boolean;
  score: number;
  onRestart: () => void;
  onNewGame: () => void;
}

function GameOverModal({ won, score, onRestart, onNewGame }: GameOverModalProps) {
  return (
    <div className="game-over-modal">
      <div className="modal-content">
        <h2 className={won ? 'win-title' : 'lose-title'}>
          {won ? '✓ NETWORK MAPPED' : '⚠ SCAN FAILED'}
        </h2>

        <div className="modal-message">
          {won ? 'All open ports identified!' : 'Intrusion detected.'}
        </div>

        <div className="modal-score">
          Score: <span className="score-value">{score}</span>
        </div>

        <div className="modal-buttons">
          <button onClick={onRestart} className="btn-modal btn-primary">
            Restart
          </button>
          <button onClick={onNewGame} className="btn-modal btn-secondary">
            New Game
          </button>
        </div>
      </div>
    </div>
  );
}

// Helper function
function countFoundPorts(grid: GridCell[][]): number {
  let count = 0;
  for (const row of grid) {
    for (const cell of row) {
      if (cell.isOpenPort && (cell.isRevealed || cell.isFlagged)) {
        count++;
      }
    }
  }
  return count;
}
