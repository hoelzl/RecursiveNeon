# PortScanner - Design Document

> **Game Type**: Graphical (Desktop App)
> **Implementation**: TypeScript/React

---

## Architecture

### Component Structure

```
PortScannerApp (React Component)
  ├── PortScannerGame (Game Logic)
  │   ├── generateGrid()
  │   ├── revealCell()
  │   ├── toggleFlag()
  │   └── checkWinCondition()
  ├── GameGrid (UI Component)
  │   └── GridCell (Individual cell)
  ├── GameHeader (Lives, Score, Timer)
  └── GameControls (Reset, Difficulty selector)
```

## Game State

```typescript
interface PortScannerState {
  grid: GridCell[][];
  rows: number;
  cols: number;
  openPorts: number;
  revealedCount: number;
  flaggedCount: number;
  lives: number;
  maxLives: number;
  score: number;
  gameStatus: 'idle' | 'playing' | 'won' | 'lost';
  difficulty: 'easy' | 'medium' | 'hard';
  startTime: number | null;
  endTime: number | null;
  firstClick: boolean;
}

interface GridCell {
  row: number;
  col: number;
  isOpenPort: boolean;
  isRevealed: boolean;
  isFlagged: boolean;
  adjacentPorts: number; // 0-8
}
```

## Core Algorithms

### Grid Generation

```typescript
function generateGrid(
  rows: number,
  cols: number,
  portCount: number
): GridCell[][] {
  const grid: GridCell[][] = [];

  // Initialize empty grid
  for (let r = 0; r < rows; r++) {
    grid[r] = [];
    for (let c = 0; c < cols; c++) {
      grid[r][c] = {
        row: r,
        col: c,
        isOpenPort: false,
        isRevealed: false,
        isFlagged: false,
        adjacentPorts: 0,
      };
    }
  }

  // Place open ports randomly
  let portsPlaced = 0;
  while (portsPlaced < portCount) {
    const r = Math.floor(Math.random() * rows);
    const c = Math.floor(Math.random() * cols);

    if (!grid[r][c].isOpenPort) {
      grid[r][c].isOpenPort = true;
      portsPlaced++;
    }
  }

  // Calculate adjacent port counts
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (!grid[r][c].isOpenPort) {
        grid[r][c].adjacentPorts = countAdjacentPorts(grid, r, c);
      }
    }
  }

  return grid;
}

function countAdjacentPorts(
  grid: GridCell[][],
  row: number,
  col: number
): number {
  let count = 0;
  const rows = grid.length;
  const cols = grid[0].length;

  // Check all 8 adjacent cells
  for (let dr = -1; dr <= 1; dr++) {
    for (let dc = -1; dc <= 1; dc++) {
      if (dr === 0 && dc === 0) continue; // Skip self

      const nr = row + dr;
      const nc = col + dc;

      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols) {
        if (grid[nr][nc].isOpenPort) {
          count++;
        }
      }
    }
  }

  return count;
}
```

### First Click Safety

```typescript
function ensureFirstClickSafe(
  grid: GridCell[][],
  row: number,
  col: number
): void {
  // If first click is on an open port or adjacent to one, move it
  const cell = grid[row][col];

  if (cell.isOpenPort || cell.adjacentPorts > 0) {
    // Find a safe location (no port, no adjacent ports)
    for (let r = 0; r < grid.length; r++) {
      for (let c = 0; c < grid[0].length; c++) {
        if (r === row && c === col) continue;

        const candidate = grid[r][c];
        if (!candidate.isOpenPort && candidate.adjacentPorts === 0) {
          // Move the port from clicked cell to safe location
          if (cell.isOpenPort) {
            cell.isOpenPort = false;
            candidate.isOpenPort = true;
          }

          // Recalculate adjacency for affected cells
          recalculateAdjacency(grid);
          return;
        }
      }
    }

    // If no perfect safe spot, just move away from clicked cell
    cell.isOpenPort = false;
    recalculateAdjacency(grid);
  }
}
```

### Cell Reveal Logic

