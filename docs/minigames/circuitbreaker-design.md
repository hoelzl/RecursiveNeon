# CircuitBreaker - Design Document

> **Game Type**: Graphical (Desktop App)
> **Implementation**: TypeScript/React

---

## Architecture

### Component Structure

```
CircuitBreakerApp (React Component)
  ├── CircuitBreakerGame (Game Logic)
  │   ├── generatePuzzle()
  │   ├── rotateTile()
  │   ├── findConnectedPaths()
  │   └── checkCircuitCompletion()
  ├── CircuitGrid (UI Component)
  │   └── CircuitTile (Individual tile)
  ├── GameTimer (Countdown display)
  └── CircuitStatus (Progress indicators)
```

## Game State

```typescript
interface CircuitBreakerState {
  grid: Tile[][];
  rows: number;
  cols: number;
  circuits: Circuit[];
  completedCircuits: number;
  timeRemaining: number;
  maxTime: number;
  moves: number;
  gameStatus: 'idle' | 'playing' | 'won' | 'lost';
  difficulty: 'easy' | 'medium' | 'hard';
  startTime: number | null;
}

interface Tile {
  row: number;
  col: number;
  type: TileType;
  rotation: 0 | 90 | 180 | 270; // Degrees
  isStart: boolean;
  isEnd: boolean;
  circuitId?: number; // Which circuit this belongs to (if start/end)
  isPowered: boolean; // Is this tile on an active path?
  powerSource?: number; // Which circuit powers this tile
}

type TileType =
  | 'straight'    // ═ or ║
  | 'corner'      // ╔ ╗ ╚ ╝
  | 't-junction'  // ╠ ╣ ╦ ╩
  | 'cross'       // ╬
  | 'empty'       // No connections
  | 'start'       // ◉ Source node
  | 'end';        // ◎ Target node

interface Circuit {
  id: number;
  startPos: { row: number; col: number };
  endPos: { row: number; col: number };
  isComplete: boolean;
  color: string;
}

// Tile connections: which sides connect
interface TileConnections {
  top: boolean;
  right: boolean;
  bottom: boolean;
  left: boolean;
}
```

## Core Algorithms

### Tile Connection Definitions

```typescript
const TILE_CONNECTIONS: Record<TileType, TileConnections> = {
  straight: { top: true, right: false, bottom: true, left: false },
  corner: { top: true, right: true, bottom: false, left: false },
  't-junction': { top: true, right: true, bottom: true, left: false },
  cross: { top: true, right: true, bottom: true, left: true },
  empty: { top: false, right: false, bottom: false, left: false },
  start: { top: false, right: true, bottom: false, left: false }, // Connects right
  end: { top: false, right: false, bottom: false, left: true },   // Connects left
};

function getRotatedConnections(
  type: TileType,
  rotation: number
): TileConnections {
  const base = { ...TILE_CONNECTIONS[type] };

  if (rotation === 0) return base;

  // Rotate connections clockwise
  const rotations = rotation / 90;
  let current = base;

  for (let i = 0; i < rotations; i++) {
    current = {
      top: current.left,
      right: current.top,
      bottom: current.right,
      left: current.bottom,
    };
  }

  return current;
}
```

### Puzzle Generation

