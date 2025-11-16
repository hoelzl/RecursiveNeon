# Hacking Minigames - Overview

> **Last Updated**: 2025-11-16
> **Project**: Recursive://Neon
> **Purpose**: Overview of hacking-themed minigames

---

## Introduction

This document provides an overview of the hacking-themed minigames integrated into RecursiveNeon. These minigames simulate various hacking activities and provide engaging challenges for players.

## Games List

### Terminal Games

1. **CodeBreaker** - A Bulls & Cows / Wordle variant where players guess hexadecimal codes
2. **MemoryDump** - A Fallout-style word-matching game in a grid of characters and symbols

### Graphical Games

3. **PortScanner** - A Minesweeper-inspired game to identify open ports on a network
4. **CircuitBreaker** - Connect circuit nodes before time runs out

## Design Philosophy

All minigames follow these principles:

- **Thematic**: Each game relates to real hacking/cybersecurity concepts
- **Accessible**: Simple to learn, challenging to master
- **Integrated**: Can be launched from the desktop or terminal
- **Safe**: Error boundaries prevent crashes from affecting the main application
- **Tested**: Comprehensive test coverage ensures reliability

## Integration Points

- **Terminal Commands**: `codebreaker`, `memorydump` for terminal games
- **Desktop Icons**: Graphical games available as desktop applications
- **Error Handling**: All games wrapped in error boundaries
- **State Management**: Games manage their own state independently

## Documentation Structure

Each game has two documents:

1. **Requirements Document** (`{game}-requirements.md`):
   - Game mechanics
   - Win/lose conditions
   - User interface requirements
   - Acceptance criteria

2. **Design Document** (`{game}-design.md`):
   - Technical architecture
   - Component structure
   - State management
   - Implementation details

---

See individual game documents for detailed specifications.
