"""
Shared configuration and utilities for LaserBench puzzle generation and testing.
"""

from typing import Literal

Direction = Literal["right", "left", "up", "down"]
Edge = Literal["top", "bottom", "left", "right"]

PUZZLE_CONFIG = {
    "small": {"rows": (5, 6), "cols": (6, 8), "mirrors": (4, 6), "min_bounces": 3},
    "medium": {"rows": (7, 9), "cols": (9, 12), "mirrors": (7, 10), "min_bounces": 5},
    "large": {"rows": (10, 12), "cols": (13, 16), "mirrors": (18, 24), "min_bounces": 8},
}

SYSTEM_PROMPT = """You are solving a laser mirror puzzle. You must trace the path of a laser beam through a grid.

## Rules:
1. The laser enters from the LEFT edge at the row marked with '>' arrow
2. The laser travels in straight lines
3. When the laser hits a mirror, it bounces 90 degrees:
   - '/' mirror: reflects like a real mirror at 45 degrees
   - '\\' mirror: reflects like a real mirror at 45 degrees (opposite direction)
4. The laser exits when it leaves the grid boundaries
5. Empty cells '.' do not affect the laser - it passes straight through

## Grid Coordinates:
- Rows are numbered 1, 2, 3, ... from top to bottom
- Columns are labeled A, B, C, ... from left to right

## Mirror Behavior Examples:

Example 1: '/' mirror
```
  → → /      The laser coming from the left hits '/' and bounces UP
        ↑
```
- Laser going RIGHT hits '/' → bounces UP
- Laser going LEFT hits '/' → bounces DOWN
- Laser going UP hits '/' → bounces RIGHT
- Laser going DOWN hits '/' → bounces LEFT

Example 2: '\\' mirror
```
  → → \\     The laser coming from the left hits '\\' and bounces DOWN
        ↓
```
- Laser going RIGHT hits '\\' → bounces DOWN
- Laser going LEFT hits '\\' → bounces UP
- Laser going UP hits '\\' → bounces LEFT
- Laser going DOWN hits '\\' → bounces RIGHT

## Worked Example:

```
    A B C D E
  +-----------+
 1| .  .  .  . |
 2| .  /  .  . |
 3|>.  .  \\  . |
 4| .  .  .  . |
  +-----------+
```

Tracing the laser:
1. Laser enters at row 3, column A, moving RIGHT
2. Passes through (3,A), (3,B) - empty cells
3. Hits '\\' at (3,C) - bounces DOWN
4. Moves to (4,C) - empty cell
5. Exits BOTTOM edge at column C

Answer: bottom edge, column C

## Your Task:
Trace the laser path step by step, then provide your answer in the exact JSON format specified."""


def build_prompt(puzzle_ascii: str) -> str:
    """Build the user prompt for a puzzle."""
    return f"""Solve this laser mirror puzzle:

{puzzle_ascii}

Rows are numbered 1, 2, 3, ... from top. Columns are labeled A, B, C, ... from left.

First, trace the laser path step by step, showing each cell the laser passes through and any direction changes at mirrors.

Then provide your final answer as JSON in exactly this format:
```json
{{"edge": "<top|bottom|left|right>", "position": "<row number or column letter>"}}
```

Where:
- "edge" is which edge the laser exits from (top, bottom, left, or right)
- "position" is the row number (for left/right exits) or column letter (for top/bottom exits)"""
