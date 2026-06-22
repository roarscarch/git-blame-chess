# Git Blame Chess

> Play chess with your git history

A CLI tool that turns your Git repository into a chess game where each commit is a move, and you can play through the development history or let two branches battle.

## Stack
- Language: **python**
- gitpython, chess

## Features
- Parse any Git repo into a chess game graph (commits as board states, diffs as moves)
- Blame-aware move generation: files changed = pieces moved, lines changed = captures
- Play through history interactively in the terminal with colored board output
- Branch duel mode: two branches play against each other, merging at conflict points
- Export the game as a PGN file for analysis in any chess GUI

## Architecture
The key insight is mapping each file in the repo to a chess piece type based on its extension, and each line diff to a piece move, using a deterministic hash of the file path and line number as the board coordinate.

## Getting Started
```bash
# Coming soon — this project is under active development.
```

*Built fresh every day by an AI-powered automation pipeline.*