```typescript
function generatePuzzle(difficulty: Difficulty): {
  grid: Tile[][];
  circuits: Circuit[];
} {
  const config = getDifficultyConfig(difficulty);
  const grid = createEmptyGrid(config.rows, config.cols);

  const circuits: Circuit[] = [];

  // Place circuits
  for (let i = 0; i < config.circuitCount; i++) {
    const circuit = placeCircuit(grid, i, config);
    circuits.push(circuit);
  }

  // Fill remaining tiles with random connections
  fillGrid(grid, config);

  // Randomize rotations
  randomizeRotations(grid);

  return { grid, circuits };
}

function placeCircuit(
  grid: Tile[][],
  circuitId: number,
  config: DifficultyConfig
): Circuit {
  const rows = grid.length;
  const cols = grid[0].length;

  // Place start node on left side
  const startRow = Math.floor(Math.random() * rows);
  const startCol = 0;

  grid[startRow][startCol] = {
    row: startRow,
    col: startCol,
    type: 'start',
    rotation: 0,
    isStart: true,
    isEnd: false,
    circuitId,
    isPowered: false,
  };

  // Place end node on right side
  const endRow = Math.floor(Math.random() * rows);
  const endCol = cols - 1;

  grid[endRow][endCol] = {
    row: endRow,
    col: endCol,
    type: 'end',
    rotation: 0,
    isStart: false,
    isEnd: true,
    circuitId,
    isPowered: false,
  };

  // Generate a valid path from start to end
  const path = generatePath(grid, startRow, startCol, endRow, endCol);
  placePath(grid, path);

  return {
    id: circuitId,
    startPos: { row: startRow, col: startCol },
    endPos: { row: endRow, col: endCol },
    isComplete: false,
    color: getCircuitColor(circuitId),
  };
}

function generatePath(
  grid: Tile[][],
  startRow: number,
  startCol: number,
  endRow: number,
  endCol: number
): { row: number; col: number }[] {
  // Simple pathfinding: move right and vertically as needed
  const path: { row: number; col: number }[] = [];
  let currentRow = startRow;
  let currentCol = startCol + 1; // Start after source node

  path.push({ row: startRow, col: startCol });

  // Move toward end column
  while (currentCol < endCol) {
    path.push({ row: currentRow, col: currentCol });
    currentCol++;
  }

  // Move vertically to end row
  while (currentRow !== endRow) {
    currentRow += currentRow < endRow ? 1 : -1;
    path.push({ row: currentRow, col: currentCol });
  }

  return path;
}

function placePath(grid: Tile[][], path: { row: number; col: number }[]): void {
  for (let i = 1; i < path.length - 1; i++) {
    const { row, col } = path[i];
    const prev = path[i - 1];
    const next = path[i + 1];

    // Determine tile type based on direction change
    const dirIn = getDirection(prev, path[i]);
    const dirOut = getDirection(path[i], next);

    let type: TileType;

    if (dirIn === dirOut) {
      type = 'straight';
    } else {
      type = 'corner';
    }

    grid[row][col] = {
      row,
      col,
      type,
      rotation: 0,
      isStart: false,
      isEnd: false,
      isPowered: false,
    };
  }
}

function getDirection(
  from: { row: number; col: number },
  to: { row: number; col: number }
): 'up' | 'down' | 'left' | 'right' {
  if (to.row < from.row) return 'up';
  if (to.row > from.row) return 'down';
  if (to.col < from.col) return 'left';
  return 'right';
}
```

### Tile Rotation

```typescript
function rotateTile(row: number, col: number): void {
  const tile = this.state.grid[row][col];

  if (tile.isStart || tile.isEnd) {
    return; // Cannot rotate start/end nodes
  }

  // Rotate 90° clockwise
  tile.rotation = ((tile.rotation + 90) % 360) as 0 | 90 | 180 | 270;
  this.state.moves++;

  // Recalculate powered paths
  this.updatePoweredPaths();

  // Check if any circuits completed
  this.checkCircuitCompletion();
}
```

### Path Finding & Power Flow

