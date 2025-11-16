/**
 * PortScanner Game Logic
 *
 * A Minesweeper-inspired game where players identify open ports on a network.
 * Pure TypeScript class with no UI dependencies for easy testing.
 */

export type Difficulty = 'easy' | 'medium' | 'hard';
export type GameStatus = 'idle' | 'playing' | 'won' | 'lost';

export interface GridCell {
  row: number;
  col: number;
  isOpenPort: boolean;
  isRevealed: boolean;
  isFlagged: boolean;
  adjacentPorts: number; // 0-8
}

export interface PortScannerState {
  grid: GridCell[][];
  rows: number;
  cols: number;
  openPorts: number;
  revealedCount: number;
  flaggedCount: number;
  score: number;
  gameStatus: GameStatus;
  difficulty: Difficulty;
  startTime: number | null;
  endTime: number | null;
  firstClick: boolean;
}

interface DifficultyConfig {
  rows: number;
  cols: number;
  ports: number;
}

export class PortScannerGame {
  private state: PortScannerState;
  private config: DifficultyConfig;
  public onUpdate?: () => void;

  constructor(difficulty: Difficulty = 'medium') {
    this.config = this.getDifficultyConfig(difficulty);
    this.state = this.initializeGame(difficulty);
  }

  private getDifficultyConfig(difficulty: Difficulty): DifficultyConfig {
    const configs: Record<Difficulty, DifficultyConfig> = {
      easy: { rows: 8, cols: 8, ports: 10 },
      medium: { rows: 10, cols: 10, ports: 15 },
      hard: { rows: 12, cols: 12, ports: 20 },
    };
    return configs[difficulty];
  }

  private initializeGame(difficulty: Difficulty): PortScannerState {
    const grid = this.generateGrid(this.config.rows, this.config.cols, this.config.ports);

    return {
      grid,
      rows: this.config.rows,
      cols: this.config.cols,
      openPorts: this.config.ports,
      revealedCount: 0,
      flaggedCount: 0,
      score: 0,
      gameStatus: 'idle',
      difficulty,
      startTime: null,
      endTime: null,
      firstClick: true,
    };
  }

  private generateGrid(rows: number, cols: number, portCount: number): GridCell[][] {
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
    this.calculateAdjacency(grid);

    return grid;
  }

  private calculateAdjacency(grid: GridCell[][]): void {
    const rows = grid.length;
    const cols = grid[0].length;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (!grid[r][c].isOpenPort) {
          grid[r][c].adjacentPorts = this.countAdjacentPorts(grid, r, c);
        }
      }
    }
  }

  private countAdjacentPorts(grid: GridCell[][], row: number, col: number): number {
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

  private ensureFirstClickSafe(row: number, col: number): void {
    const cell = this.state.grid[row][col];

    // If first click is on a port or adjacent to one, move the ports
    if (cell.isOpenPort || cell.adjacentPorts > 0) {
      // Find a safe location (no port, no adjacent ports)
      for (let r = 0; r < this.state.rows; r++) {
        for (let c = 0; c < this.state.cols; c++) {
          if (r === row && c === col) continue;

          const candidate = this.state.grid[r][c];
          const adjacentCount = this.countAdjacentPorts(this.state.grid, r, c);

          if (!candidate.isOpenPort && adjacentCount === 0) {
            // Move port from clicked cell to safe location
            if (cell.isOpenPort) {
              cell.isOpenPort = false;
              candidate.isOpenPort = true;
            }

            // Recalculate adjacency
            this.calculateAdjacency(this.state.grid);
            return;
          }
        }
      }

      // If no perfect safe spot found, just move the port away
      if (cell.isOpenPort) {
        cell.isOpenPort = false;
        this.calculateAdjacency(this.state.grid);
      }
    }
  }

  /**
   * Reveal a cell at the given position
   */
  public revealCell(row: number, col: number): {
    success: boolean;
    hitPort: boolean;
    autoRevealed: GridCell[];
  } {
    if (this.state.gameStatus === 'lost' || this.state.gameStatus === 'won') {
      return { success: false, hitPort: false, autoRevealed: [] };
    }

    const cell = this.state.grid[row][col];

    if (cell.isRevealed || cell.isFlagged) {
      return { success: false, hitPort: false, autoRevealed: [] };
    }

    // Start game on first click
    if (this.state.firstClick) {
      this.ensureFirstClickSafe(row, col);
      this.state.firstClick = false;
      this.state.startTime = Date.now();
      this.state.gameStatus = 'playing';
    }

    cell.isRevealed = true;
    this.state.revealedCount++;

    // Hit open port!
    if (cell.isOpenPort) {
      this.state.score += 10;
      this.checkWinCondition();
      this.notifyUpdate();
      return { success: true, hitPort: true, autoRevealed: [] };
    }

    // Auto-reveal if zero adjacent
    let autoRevealed: GridCell[] = [];
    if (cell.adjacentPorts === 0) {
      autoRevealed = this.autoRevealAdjacent(row, col);
    }

    this.checkWinCondition();
    this.notifyUpdate();
    return { success: true, hitPort: false, autoRevealed };
  }

  private autoRevealAdjacent(row: number, col: number): GridCell[] {
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

          if (nr < 0 || nr >= this.state.rows || nc < 0 || nc >= this.state.cols) {
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

  /**
   * Toggle flag on a cell
   */
  public toggleFlag(row: number, col: number): boolean {
    if (this.state.gameStatus === 'lost' || this.state.gameStatus === 'won') {
      return false;
    }

    const cell = this.state.grid[row][col];

    if (cell.isRevealed) {
      return false;
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
        this.state.score -= 5; // Penalty for incorrect flag removal
      }
    }

    this.checkWinCondition();
    this.notifyUpdate();
    return true;
  }

  private checkWinCondition(): void {
    // Win if all open ports are either revealed or flagged
    let foundPorts = 0;
    const totalPorts = this.state.openPorts;

    for (const row of this.state.grid) {
      for (const cell of row) {
        if (cell.isOpenPort && (cell.isRevealed || cell.isFlagged)) {
          foundPorts++;
        }
      }
    }

    if (foundPorts === totalPorts) {
      this.state.gameStatus = 'won';
      this.state.endTime = Date.now();

      // Time bonus
      if (this.state.startTime) {
        const timeSeconds = Math.floor((this.state.endTime - this.state.startTime) / 1000);
        this.state.score += Math.max(0, 300 - timeSeconds);
      }

      this.notifyUpdate();
    }
  }

  /**
   * Reset/restart the game
   */
  public reset(): void {
    this.state = this.initializeGame(this.state.difficulty);
    this.notifyUpdate();
  }

  /**
   * Get current game state (immutable)
   */
  public getState(): Readonly<PortScannerState> {
    return {
      ...this.state,
      grid: this.state.grid.map(row => row.map(cell => ({ ...cell }))),
    };
  }

  private notifyUpdate(): void {
    if (this.onUpdate) {
      this.onUpdate();
    }
  }
}
