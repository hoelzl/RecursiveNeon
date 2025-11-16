# PortScanner - Requirements Document

> **Game Type**: Graphical (Desktop App)
> **Difficulty**: Easy - Medium
> **Theme**: Network port scanning and enumeration

---

## Overview

PortScanner is a Minesweeper-inspired graphical game where players must identify all "open ports" on a network grid while avoiding "firewalls". Each cell reveals clues about adjacent open ports.

## Game Mechanics

### Setup

- Grid of network nodes (e.g., 8×8, 10×10, or 12×12)
- Random number of "open ports" placed in grid (10-15% of cells)
- Remaining cells are either "closed ports" or contain firewalls
- First click is always safe (no firewall)

### Gameplay

1. Player clicks a cell to scan it
2. Cell reveals one of:
   - **Number (0-8)**: Count of open ports in adjacent cells (including diagonals)
   - **Open Port**: Successfully identified an open port (+10 points)
   - **Firewall**: Triggers firewall alert (-1 life or instant loss)

3. Player can "flag" cells believed to be open ports
4. Game continues until win/lose condition met

### Special Mechanics

**Auto-Reveal**: When a cell with 0 adjacent open ports is clicked, automatically reveal all adjacent safe cells (like Minesweeper)

**Flagging**: Right-click or Ctrl+click to flag a cell as an open port
- Flagged cells cannot be accidentally clicked
- Unflag by clicking again
- Visual indicator (flag icon or special color)

**Lives System** (Optional):
- Player starts with 3 lives
- Hitting a firewall costs 1 life
- Game ends when lives reach 0

## Win/Lose Conditions

### Win Condition

Player successfully identifies (clicks or flags) all open ports without hitting too many firewalls

**Win Message**:
```
✓ NETWORK MAPPED
All open ports identified!
Time: {time}
Score: {score}
```

### Lose Condition

**Hard Mode**: Player clicks a single firewall
**Normal Mode**: Player exhausts all lives (3 firewalls)

**Lose Message**:
```
⚠ FIREWALL TRIGGERED
Intrusion detected. Connection terminated.
Open ports found: {found}/{total}
```

## User Interface Requirements

### Grid Display

```
┌─────────────────────────────┐
│  PortScanner v1.0           │
│  Lives: ♥♥♥  Score: 120     │
├─────────────────────────────┤
│  [?] [?] [1] [0] [0] [1] [?]│
│  [?] [?] [2] [0] [0] [1] [?]│
│  [2] [2] [1] [0] [0] [1] [1]│
│  [⚑] [1] [0] [0] [0] [0] [0]│
│  [1] [1] [0] [1] [1] [1] [0]│
│  [0] [0] [0] [1] [⚑] [1] [0]│
│  [?] [1] [1] [2] [1] [1] [0]│
│  [?] [?] [?] [?] [1] [0] [0]│
└─────────────────────────────┘
```

### Cell States

- **Unrevealed**: `[?]` - Gray background, clickable
- **Number**: `[N]` - Shows count (0-8), different colors for different numbers
- **Open Port**: `[●]` - Green background, port icon
- **Flagged**: `[⚑]` - Blue background, flag icon
- **Firewall (revealed)**: `[✕]` - Red background, warning icon

### Color Scheme

- Background: Dark theme (cyberpunk aesthetic)
- Unrevealed cells: Dark gray (#2a2a2a)
- Revealed empty: Darker (#1a1a1a)
- Numbers: Color-coded (1=blue, 2=green, 3=yellow, 4=orange, 5+=red)
- Open port: Bright green (#00ff00)
- Firewall: Bright red (#ff0000)
- Flagged: Cyan (#00ffff)

### HUD Elements

- **Top bar**:
  - Lives remaining (hearts or icons)
  - Score (points)
  - Timer (optional)
  - Difficulty indicator

- **Bottom bar**:
  - Flag count: "Flags: {used}/{total}"
  - Quick stats: "Ports found: {found}/{total}"
  - Reset button

### Interactions

- **Left click**: Reveal cell
- **Right click** / **Ctrl+click**: Toggle flag
- **Double click** on number: Auto-reveal adjacent cells if enough flags placed
- **Hover**: Highlight cell

## Difficulty Modes

### Easy
- 8×8 grid
- 10 open ports
- 3 lives
- First click guaranteed safe

### Medium
- 10×10 grid
- 15 open ports
- 2 lives
- First click guaranteed safe

### Hard
- 12×12 grid
- 20 open ports
- 1 life (instant fail on firewall)
- First click guaranteed safe

## Scoring System

- **Port found**: +10 points
- **Correct flag placement**: +5 points
- **Incorrect flag removal**: -5 points
- **Time bonus**: +1 point per second remaining (if timed mode)
- **Firewall hit**: -20 points (if lives mode)

## Acceptance Criteria

- [ ] Grid generates correctly with random open ports
- [ ] First click is always safe
- [ ] Number cells show correct count of adjacent ports
- [ ] Auto-reveal works for zero-adjacent cells
- [ ] Flagging prevents accidental clicks
- [ ] Win condition detected correctly
- [ ] Lose condition detected correctly
- [ ] Visual feedback is clear and intuitive
- [ ] Game can be reset/restarted
- [ ] Responsive to mouse input

## Edge Cases

1. **Corner and edge cells**: Correctly count only existing neighbors
2. **First click on open port**: Should reveal it successfully
3. **All adjacent cells are flagged**: Enable double-click reveal
4. **Flagging non-port cells**: Should be allowed but penalized in score
5. **Grid with clusters**: Ensure solvable configuration

## Non-Functional Requirements

- Smooth animations for reveals
- Responsive grid sizing
- Keyboard shortcuts (space for flag, arrows to move)
- Save game state on close (optional)
- Leaderboard/statistics (optional)

## Accessibility

- Clear visual distinctions between states
- Keyboard navigation support
- Screen reader friendly (ARIA labels)
- Colorblind-friendly mode (use symbols + colors)

---

## User Stories

**As a player**, I want to:
- Easily distinguish between different cell states
- Use flags to mark suspected open ports
- Understand the number clues intuitively
- Feel challenged but not frustrated
- Track my progress toward completion
- Restart quickly if I make a mistake

**As a developer**, I need:
- Grid generation algorithm
- Adjacency counting logic
- Clean component structure
- Comprehensive test coverage
- Error boundary protection
