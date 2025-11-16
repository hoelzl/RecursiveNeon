# CircuitBreaker - Requirements Document

> **Game Type**: Graphical (Desktop App)
> **Difficulty**: Medium
> **Theme**: Circuit connection and network routing

---

## Overview

CircuitBreaker is a fast-paced puzzle game where players must connect circuit nodes by rotating connection pieces before time runs out. Similar to pipe-connection games, players rotate tiles to create a path from the start node to the end node.

## Game Mechanics

### Setup

- Grid of circuit tiles (e.g., 6×6 or 8×8)
- Each tile contains connection paths (straight, corner, T-junction, cross)
- One or more starting nodes (power sources)
- One or more ending nodes (targets)
- Random initial tile rotations
- Time limit (30-90 seconds depending on difficulty)

### Tile Types

1. **Straight**: `═` or `║` - Connects two opposite sides
2. **Corner**: `╔` `╗` `╚` `╝` - Connects two adjacent sides (90° turn)
3. **T-Junction**: `╠` `╣` `╦` `╩` - Connects three sides
4. **Cross**: `╬` - Connects all four sides
5. **Empty**: No connections (rare, used as obstacles)
6. **Start Node**: `◉` - Power source (green)
7. **End Node**: `◎` - Target (blue)

### Gameplay

1. Player clicks a tile to rotate it 90° clockwise
2. Tiles can be rotated unlimited times
3. When a path connects start to end, that circuit is "completed"
4. All circuits must be completed to win
5. Timer counts down
6. Game ends when timer reaches zero or all circuits completed

### Path Validation

- Connections must be physically adjacent (share an edge)
- Both tiles must have paths on the connected edges
- Multiple overlapping paths are allowed (cross tiles)
- Dead ends are acceptable but don't contribute to solution

## Win/Lose Conditions

### Win Condition

Player connects all start nodes to their corresponding end nodes before time expires

**Win Message**:
```
⚡ CIRCUITS CONNECTED ⚡
All nodes powered successfully!
Time remaining: {time}s
Moves: {moves}
```

### Lose Condition

Timer reaches zero before all circuits are connected

**Lose Message**:
```
⌛ CONNECTION TIMEOUT ⌛
Circuit incomplete. System offline.
Circuits completed: {completed}/{total}
```

## User Interface Requirements

### Grid Display

```
┌─────────────────────────────────┐
│  CircuitBreaker v1.0            │
│  Time: 45s  Moves: 12           │
│  Circuits: 1/2 Complete         │
├─────────────────────────────────┤
│                                 │
│   ◉──╗  ║  ╚══╗  ╔══◎          │
│      ║  ║     ║  ║              │
│   ╔══╝  ╚═╗  ╔╝  ║              │
│   ║       ║  ║   ║              │
│   ╚═══════╝  ╚═══╝              │
│                                 │
└─────────────────────────────────┘
```

### Visual Elements

**Active/Powered Paths**:
- Connected paths glow/pulse
- Color indicates which circuit (green→blue for circuit 1, etc.)
- Animation flows from start to end

**Unpowered Paths**:
- Gray or dim color
- No animation

**Tiles**:
- Clickable with hover effect
- Rotation animation (smooth 90° spin)
- Clear connection points

### HUD

- **Timer**: Large, prominent countdown
- **Move counter**: Number of rotations made
- **Circuit status**: "N/M Complete" with visual indicators
- **Reset button**: Start over with same configuration
- **New Game button**: Generate new puzzle

### Color Scheme

- Background: Dark (#1a1a2e)
- Inactive paths: Gray (#555555)
- Circuit 1 (powered): Green (#00ff00) to Cyan (#00ffff) gradient
- Circuit 2 (powered): Blue (#0099ff) to Purple (#9900ff) gradient
- Start nodes: Bright green glow
- End nodes: Bright blue/cyan glow
- Timer (warning): Yellow < 15s, Red < 5s

## Difficulty Modes

### Easy
- 6×6 grid
- 1 circuit
- Simple tile types (mostly straight and corners)
- 60 seconds
- Guaranteed solvable

### Medium
- 8×8 grid
- 2 circuits
- All tile types
- 90 seconds
- Guaranteed solvable

### Hard
- 10×10 grid
- 3 circuits
- All tile types including obstacles
- 120 seconds
- Minimal redundant tiles

## Scoring System (Optional)

- **Base points**: 100 per circuit
- **Time bonus**: +1 point per second remaining
- **Move efficiency**: Bonus for completing with fewer moves
- **Perfect solve**: All circuits + time remaining > 50%

## Acceptance Criteria

- [ ] Grid generates with correct tile distribution
- [ ] Tiles rotate 90° on click
- [ ] Path validation works correctly
- [ ] Visual feedback shows active circuits
- [ ] Timer counts down accurately
- [ ] Win condition detected when all circuits complete
- [ ] Lose condition triggered on timeout
- [ ] Puzzle is always solvable
- [ ] Rotation animations are smooth
- [ ] Game can be reset/restarted

## Edge Cases

1. **Multiple valid solutions**: Accept any working configuration
2. **Tiles with no impact**: Empty tiles or isolated pieces are okay
3. **Overlapping circuits**: Two circuits can share tiles (crosses)
4. **Instant win**: If generated puzzle is already solved, regenerate
5. **Impossible puzzle**: Generation algorithm must ensure solvability

## Algorithm Requirements

### Puzzle Generation

The puzzle generator must:
1. Place start and end nodes
2. Generate a valid solution path
3. Add additional tiles for complexity
4. Randomize all tile rotations
5. Verify puzzle is still solvable
6. Ensure puzzle isn't trivially simple

### Path Finding

- Use flood-fill or BFS to trace connections
- Start from each power source
- Mark all connected tiles
- Check if end node is reachable

## Non-Functional Requirements

- Smooth 60 FPS animations
- Responsive to clicks (< 50ms)
- Puzzle generation < 1 second
- Visual feedback immediate
- Works on different screen sizes

## Accessibility

- Keyboard controls (arrows to navigate, space to rotate)
- High contrast mode
- Screen reader support
- Colorblind-friendly (use different patterns per circuit)
- Adjustable time limits

---

## User Stories

**As a player**, I want to:
- Quickly understand how tiles connect
- See which paths are active/powered
- Know how much time I have left
- Feel satisfaction when circuits complete
- Restart easily if stuck
- Try different difficulty levels

**As a developer**, I need:
- Efficient path-finding algorithm
- Puzzle generation that guarantees solvability
- Clean state management
- Smooth animations
- Comprehensive tests
- Error boundary protection

---

## Inspiration

Games like Pipe Mania, NetWalk, and similar connection puzzles, but with a cyberpunk circuit theme and time pressure for added excitement.
