#!/usr/bin/env python3
# To run this code you need to install the following dependencies:
# pip install google-genai python-dotenv matplotlib

import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")


# ============== Puzzle Generation ==============

Direction = Literal["right", "left", "up", "down"]
Edge = Literal["top", "bottom", "left", "right"]

PUZZLE_CONFIG = {
    "small": {"rows": (5, 6), "cols": (6, 8), "mirrors": (4, 6)},
    "medium": {"rows": (7, 9), "cols": (9, 12), "mirrors": (7, 10)},
    "large": {"rows": (10, 12), "cols": (13, 16), "mirrors": (12, 16)},
}


def generate_grid(rows: int, cols: int, mirror_count: int) -> list[list[str]]:
    grid = [["." for _ in range(cols)] for _ in range(rows)]
    placed = 0
    while placed < mirror_count:
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        if grid[r][c] == ".":
            grid[r][c] = "/" if random.random() < 0.5 else "\\"
            placed += 1
    return grid


def get_next_direction(current: Direction, mirror: str) -> Direction:
    if mirror == "/":
        return {"right": "up", "left": "down", "up": "right", "down": "left"}[current]
    else:  # mirror == "\\"
        return {"right": "down", "left": "up", "up": "left", "down": "right"}[current]


def col_to_letter(col: int) -> str:
    """Convert column number (1-indexed) to letter (A, B, C, ... Z, AA, AB, ...)."""
    result = ""
    while col > 0:
        col -= 1
        result = chr(ord("A") + (col % 26)) + result
        col //= 26
    return result


def simulate_laser(
    grid: list[list[str]], start_row: int, start_direction: Direction = "right"
) -> dict:
    rows = len(grid)
    cols = len(grid[0])
    path = []

    row = start_row
    col = 0
    direction = start_direction

    while True:
        if row < 0:
            return {"path": path, "exit": {"edge": "top", "position": col_to_letter(col + 1)}}
        if row >= rows:
            return {"path": path, "exit": {"edge": "bottom", "position": col_to_letter(col + 1)}}
        if col < 0:
            return {"path": path, "exit": {"edge": "left", "position": row + 1}}
        if col >= cols:
            return {"path": path, "exit": {"edge": "right", "position": row + 1}}

        path.append({"row": row, "col": col, "direction": direction})

        cell = grid[row][col]
        if cell in ["/", "\\"]:
            direction = get_next_direction(direction, cell)

        if direction == "right":
            col += 1
        elif direction == "left":
            col -= 1
        elif direction == "up":
            row -= 1
        elif direction == "down":
            row += 1

        if len(path) > 1000:
            break

    return {"path": path, "exit": {"edge": "right", "position": 1}}


def generate_puzzle_ascii(grid: list[list[str]], start_row: int) -> str:
    rows = len(grid)
    cols = len(grid[0])

    # Header with column letters
    output = "    "
    for c in range(1, cols + 1):
        output += col_to_letter(c) + " "
    output += "\n"

    # Top border
    output += "  +" + "-" * (cols * 2 + 1) + "+\n"

    # Grid rows
    for r in range(rows):
        row_num = str(r + 1)
        if len(row_num) == 1:
            row_num = " " + row_num
        arrow = ">" if r == start_row else " "
        output += f"{row_num}|{arrow}"

        for c in range(cols):
            output += grid[r][c] + " "
        output += "|\n"

    # Bottom border
    output += "  +" + "-" * (cols * 2 + 1) + "+"

    return output


def generate_puzzle(size: str = "large") -> dict:
    config = PUZZLE_CONFIG[size]
    rows = random.randint(config["rows"][0], config["rows"][1])
    cols = random.randint(config["cols"][0], config["cols"][1])
    mirror_count = random.randint(config["mirrors"][0], config["mirrors"][1])

    grid = generate_grid(rows, cols, mirror_count)
    start_row = random.randint(0, rows - 1)
    result = simulate_laser(grid, start_row)

    return {
        "grid": grid,
        "start_row": start_row,
        "ascii": generate_puzzle_ascii(grid, start_row),
        "answer": result["exit"],
        "path_length": len(result["path"]),
    }


# ============== Prompt Construction ==============

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


# ============== Testing ==============


