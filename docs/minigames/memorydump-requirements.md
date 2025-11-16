# MemoryDump - Requirements Document

> **Game Type**: Terminal
> **Difficulty**: Medium
> **Theme**: Memory analysis and pattern recognition

---

## Overview

MemoryDump is a terminal-based word-finding game inspired by the Fallout series hacking minigame. Players must identify the correct password from a grid of characters, symbols, and potential words. Selecting incorrect words provides feedback about how many letters match the target password.

## Game Mechanics

### Setup

- System selects a target word from a curated word list (5-8 letters)
- Grid is populated with:
  - Multiple decoy words (same length as target)
  - Random symbols and characters as "garbage"
  - Words are scattered throughout the grid
- Typical grid size: 16-20 rows × 12 columns (2 columns side-by-side)
- Player has 4 attempts to find the correct word

### Word Selection

- All words (target + decoys) must be the same length
- Words should be thematically appropriate (tech, cyber, sci-fi terms)
- Minimum 6-8 possible words in the grid
- Words can appear forwards, may wrap across rows (but not columns)

### Gameplay Loop

1. Player selects a word from the grid by clicking or typing it
2. If incorrect, system provides "likeness" feedback:
   - **Likeness**: Number of letters that match the target word in the same position
   - Example: Target is "PROGRAM", guess is "PROCESS" → Likeness: 3/7 (P, R, O match)
3. Player uses feedback to eliminate possibilities
4. Attempts decrease with each wrong guess
5. Game continues until win/lose condition met

### Special Features (Optional)

**Dud Removers**: Hidden bracket pairs that when selected:
- Remove one incorrect word from the grid
- Or restore one attempt
- Bracket pairs: `[]`, `()`, `{}`, `<>`
- Must be complete pairs (opening and closing on the same line)

Example:
```
#<.TERM>  ← Selecting this pair removes a dud or restores attempt
```

## Win/Lose Conditions

### Win Condition

Player selects the correct password

**Win Message**:
```
>>> ACCESS GRANTED <<<
Entry granted. Password: {password}
System unlocked.
```

### Lose Condition

Player exhausts all 4 attempts without finding the password

**Lose Message**:
```
>>> TERMINAL LOCKED <<<
Intrusion detected. Tracing connection...
The password was: {password}
```

## User Interface Requirements

### Grid Display

```
0x0A40  !@#$ CYBER  ^&*( )!@# S  0x0AC0  YSTEM &*()  !@#$ DATA !
0x0A50  PROBE #$%^ &*() !@#$  P  0x0AD0  ACKET ^&*( )!@#$ %^&*
0x0A60  !@#$ TRACE  ^&*( )!@#  0x0AE0  VIRUS &*()  !@#$ ^&*(
0x0A70  PROXY #$%^ &*() !@#$ R  0x0AF0  OUTER ^&*( )!@#$ %^&*
...
```

### Status Display

```
ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL
ENTER PASSWORD NOW

Attempts Remaining: ███ 1

Selected: CYBER
Likeness: 2/5

Previous Attempts:
> CYBER    Likeness: 2/5
> PROBE    Likeness: 1/5
> TRACE    Likeness: 0/5
```

### Word Selection Interface

**Terminal Mode**:
- Player types the word they want to select
- Case-insensitive matching
- Partial matching not allowed - must type complete word

**Interactive Mode** (if hovering supported):
- Highlight word on hover
- Click or press Enter to select

## Difficulty Modes

### Easy
- 4 letters per word
- 5 attempts
- 6-8 words in grid
- More dud removers (3-4)

### Medium (Default)
- 5-6 letters per word
- 4 attempts
- 8-10 words in grid
- Some dud removers (2-3)

### Hard
- 7-8 letters per word
- 3 attempts
- 10-12 words in grid
- Fewer dud removers (1-2)

## Acceptance Criteria

- [ ] Grid generates correctly with words and garbage
- [ ] All words in grid have same length as target
- [ ] Likeness calculation is accurate
- [ ] Win condition detected on correct word
- [ ] Lose condition triggered after max attempts
- [ ] Words are selectable via typing
- [ ] Dud removers work correctly
- [ ] Grid is visually readable
- [ ] Previous attempts and feedback displayed
- [ ] Game can be restarted

## Edge Cases

1. **Multiple words with same likeness**
   - Player must use process of elimination
   - This is expected behavior

2. **Word wrapping**
   - Words may wrap at end of line to beginning of next
   - Or be split across the two columns

3. **Overlapping bracket pairs**
   - `[()]` contains two pairs: `[]` and `()`
   - Each can only be used once

4. **No valid dud removers**
   - Game should still be winnable through deduction

## Non-Functional Requirements

- Grid generation: < 500ms
- Responsive to input
- Deterministic (same seed → same grid)
- Memory efficient
- No flickering or display issues

## Word Lists

### Tech/Cyber Theme Examples

5-letter words: CYBER, PROXY, VIRUS, PROBE, TRACE, FRAME, PIXEL, LOGIC, ADMIN, DEBUG

6-letter words: SYSTEM, PACKET, ROUTER, HACKER, KERNEL, DAEMON, VECTOR, BINARY, THREAD, SOCKET

7-letter words: PROGRAM, NETWORK, DIGITAL, FIREWALL, PROCESS, GATEWAY, ENCRYPT

8-letter words: TERMINAL, PROTOCOL, DATABASE, PASSWORD, OVERFLOW, BACKBONE

---

## User Stories

**As a player**, I want to:
- Clearly see all words in the grid
- Understand likeness feedback
- Track my previous attempts
- Use dud removers strategically
- Feel challenged but not frustrated

**As a developer**, I need:
- Algorithmic word placement in grid
- Accurate likeness calculation
- Comprehensive test coverage
- Reusable word lists
- Clear separation of logic and display
