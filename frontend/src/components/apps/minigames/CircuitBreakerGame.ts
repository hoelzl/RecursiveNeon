/**
 * CircuitBreaker Game Logic
 *
 * A time-based puzzle where players rotate tiles to connect circuits.
 */

export type Difficulty = 'easy' | 'medium' | 'hard';
export type GameStatus = 'idle' | 'playing' | 'won' | 'lost';
export type TileType = 'straight' | 'corner' | 'empty' | 'start' | 'end';

export interface Tile {
  row: number;
  col: number;
  type: TileType;
  rotation: 0 | 90 | 180 | 270;
  isPowered: boolean;
}

export interface CircuitBreakerState {
  grid: Tile[][];
  rows: number;
  cols: number;
  startPos: { row: number; col: number };
  endPos: { row: number; col: number };
  isComplete: boolean;
  moves: number;
  timeRemaining: number;
  maxTime: number;
  gameStatus: GameStatus;
  difficulty: Difficulty;
}

interface TileConnections {
  top: boolean;
  right: boolean;
  bottom: boolean;
  left: boolean;
}

const TILE_CONNECTIONS: Record<TileType, TileConnections> = {
  straight: { top: true, right: false, bottom: true, left: false },
  corner: { top: true, right: true, bottom: false, left: false },
  empty: { top: false, right: false, bottom: false, left: false },
  start: { top: false, right: true, bottom: false, left: false },
  end: { top: false, right: false, bottom: false, left: true },
};

export class CircuitBreakerGame {
  private state: CircuitBreakerState;
  private timerInterval: number | null = null;
  public onUpdate?: () => void;

  constructor(difficulty: Difficulty = 'medium') {
    const config = this.getDifficultyConfig(difficulty);
    this.state = this.initializeGame(difficulty, config);
  }

  private getDifficultyConfig(difficulty: Difficulty) {
    const configs = {
      easy: { rows: 6, cols: 6, time: 60 },
      medium: { rows: 8, cols: 8, time: 90 },
      hard: { rows: 10, cols: 10, time: 120 },
    };
    return configs[difficulty];
  }

  private initializeGame(difficulty: Difficulty, config: any): CircuitBreakerState {
    const grid = this.generatePuzzle(config.rows, config.cols);
    const startPos = { row: 0, col: 0 };
    const endPos = { row: config.rows - 1, col: config.cols - 1 };

    return {
      grid,
      rows: config.rows,
      cols: config.cols,
      startPos,
      endPos,
      isComplete: false,
      moves: 0,
      timeRemaining: config.time,
      maxTime: config.time,
      gameStatus: 'idle',
      difficulty,
    };
  }

  private generatePuzzle(rows: number, cols: number): Tile[][] {
    const grid: Tile[][] = [];

    // Initialize grid
    for (let r = 0; r < rows; r++) {
      grid[r] = [];
      for (let c = 0; c < cols; c++) {
        grid[r][c] = {
          row: r,
          col: c,
          type: 'straight',
          rotation: 0,
          isPowered: false,
        };
      }
    }

    // Place start and end
    grid[0][0].type = 'start';
    grid[rows - 1][cols - 1].type = 'end';

    // Generate a valid path from start to end
    this.generatePath(grid, 0, 0, rows - 1, cols - 1);

    // Randomize rotations
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (grid[r][c].type !== 'start' && grid[r][c].type !== 'end') {
          const rotations = [0, 90, 180, 270] as const;
          grid[r][c].rotation = rotations[Math.floor(Math.random() * rotations.length)];
        }
      }
    }

    return grid;
  }

  private generatePath(
    grid: Tile[][],
    startRow: number,
    startCol: number,
    endRow: number,
    endCol: number
  ): void {
    let currentRow = startRow;
    let currentCol = startCol + 1;

    // Simple right-then-down path
    while (currentCol < endCol) {
      grid[currentRow][currentCol].type = 'straight';
      currentCol++;
    }

    while (currentRow < endRow) {
      if (currentRow + 1 < endRow || currentCol === endCol) {
        grid[currentRow][currentCol].type = currentRow === startRow ? 'corner' : 'straight';
      }
      currentRow++;
    }
  }

  private getRotatedConnections(type: TileType, rotation: number): TileConnections {
    const base = { ...TILE_CONNECTIONS[type] };
    if (rotation === 0) return base;

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

  public rotateTile(row: number, col: number): void {
    if (this.state.gameStatus !== 'playing') return;

    const tile = this.state.grid[row][col];
    if (tile.type === 'start' || tile.type === 'end') return;

    tile.rotation = ((tile.rotation + 90) % 360) as 0 | 90 | 180 | 270;
    this.state.moves++;

    this.updatePowerFlow();
    this.checkComplete();
    this.notifyUpdate();
  }

  private updatePowerFlow(): void {
    // Reset all tiles
    for (const row of this.state.grid) {
      for (const tile of row) {
        tile.isPowered = false;
      }
    }

    // Trace from start
    const visited = new Set<string>();
    const queue: { row: number; col: number }[] = [this.state.startPos];

    while (queue.length > 0) {
      const current = queue.shift()!;
      const key = `${current.row},${current.col}`;

      if (visited.has(key)) continue;
      visited.add(key);

      const tile = this.state.grid[current.row][current.col];
      tile.isPowered = true;

      const connections = this.getRotatedConnections(tile.type, tile.rotation);

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

        if (nr < 0 || nr >= this.state.rows || nc < 0 || nc >= this.state.cols) continue;

        const neighbor = this.state.grid[nr][nc];
        const neighborKey = `${nr},${nc}`;

        if (visited.has(neighborKey)) continue;

        const neighborConnections = this.getRotatedConnections(neighbor.type, neighbor.rotation);

        if (neighborConnections[opposite as keyof TileConnections]) {
          queue.push({ row: nr, col: nc });
        }
      }
    }
  }

  private checkComplete(): void {
    const endTile = this.state.grid[this.state.endPos.row][this.state.endPos.col];

    if (endTile.isPowered) {
      this.state.isComplete = true;
      this.state.gameStatus = 'won';
      this.stopTimer();
    }
  }

  public startTimer(): void {
    if (this.timerInterval) return;

    this.state.gameStatus = 'playing';

    this.timerInterval = window.setInterval(() => {
      if (this.state.timeRemaining > 0) {
        this.state.timeRemaining--;
        this.notifyUpdate();

        if (this.state.timeRemaining === 0 && this.state.gameStatus === 'playing') {
          this.state.gameStatus = 'lost';
          this.stopTimer();
          this.notifyUpdate();
        }
      }
    }, 1000);
  }

  public stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  public reset(): void {
    this.stopTimer();
    const config = this.getDifficultyConfig(this.state.difficulty);
    this.state = this.initializeGame(this.state.difficulty, config);
    this.notifyUpdate();
  }

  public getState(): Readonly<CircuitBreakerState> {
    return {
      ...this.state,
      grid: this.state.grid.map(row => row.map(tile => ({ ...tile }))),
    };
  }

  private notifyUpdate(): void {
    if (this.onUpdate) {
      this.onUpdate();
    }
  }

  public destroy(): void {
    this.stopTimer();
  }
}