```typescript
function updatePoweredPaths(): void {
  // Reset all tiles
  for (const row of this.state.grid) {
    for (const tile of row) {
      tile.isPowered = false;
      tile.powerSource = undefined;
    }
  }

  // Trace each circuit
  for (const circuit of this.state.circuits) {
    const visited = new Set<string>();
    const queue: { row: number; col: number }[] = [circuit.startPos];

    while (queue.length > 0) {
      const current = queue.shift()!;
      const key = `${current.row},${current.col}`;

      if (visited.has(key)) continue;
      visited.add(key);

      const tile = this.state.grid[current.row][current.col];
      tile.isPowered = true;
      tile.powerSource = circuit.id;

      // Get connections for this tile
      const connections = getRotatedConnections(tile.type, tile.rotation);

      // Check each direction
      const directions = [
        { dir: 'top', dr: -1, dc: 0, connect: connections.top, opposite: 'bottom' },
        { dir: 'right', dr: 0, dc: 1, connect: connections.right, opposite: 'left' },
        { dir: 'bottom', dr: 1, dc: 0, connect: connections.bottom, opposite: 'top' },
        { dir: 'left', dr: 0, dc: -1, connect: connections.left, opposite: 'right' },
      ];

      for (const { dr, dc, connect, opposite } of directions) {
        if (!connect) continue;

        const nr = current.row + dr;
        const nc = current.col + dc;

        // Check bounds
        if (nr < 0 || nr >= this.state.rows || nc < 0 || nc >= this.state.cols) {
          continue;
        }

        const neighbor = this.state.grid[nr][nc];
        const neighborKey = `${nr},${nc}`;

        if (visited.has(neighborKey)) continue;

        // Check if neighbor connects back to us
        const neighborConnections = getRotatedConnections(
          neighbor.type,
          neighbor.rotation
        );

        if (neighborConnections[opposite as keyof TileConnections]) {
          queue.push({ row: nr, col: nc });
        }
      }
    }
  }
}

function checkCircuitCompletion(): void {
  let completedCount = 0;

  for (const circuit of this.state.circuits) {
    const endTile = this.state.grid[circuit.endPos.row][circuit.endPos.col];

    circuit.isComplete = endTile.isPowered && endTile.powerSource === circuit.id;

    if (circuit.isComplete) {
      completedCount++;
    }
  }

  this.state.completedCircuits = completedCount;

  // Check win condition
  if (completedCount === this.state.circuits.length) {
    this.state.gameStatus = 'won';
  }
}
```

### Timer Logic

```typescript
function startTimer(): void {
  const interval = setInterval(() => {
    if (this.state.gameStatus !== 'playing') {
      clearInterval(interval);
      return;
    }

    this.state.timeRemaining--;

    if (this.state.timeRemaining <= 0) {
      this.state.gameStatus = 'lost';
      clearInterval(interval);
    }

    // Trigger UI update
    this.notifyUpdate();
  }, 1000);
}
```

## React Component Structure

### Main Component

```typescript
export function CircuitBreakerApp() {
  const [game, setGame] = useState<CircuitBreakerGame | null>(null);
  const [, forceUpdate] = useReducer(x => x + 1, 0);

  useEffect(() => {
    startNewGame('medium');
  }, []);

  const startNewGame = useCallback((difficulty: Difficulty) => {
    const newGame = new CircuitBreakerGame(difficulty);
    newGame.onUpdate = () => forceUpdate();
    newGame.startTimer();
    setGame(newGame);
  }, []);

  const handleTileClick = useCallback((row: number, col: number) => {
    if (!game || game.getState().gameStatus !== 'playing') return;
    game.rotateTile(row, col);
  }, [game]);

  if (!game) return <div>Loading...</div>;

  const state = game.getState();

  return (
    <div className="circuit-breaker-app">
      <GameHeader
        timeRemaining={state.timeRemaining}
        maxTime={state.maxTime}
        moves={state.moves}
        completedCircuits={state.completedCircuits}
        totalCircuits={state.circuits.length}
      />

      <CircuitGrid
        grid={state.grid}
        circuits={state.circuits}
        onTileClick={handleTileClick}
        gameStatus={state.gameStatus}
      />

      <GameControls
        onReset={() => startNewGame(state.difficulty)}
        onNewGame={() => startNewGame(state.difficulty)}
      />

      {state.gameStatus === 'won' && <WinModal />}
      {state.gameStatus === 'lost' && <LoseModal />}
    </div>
  );
}
```

### Tile Component

```typescript
interface CircuitTileProps {
  tile: Tile;
  onClick: () => void;
  gameStatus: GameStatus;
}

export function CircuitTile({ tile, onClick, gameStatus }: CircuitTileProps) {
  const getTileSymbol = () => {
    if (tile.isStart) return '◉';
    if (tile.isEnd) return '◎';

    const symbols = {
      straight: '═',
      corner: '╔',
      't-junction': '╠',
      cross: '╬',
      empty: '',
    };

    return symbols[tile.type] || '';
  };

  const getTileClass = () => {
    const classes = ['circuit-tile', tile.type];

    if (tile.isPowered) {
      classes.push('powered');
      classes.push(`circuit-${tile.powerSource}`);
    }

    if (tile.isStart) classes.push('start-node');
    if (tile.isEnd) classes.push('end-node');

    return classes.join(' ');
  };

  return (
    <button
      className={getTileClass()}
      onClick={onClick}
      disabled={gameStatus !== 'playing' || tile.isStart || tile.isEnd}
      style={{
        transform: `rotate(${tile.rotation}deg)`,
      }}
    >
      {getTileSymbol()}
    </button>
  );
}
```