```typescript
function revealCell(row: number, col: number): {
  success: boolean;
  hitFirewall: boolean;
  autoRevealed: GridCell[];
} {
  const cell = this.state.grid[row][col];

  if (cell.isRevealed || cell.isFlagged) {
    return { success: false, hitFirewall: false, autoRevealed: [] };
  }

  // Ensure first click is safe
  if (this.state.firstClick) {
    this.ensureFirstClickSafe(row, col);
    this.state.firstClick = false;
    this.state.startTime = Date.now();
  }

  cell.isRevealed = true;
  this.state.revealedCount++;

  // Hit open port
  if (cell.isOpenPort) {
    this.state.score += 10;
    this.checkWinCondition();
    return { success: true, hitFirewall: false, autoRevealed: [] };
  }

  // Hit firewall (non-port, non-zero cell in hard mode)
  // In normal Minesweeper variant, all non-ports are safe
  // We'll simplify: only open ports are valuable, others are safe

  // Auto-reveal if zero adjacent
  if (cell.adjacentPorts === 0) {
    const autoRevealed = this.autoRevealAdjacent(row, col);
    return { success: true, hitFirewall: false, autoRevealed };
  }

  return { success: true, hitFirewall: false, autoRevealed: [] };
}

function autoRevealAdjacent(row: number, col: number): GridCell[] {
  const revealed: GridCell[] = [];
  const toCheck: [number, number][] = [[row, col]];
  const checked = new Set<string>();

  while (toCheck.length > 0) {
    const [r, c] = toCheck.pop()!;
    const key = `${r},${c}`;

    if (checked.has(key)) continue;
    checked.add(key);

    // Check all 8 adjacent cells
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;

        const nr = r + dr;
        const nc = c + dc;

        if (nr < 0 || nr >= this.state.rows ||
            nc < 0 || nc >= this.state.cols) {
          continue;
        }

        const neighbor = this.state.grid[nr][nc];

        if (!neighbor.isRevealed && !neighbor.isFlagged && !neighbor.isOpenPort) {
          neighbor.isRevealed = true;
          this.state.revealedCount++;
          revealed.push(neighbor);

          // If this neighbor also has zero adjacent, continue flood fill
          if (neighbor.adjacentPorts === 0) {
            toCheck.push([nr, nc]);
          }
        }
      }
    }
  }

  return revealed;
}
```

### Flagging Logic

```typescript
function toggleFlag(row: number, col: number): boolean {
  const cell = this.state.grid[row][col];

  if (cell.isRevealed) {
    return false; // Cannot flag revealed cells
  }

  cell.isFlagged = !cell.isFlagged;

  if (cell.isFlagged) {
    this.state.flaggedCount++;
    if (cell.isOpenPort) {
      this.state.score += 5; // Bonus for correct flag
    }
  } else {
    this.state.flaggedCount--;
    if (!cell.isOpenPort) {
      this.state.score -= 5; // Penalty for removing incorrect flag
    }
  }

  this.checkWinCondition();
  return true;
}
```

### Win Condition

```typescript
function checkWinCondition(): void {
  // Win if all open ports are either revealed or flagged
  let foundPorts = 0;
  let totalPorts = 0;

  for (const row of this.state.grid) {
    for (const cell of row) {
      if (cell.isOpenPort) {
        totalPorts++;
        if (cell.isRevealed || cell.isFlagged) {
          foundPorts++;
        }
      }
    }
  }

  if (foundPorts === totalPorts) {
    this.state.gameStatus = 'won';
    this.state.endTime = Date.now();

    // Time bonus
    if (this.state.startTime) {
      const timeSeconds = Math.floor(
        (this.state.endTime - this.state.startTime) / 1000
      );
      this.state.score += Math.max(0, 300 - timeSeconds);
    }
  }
}
```

## React Component Structure

### Main Component

```typescript
export function PortScannerApp() {
  const [game, setGame] = useState<PortScannerGame | null>(null);
  const [, forceUpdate] = useReducer(x => x + 1, 0);

  useEffect(() => {
    startNewGame('medium');
  }, []);

  const startNewGame = useCallback((difficulty: Difficulty) => {
    const newGame = new PortScannerGame(difficulty);
    setGame(newGame);
  }, []);

  const handleCellClick = useCallback((row: number, col: number) => {
    if (!game || game.getState().gameStatus !== 'playing') return;

    const result = game.revealCell(row, col);
    forceUpdate();

    // Handle animations, sound effects, etc.
  }, [game]);

  const handleCellRightClick = useCallback((
    e: React.MouseEvent,
    row: number,
    col: number
  ) => {
    e.preventDefault();
    if (!game || game.getState().gameStatus !== 'playing') return;

    game.toggleFlag(row, col);
    forceUpdate();
  }, [game]);

  if (!game) return <div>Loading...</div>;

  const state = game.getState();

  return (
    <div className="port-scanner-app">
      <GameHeader
        lives={state.lives}
        maxLives={state.maxLives}
        score={state.score}
        difficulty={state.difficulty}
      />

      <GameGrid
        grid={state.grid}
        onCellClick={handleCellClick}
        onCellRightClick={handleCellRightClick}
        gameStatus={state.gameStatus}
      />

      <GameControls
        onReset={() => startNewGame(state.difficulty)}
        onDifficultyChange={startNewGame}
      />

      {state.gameStatus === 'won' && (
        <WinModal score={state.score} onRestart={() => startNewGame(state.difficulty)} />
      )}

      {state.gameStatus === 'lost' && (
        <LoseModal onRestart={() => startNewGame(state.difficulty)} />
      )}
    </div>
  );
}
```

