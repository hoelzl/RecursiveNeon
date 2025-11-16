# CodeBreaker - Requirements Document

> **Game Type**: Terminal
> **Difficulty**: Easy - Medium
> **Theme**: Hexadecimal code cracking

---

## Overview

CodeBreaker is a terminal-based code-guessing game inspired by Bulls & Cows and Wordle. Players attempt to guess a 4-character hexadecimal code through logical deduction based on feedback.

## Game Mechanics

### Setup

- System generates a random 4-character hexadecimal code (0-9, A-F)
- Code characters may repeat (e.g., "CAFE", "DEAD", "1337", "AAAA")
- Player has 10 attempts to guess the code

### Gameplay

1. Player enters a 4-character hex code
2. System provides feedback:
   - **Exact matches**: Characters in the correct position (shown in GREEN)
   - **Partial matches**: Correct characters in wrong position (shown in YELLOW)
   - **Misses**: Characters not in the code (shown in GRAY)

3. Player uses feedback to make informed guesses
4. Process repeats until win/lose condition met

### Input Validation

- Only accept 4-character inputs
- Only accept valid hex characters (0-9, A-F, case-insensitive)
- Reject invalid inputs with helpful error messages

## Win/Lose Conditions

### Win Condition

Player guesses the exact code (all 4 characters correct and in correct positions)

**Win Message**:
```
🎉 ACCESS GRANTED 🎉
Code cracked in {attempts} attempts!
The code was: {code}
```

### Lose Condition

Player exhausts all 10 attempts without guessing correctly

**Lose Message**:
```
❌ ACCESS DENIED ❌
System locked. The code was: {code}
Better luck next time, hacker.
```

## User Interface Requirements

### Terminal Display

```
╔══════════════════════════════════════╗
║       CODEBREAKER v1.0              ║
║   Crack the 4-digit hex code        ║
╚══════════════════════════════════════╝

Attempts remaining: 8/10

Previous guesses:
  1. CAFE  ✓✗✗⚬  (1 exact, 1 partial)
  2. DEAD  ✗✗⚬⚬  (2 partial)

Enter your guess (4 hex digits): _
```

### Feedback Symbols

- `✓` or GREEN background: Correct position
- `⚬` or YELLOW background: Wrong position
- `✗` or GRAY background: Not in code

### Color Coding (if terminal supports)

- Green: Exact match
- Yellow: Partial match
- Gray/Dark: Miss

## Difficulty Modes (Optional Enhancement)

### Easy Mode
- 5 characters: 0-9 only (decimal)
- 12 attempts

### Medium Mode (Default)
- 4 characters: 0-9, A-F (hex)
- 10 attempts

### Hard Mode
- 6 characters: 0-9, A-F (hex)
- 8 attempts

## Acceptance Criteria

- [ ] Game generates random valid hex codes
- [ ] Input validation works correctly
- [ ] Feedback accurately shows exact/partial/miss
- [ ] Win condition detected correctly
- [ ] Lose condition detected after 10 attempts
- [ ] Game can be restarted
- [ ] Display is clear and easy to read
- [ ] Color coding works in supported terminals
- [ ] Invalid input doesn't count as an attempt
- [ ] Case-insensitive input handling

## Edge Cases

1. **Repeated characters in code**: e.g., "AAAA"
   - Guess "AAAB" should show 3 exact, 0 partial, 1 miss

2. **Repeated characters in guess**: e.g., Code "ABCD", Guess "AAAA"
   - Should show 1 exact (first A), 3 misses

3. **All wrong**: Guess shares no characters with code
   - Should show 4 misses

4. **All partial**: All characters correct but in wrong positions
   - Should show 4 partial matches

## Non-Functional Requirements

- Response time: < 100ms for feedback
- Memory efficient: No history beyond current game
- Accessible: Works in any standard terminal
- Testable: All logic unit-testable

---

## User Stories

**As a player**, I want to:
- See clear feedback on each guess so I can deduce the code
- Know how many attempts I have left
- Understand what each symbol/color means
- Play again after winning or losing
- Get hints if I'm stuck (optional)

**As a developer**, I need:
- Deterministic random generation (seedable for testing)
- Clear separation of game logic and UI
- Comprehensive test coverage
- Error boundaries to prevent crashes