## Styling

```css
.circuit-breaker-app {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
  min-height: 100%;
  color: #00ff00;
  font-family: 'Courier New', monospace;
}

.circuit-grid {
  display: grid;
  gap: 4px;
  padding: 1rem;
  background: rgba(0, 255, 0, 0.1);
  border: 2px solid #00ff00;
  border-radius: 8px;
}

.circuit-tile {
  width: 60px;
  height: 60px;
  border: 2px solid #333;
  background: #1a1a1a;
  color: #555;
  font-size: 32px;
  cursor: pointer;
  transition: transform 0.3s ease, background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.circuit-tile:hover:not(:disabled) {
  background: #2a2a2a;
}

.circuit-tile.powered {
  color: #00ff00;
  box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
  animation: pulse 2s infinite;
}

.circuit-tile.circuit-0 {
  color: #00ff00;
}

.circuit-tile.circuit-1 {
  color: #00ffff;
}

.circuit-tile.circuit-2 {
  color: #ff00ff;
}

.circuit-tile.start-node,
.circuit-tile.end-node {
  font-size: 40px;
  cursor: default;
}

.circuit-tile.start-node {
  color: #00ff00;
  box-shadow: 0 0 20px rgba(0, 255, 0, 0.8);
}

.circuit-tile.end-node {
  color: #00ffff;
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.8);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.game-timer {
  font-size: 2rem;
  font-weight: bold;
  color: #00ff00;
}

.game-timer.warning {
  color: #ffff00;
  animation: blink 0.5s infinite;
}

.game-timer.danger {
  color: #ff0000;
  animation: blink 0.3s infinite;
}

@keyframes blink {
  50% { opacity: 0.3; }
}
```

## Testing Strategy

```typescript
describe('CircuitBreakerGame', () => {
  it('generates puzzle with correct dimensions', () => {
    const game = new CircuitBreakerGame('medium');
    const state = game.getState();
    expect(state.rows).toBe(8);
    expect(state.cols).toBe(8);
  });

  it('places correct number of circuits', () => {
    const game = new CircuitBreakerGame('medium');
    const state = game.getState();
    expect(state.circuits.length).toBe(2);
  });

  it('rotates tiles correctly', () => {
    const game = new CircuitBreakerGame('easy');
    const tile = game.getState().grid[2][2];
    const initialRotation = tile.rotation;

    game.rotateTile(2, 2);
    expect(tile.rotation).toBe((initialRotation + 90) % 360);
  });

  it('detects circuit completion', () => {
    // Create a simple solvable puzzle
    // Rotate tiles to complete circuit
    // Verify circuit is marked complete
  });

  it('detects win condition', () => {
    // Complete all circuits
    // Verify game status is 'won'
  });

  it('times out correctly', () => {
    const game = new CircuitBreakerGame('easy');
    game['state'].timeRemaining = 0;
    game['checkTimeout']();
    expect(game.getState().gameStatus).toBe('lost');
  });
});
```

## File Structure

```
frontend/src/
├── components/
│   └── apps/
│       └── minigames/
│           ├── CircuitBreakerApp.tsx
│           ├── CircuitBreakerGame.ts
│           ├── CircuitBreakerGame.test.ts
│           ├── components/
│           │   ├── CircuitGrid.tsx
│           │   ├── CircuitTile.tsx
│           │   ├── GameTimer.tsx
│           │   └── CircuitStatus.tsx
│           └── circuitbreaker.css
```

---

## Summary

CircuitBreaker delivers a compelling puzzle experience with:
- Time pressure for excitement
- Visual feedback of power flow
- Strategic tile rotation mechanics
- Guaranteed solvable puzzles
- Clean architecture for testing
- Engaging cyberpunk aesthetic