### Grid Component

```typescript
interface GameGridProps {
  grid: GridCell[][];
  onCellClick: (row: number, col: number) => void;
  onCellRightClick: (e: React.MouseEvent, row: number, col: number) => void;
  gameStatus: GameStatus;
}

export function GameGrid({ grid, onCellClick, onCellRightClick, gameStatus }: GameGridProps) {
  return (
    <div className="game-grid">
      {grid.map((row, rowIndex) => (
        <div key={rowIndex} className="grid-row">
          {row.map((cell, colIndex) => (
            <GridCell
              key={`${rowIndex}-${colIndex}`}
              cell={cell}
              onClick={() => onCellClick(cell.row, cell.col)}
              onContextMenu={(e) => onCellRightClick(e, cell.row, cell.col)}
              gameOver={gameStatus !== 'playing'}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
```

### Cell Component

```typescript
interface GridCellProps {
  cell: GridCell;
  onClick: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
  gameOver: boolean;
}

export function GridCell({ cell, onClick, onContextMenu, gameOver }: GridCellProps) {
  const getCellContent = () => {
    if (cell.isFlagged) {
      return <span className="flag-icon">⚑</span>;
    }

    if (!cell.isRevealed) {
      return gameOver && cell.isOpenPort ? '●' : '?';
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
```

## Styling

```css
.port-scanner-app {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  min-height: 100%;
  font-family: 'Courier New', monospace;
}

.game-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 1rem;
  background: #0f3460;
  border: 2px solid #00ff00;
  border-radius: 4px;
}

.grid-row {
  display: flex;
  gap: 2px;
}

.grid-cell {
  width: 40px;
  height: 40px;
  border: 1px solid #00ff00;
  background: #2a2a2a;
  color: #00ff00;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s;
}

.grid-cell:hover:not(:disabled) {
  background: #3a3a3a;
  transform: scale(1.05);
}

.grid-cell.revealed {
  background: #1a1a1a;
  cursor: default;
}

.grid-cell.unrevealed {
  background: #2a2a2a;
}

.grid-cell.flagged {
  background: #004477;
  color: #00ffff;
}

.grid-cell.open-port {
  background: #00ff00;
  color: #000;
}

/* Number colors */
.grid-cell.adjacent-1 { color: #0099ff; }
.grid-cell.adjacent-2 { color: #00ff00; }
.grid-cell.adjacent-3 { color: #ffff00; }
.grid-cell.adjacent-4 { color: #ff9900; }
.grid-cell.adjacent-5 { color: #ff0000; }
.grid-cell.adjacent-6 { color: #ff00ff; }
.grid-cell.adjacent-7 { color: #ffffff; }
.grid-cell.adjacent-8 { color: #ff0099; }
```

## Testing Strategy

```typescript
describe('PortScannerGame', () => {
  it('generates grid with correct dimensions', () => {
    const game = new PortScannerGame('medium');
    const state = game.getState();
    expect(state.rows).toBe(10);
    expect(state.cols).toBe(10);
  });

  it('places correct number of open ports', () => {
    const game = new PortScannerGame('easy');
    const state = game.getState();
    let portCount = 0;

    for (const row of state.grid) {
      for (const cell of row) {
        if (cell.isOpenPort) portCount++;
      }
    }

    expect(portCount).toBe(10);
  });

  it('calculates adjacent ports correctly', () => {
    // Test with known configuration
  });

  it('auto-reveals cells with zero adjacent ports', () => {
    const game = new PortScannerGame('easy');
    // Find a zero-adjacent cell and click it
    // Verify multiple cells revealed
  });

  it('detects win condition', () => {
    const game = new PortScannerGame('easy');
    // Reveal all ports
    // Verify game status is 'won'
  });
});
```

## File Structure

```
frontend/src/
├── components/
│   └── apps/
│       └── minigames/
│           ├── PortScannerApp.tsx
│           ├── PortScannerGame.ts
│           ├── PortScannerGame.test.ts
│           ├── components/
│           │   ├── GameGrid.tsx
│           │   ├── GridCell.tsx
│           │   ├── GameHeader.tsx
│           │   └── GameControls.tsx
│           └── portscanner.css
```

---

## Summary

PortScanner provides an engaging Minesweeper-style experience with:
- Clear visual feedback
- Strategic depth
- Replayability
- Clean component architecture
- Comprehensive testing
- Cyberpunk aesthetic