def parse_llm_response(response: str) -> dict | None:
    """Extract the JSON answer from the LLM response."""
    # Try to find JSON in code block
    json_match = re.search(r"```json\s*(\{[^}]+\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON (position can be number or string)
    json_match = re.search(r'\{"edge":\s*"[^"]+",\s*"position":\s*(?:\d+|"[^"]+")\}', response)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def normalize_position(pos) -> str:
    """Normalize position to string for comparison."""
    if isinstance(pos, int):
        return str(pos)
    return str(pos).upper()


def test_model(puzzle: dict, client: genai.Client, model: str) -> dict:
    """Test a single puzzle against a model."""
    prompt = build_prompt(puzzle["ascii"])

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.1,
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        response_text = response.text or ""
    except Exception as e:
        print(f"  Error: {e}")
        response_text = ""

    parsed = parse_llm_response(response_text)

    correct = False
    if parsed:
        expected_pos = normalize_position(puzzle["answer"]["position"])
        llm_pos = normalize_position(parsed.get("position", ""))
        correct = (
            parsed.get("edge") == puzzle["answer"]["edge"]
            and llm_pos == expected_pos
        )

    return {
        "puzzle_ascii": puzzle["ascii"],
        "expected": puzzle["answer"],
        "llm_answer": parsed,
        "correct": correct,
        "response": response_text,
        "path_length": puzzle["path_length"],
    }


def run_multi_model_benchmark(
    models: list[str],
    num_puzzles: int = 20,
    size: str = "large"
) -> dict:
    """Run benchmark across multiple models with the same puzzles."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        print("Please create a .env file in the project root with:")
        print("  GEMINI_API_KEY=your-api-key-here")
        return {}

    client = genai.Client(api_key=api_key)

    # Generate puzzles once - same puzzles for all models
    print(f"Generating {num_puzzles} {size} puzzles...")
    puzzles = [generate_puzzle(size) for _ in range(num_puzzles)]

    all_results = {}

    for model in models:
        print(f"\n{'='*60}")
        print(f"Testing model: {model}")
        print(f"{'='*60}")

        results = []
        correct_count = 0

        for i, puzzle in enumerate(puzzles):
            print(f"  Puzzle {i + 1}/{num_puzzles}...", end=" ", flush=True)

            result = test_model(puzzle, client, model)
            results.append(result)

            if result["correct"]:
                correct_count += 1
                print("✓")
            else:
                print("✗")

        accuracy = correct_count / num_puzzles
        print(f"\n{model}: {correct_count}/{num_puzzles} ({accuracy*100:.1f}%)")

        all_results[model] = {
            "correct": correct_count,
            "total": num_puzzles,
            "accuracy": accuracy,
            "results": results,
        }

    return all_results


def plot_results(all_results: dict, output_path: Path):
    """Generate a bar chart of model accuracies."""
    models = list(all_results.keys())
    accuracies = [all_results[m]["accuracy"] * 100 for m in models]

    # Shorten model names for display
    display_names = []
    for m in models:
        name = m.replace("models/", "").replace("-preview", "")
        display_names.append(name)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Color bars by accuracy
    colors = ['#ef4444' if a < 50 else '#f59e0b' if a < 75 else '#22c55e' for a in accuracies]

    bars = ax.bar(display_names, accuracies, color=colors, edgecolor='black', linewidth=1.2)

    # Add value labels on bars
    for bar, acc in zip(bars, accuracies):
        height = bar.get_height()
        ax.annotate(f'{acc:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=12, fontweight='bold')

    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_xlabel('Model', fontsize=12)
    ax.set_title('LaserBench: Gemini Model Comparison\n(Large puzzles, 20 trials each)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 105)
    ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5, label='Random baseline')

    # Rotate x labels if needed
    plt.xticks(rotation=25, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to {output_path}")
    plt.close()


def main():
    models = [
        "models/gemini-2.5-pro",
        "models/gemini-3-pro-preview",
        "models/gemini-flash-latest",
        "models/gemini-flash-lite-latest",
    ]

    num_puzzles = 20
    size = "large"

    print("=" * 60)
    print("LaserBench - Multi-Model Benchmark")
    print("=" * 60)
    print(f"Models: {len(models)}")
    print(f"Puzzles per model: {num_puzzles}")
    print(f"Puzzle size: {size}")
    print("=" * 60)

    all_results = run_multi_model_benchmark(models, num_puzzles, size)

    if not all_results:
        return

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    results_path = results_dir / f"benchmark_{timestamp}.json"
    with open(results_path, "w") as f:
        # Remove response text to keep file smaller
        save_results = {}
        for model, data in all_results.items():
            save_results[model] = {
                "correct": data["correct"],
                "total": data["total"],
                "accuracy": data["accuracy"],
                "results": [
                    {
                        "expected": r["expected"],
                        "llm_answer": r["llm_answer"],
                        "correct": r["correct"],
                        "path_length": r["path_length"],
                    }
                    for r in data["results"]
                ],
            }
        json.dump(save_results, f, indent=2)
    print(f"\nResults saved to {results_path}")

    # Generate plot
    plot_path = results_dir / f"benchmark_{timestamp}.png"
    plot_results(all_results, plot_path)

    # Print summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    for model in models:
        data = all_results[model]
        print(f"{model}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")


if __name__ == "__main__":
    main()
