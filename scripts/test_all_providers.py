#!/usr/bin/env python3
"""
Multi-provider LLM benchmark for LaserBench.
Tests OpenAI, Anthropic, Google, and Grok models.

pip install google-genai python-dotenv openai anthropic
"""

import json
import os
import random
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from puzzle_config import PUZZLE_CONFIG, SYSTEM_PROMPT, build_prompt, Direction

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent / ".env")


# ============== Puzzle Generation ==============

PORTAL_CELLS = ["1", "2", "3"]
DEGRADING_MIRRORS = {"~": "/", "`": "\\"}  # ~ acts like /, ` acts like \
# Toggle mirrors: [/ [\ start ON (reflecting), ]/ ]\ start OFF (pass-through)
TOGGLE_MIRRORS_ON = {"[/": "/", "[\\": "\\"}
TOGGLE_MIRRORS_OFF = {"]/": "/", "]\\": "\\"}
# Flipping mirrors: {/ {\ rotate 90° each hit
FLIPPING_MIRRORS = {"{/": "/", "{\\": "\\"}


def generate_grid(rows: int, cols: int, mirror_count: int, portal_count: int = 0, mirror_distribution: tuple[int, int, int, int] = (100, 0, 0, 0)) -> list[list[str]]:
    """Generate a grid with mirrors distributed according to percentages.

    mirror_distribution: (normal%, degrading%, toggle%, flipping%)
    """
    grid = [["." for _ in range(cols)] for _ in range(rows)]

    # Calculate mirror counts based on distribution
    normal_pct, degrading_pct, toggle_pct, flipping_pct = mirror_distribution
    total_pct = normal_pct + degrading_pct + toggle_pct + flipping_pct

    normal_count = int(mirror_count * normal_pct / total_pct)
    degrading_count = int(mirror_count * degrading_pct / total_pct)
    toggle_count = int(mirror_count * toggle_pct / total_pct)
    flipping_count = mirror_count - normal_count - degrading_count - toggle_count  # Remainder goes to flipping

    # Place regular mirrors
    placed = 0
    while placed < normal_count:
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        if grid[r][c] == ".":
            grid[r][c] = "/" if random.random() < 0.5 else "\\"
            placed += 1

    # Place degrading mirrors
    placed = 0
    while placed < degrading_count:
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        if grid[r][c] == ".":
            grid[r][c] = "~" if random.random() < 0.5 else "`"
            placed += 1

    # Place toggle mirrors (randomly ON or OFF)
    placed = 0
    while placed < toggle_count:
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        if grid[r][c] == ".":
            mirror_type = "/" if random.random() < 0.5 else "\\"
            start_on = random.random() < 0.5
            if start_on:
                grid[r][c] = "[" + mirror_type  # [/ or [\
            else:
                grid[r][c] = "]" + mirror_type  # ]/ or ]\
            placed += 1

    # Place flipping mirrors
    placed = 0
    while placed < flipping_count:
        r = random.randint(0, rows - 1)
        c = random.randint(0, cols - 1)
        if grid[r][c] == ".":
            grid[r][c] = "{/" if random.random() < 0.5 else "{\\"
            placed += 1

    # Place portal pairs (each portal number appears exactly twice)
    for p in range(min(portal_count, len(PORTAL_CELLS))):
        portal_char = PORTAL_CELLS[p]
        placed_pair = 0
        while placed_pair < 2:
            r = random.randint(0, rows - 1)
            c = random.randint(0, cols - 1)
            if grid[r][c] == ".":
                grid[r][c] = portal_char
                placed_pair += 1

    return grid


def get_next_direction(current: Direction, mirror: str) -> Direction:
    if mirror == "/":
        return {"right": "up", "left": "down", "up": "right", "down": "left"}[current]
    else:
        return {"right": "down", "left": "up", "up": "left", "down": "right"}[current]


def col_to_letter(col: int) -> str:
    result = ""
    while col > 0:
        col -= 1
        result = chr(ord("A") + (col % 26)) + result
        col //= 26
    return result


def find_portal_exit(grid: list[list[str]], portal_char: str, entry_row: int, entry_col: int) -> tuple[int, int] | None:
    """Find the paired portal location."""
    rows = len(grid)
    cols = len(grid[0])
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == portal_char and (r != entry_row or c != entry_col):
                return (r, c)
    return None


def simulate_laser(
    grid: list[list[str]], start_row: int, start_direction: Direction = "right"
) -> dict:
    rows = len(grid)
    cols = len(grid[0])
    path = []
    # Mirror state tracking
    degraded_mirrors: set[tuple[int, int]] = set()  # Degrading mirrors that have been hit
    toggle_state: dict[tuple[int, int], bool] = {}  # Toggle mirrors: True = ON, False = OFF
    flip_state: dict[tuple[int, int], str] = {}  # Flipping mirrors: current orientation "/" or "\\"

    row = start_row
    col = 0
    direction = start_direction
    bounces = 0
    teleports = 0

    def make_result(edge: str, position) -> dict:
        return {
            "path": path,
            "exit": {"edge": edge, "position": position},
            "bounces": bounces,
            "teleports": teleports,
            "mirror_state": {
                "degraded": degraded_mirrors,
                "toggle_state": toggle_state,
                "flip_state": flip_state,
            }
        }

    while True:
        if row < 0:
            return make_result("top", col_to_letter(col + 1))
        if row >= rows:
            return make_result("bottom", col_to_letter(col + 1))
        if col < 0:
            return make_result("left", row + 1)
        if col >= cols:
            return make_result("right", row + 1)

        path.append({"row": row, "col": col, "direction": direction})
        cell = grid[row][col]
        pos = (row, col)

        if cell in ["/", "\\"]:
            # Regular mirror - always reflects
            direction = get_next_direction(direction, cell)
            bounces += 1
        elif cell in DEGRADING_MIRRORS:
            # Degrading mirror: only reflects if not already hit
            if pos not in degraded_mirrors:
                mirror_type = DEGRADING_MIRRORS[cell]
                direction = get_next_direction(direction, mirror_type)
                bounces += 1
                degraded_mirrors.add(pos)  # Mark as degraded
            # If already degraded, laser passes through (no direction change)
        elif cell in TOGGLE_MIRRORS_ON or cell in TOGGLE_MIRRORS_OFF:
            # Toggle mirror: reflects only if currently ON, then toggles state
            # Initialize state if first encounter
            if pos not in toggle_state:
                toggle_state[pos] = cell in TOGGLE_MIRRORS_ON  # ON if [/ or [\

            if toggle_state[pos]:  # Currently ON - reflects
                mirror_type = TOGGLE_MIRRORS_ON.get(cell) or TOGGLE_MIRRORS_OFF.get(cell)
                direction = get_next_direction(direction, mirror_type)
                bounces += 1

            # Toggle state for next pass
            toggle_state[pos] = not toggle_state[pos]
        elif cell in FLIPPING_MIRRORS:
            # Flipping mirror: reflects based on current orientation, then flips
            # Initialize state if first encounter
            if pos not in flip_state:
                flip_state[pos] = FLIPPING_MIRRORS[cell]

            current_orientation = flip_state[pos]
            direction = get_next_direction(direction, current_orientation)
            bounces += 1

            # Flip orientation for next hit
            flip_state[pos] = "\\" if current_orientation == "/" else "/"
        elif cell in PORTAL_CELLS:
            # Teleport to the paired portal, keep same direction
            exit_pos = find_portal_exit(grid, cell, row, col)
            if exit_pos:
                teleports += 1
                row, col = exit_pos
                # Continue moving in the same direction from the exit portal
                if direction == "right":
                    col += 1
                elif direction == "left":
                    col -= 1
                elif direction == "up":
                    row -= 1
                elif direction == "down":
                    row += 1
                continue  # Skip the normal movement below

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

    return make_result("right", 1)


def generate_puzzle_ascii(grid: list[list[str]], start_row: int) -> str:
    rows = len(grid)
    cols = len(grid[0])
    output = "    "
    for c in range(1, cols + 1):
        output += col_to_letter(c) + " "
    output += "\n"
    output += "  +" + "-" * (cols * 2 + 1) + "+\n"

    for r in range(rows):
        row_num = str(r + 1).rjust(2)
        arrow = ">" if r == start_row else " "
        output += f"{row_num}|{arrow}"
        for c in range(cols):
            output += grid[r][c] + " "
        output += "|\n"

    output += "  +" + "-" * (cols * 2 + 1) + "+"
    return output


def generate_puzzle(size: str = "large", min_bounces: int | None = None) -> dict:
    config = PUZZLE_CONFIG[size]
    rows = random.randint(config["rows"][0], config["rows"][1])
    cols = random.randint(config["cols"][0], config["cols"][1])
    mirror_count = random.randint(config["mirrors"][0], config["mirrors"][1])
    portal_count = config.get("portals", 0)
    mirror_distribution = config.get("mirror_distribution", (100, 0, 0, 0))

    # Use config default if min_bounces not specified
    if min_bounces is None:
        min_bounces = config.get("min_bounces", 0)

    # Generate puzzles and keep the most complex one (highest bounces + teleports)
    max_attempts = 100
    best_puzzle = None
    best_score = 0

    for _ in range(max_attempts):
        grid = generate_grid(rows, cols, mirror_count, portal_count, mirror_distribution)
        start_row = random.randint(0, rows - 1)
        result = simulate_laser(grid, start_row)

        # Score based on bounces + teleports (teleports count double for complexity)
        score = result["bounces"] + result.get("teleports", 0) * 2
        if score > best_score:
            best_score = score
            best_puzzle = {
                "grid": grid,
                "start_row": start_row,
                "ascii": generate_puzzle_ascii(grid, start_row),
                "answer": result["exit"],
                "path_length": len(result["path"]),
                "bounces": result["bounces"],
                "teleports": result.get("teleports", 0),
            }

        # Early exit if we find a really good puzzle
        if best_score >= min_bounces * 2:
            break

    return best_puzzle


# ============== Response Parsing ==============

def parse_llm_response(response: str) -> dict | None:
    json_match = re.search(r"```json\s*(\{[^}]+\})\s*```", response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    json_match = re.search(r'\{"edge":\s*"[^"]+",\s*"position":\s*(?:\d+|"[^"]+")\}', response)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def normalize_position(pos) -> str:
    if isinstance(pos, int):
        return str(pos)
    return str(pos).upper()


# ============== Provider Implementations ==============

def test_openai(puzzle: dict, model: str) -> dict:
    """Test using OpenAI API."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    prompt = build_prompt(puzzle["ascii"])

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        response_text = response.choices[0].message.content or ""
    except Exception as e:
        print(f" Error: {e}")
        response_text = ""

    return evaluate_response(puzzle, response_text)


def test_anthropic(puzzle: dict, model: str) -> dict:
    """Test using Anthropic API."""
    from anthropic import Anthropic

    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    prompt = build_prompt(puzzle["ascii"])

    try:
        # Enable extended thinking for Opus models
        if "opus" in model:
            response = client.messages.create(
                model=model,
                max_tokens=16000,
                temperature=1.0,  # Required for extended thinking
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000,
                },
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        else:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        # Extract text from response (may have thinking blocks)
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text = block.text
                break
    except Exception as e:
        print(f" Error: {e}")
        response_text = ""

    return evaluate_response(puzzle, response_text)


def test_gemini(puzzle: dict, model: str) -> dict:
    """Test using Google Gemini API."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    prompt = build_prompt(puzzle["ascii"])

    try:
        # Use thinking config for Gemini 3 Pro models
        if "gemini-3" in model:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=1.0,  # Gemini 3 recommends default temperature
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.HIGH
                ),
            )
        else:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
            )

        response = client.models.generate_content(
            model=model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
            config=config,
        )
        response_text = response.text or ""
    except Exception as e:
        print(f" Error: {e}")
        response_text = ""

    return evaluate_response(puzzle, response_text)


def evaluate_response(puzzle: dict, response_text: str) -> dict:
    parsed = parse_llm_response(response_text)
    correct = False
    if parsed:
        expected_pos = normalize_position(puzzle["answer"]["position"])
        llm_pos = normalize_position(parsed.get("position", ""))
        correct = parsed.get("edge") == puzzle["answer"]["edge"] and llm_pos == expected_pos

    return {
        "expected": puzzle["answer"],
        "llm_answer": parsed,
        "correct": correct,
        "path_length": puzzle["path_length"],
    }


# ============== Main Benchmark ==============

MODELS = {
    # OpenAI
    # "gpt-5.1": ("openai", "gpt-5.1"),
    # Anthropic
    # "claude-sonnet-4-5": ("anthropic", "claude-sonnet-4-5"),
    # "claude-opus-4-5": ("anthropic", "claude-opus-4-5"),
    # Google Gemini
    # "gemini-2.5-pro": ("gemini", "models/gemini-2.5-pro"),
    "gemini-3-pro": ("gemini", "models/gemini-3-pro-preview"),
    # "gemini-flash": ("gemini", "models/gemini-flash-latest"),
    # "gemini-flash-lite": ("gemini", "models/gemini-flash-lite-latest"),
}


def run_benchmark(num_puzzles: int = 5, size: str = "large", min_bounces: int | None = None) -> dict:
    print("=" * 60)
    print("LaserBench - Multi-Provider Benchmark")
    print("=" * 60)
    print(f"Models: {len(MODELS)}")
    print(f"Puzzles per model: {num_puzzles}")
    print(f"Puzzle size: {size}")
    config = PUZZLE_CONFIG[size]
    effective_min_bounces = min_bounces if min_bounces is not None else config.get("min_bounces", 0)
    print(f"Min bounces: {effective_min_bounces}")
    print("=" * 60)

    # Generate puzzles once
    print(f"\nGenerating {num_puzzles} {size} puzzles (min {effective_min_bounces} bounces)...")
    puzzles = [generate_puzzle(size, min_bounces) for _ in range(num_puzzles)]
    avg_bounces = sum(p["bounces"] for p in puzzles) / len(puzzles)
    avg_teleports = sum(p.get("teleports", 0) for p in puzzles) / len(puzzles)
    print(f"Average bounces: {avg_bounces:.1f}")
    if avg_teleports > 0:
        print(f"Average teleports: {avg_teleports:.1f}")

    all_results = {}

    for display_name, (provider, model_id) in MODELS.items():
        print(f"\n{'='*60}")
        print(f"Testing: {display_name} ({provider})")
        print(f"{'='*60}")

        results = []
        correct_count = 0

        for i, puzzle in enumerate(puzzles):
            print(f"  Puzzle {i + 1}/{num_puzzles}...", end=" ", flush=True)

            if provider == "openai":
                result = test_openai(puzzle, model_id)
            elif provider == "anthropic":
                result = test_anthropic(puzzle, model_id)
            elif provider == "gemini":
                result = test_gemini(puzzle, model_id)
            else:
                print(f"Unknown provider: {provider}")
                continue

            results.append(result)
            if result["correct"]:
                correct_count += 1
                print("✓")
            else:
                print("✗")

        accuracy = correct_count / num_puzzles if num_puzzles > 0 else 0
        print(f"\n{display_name}: {correct_count}/{num_puzzles} ({accuracy*100:.1f}%)")

        all_results[display_name] = {
            "provider": provider,
            "model_id": model_id,
            "correct": correct_count,
            "total": num_puzzles,
            "accuracy": accuracy,
            "results": results,
        }

    return all_results


def save_results(all_results: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    results_path = results_dir / f"multi_provider_{timestamp}.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {results_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    for name, data in all_results.items():
        print(f"{name}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")

    return results_path


if __name__ == "__main__":
    results = run_benchmark(num_puzzles=10, size="extreme")
    if results:
        save_results(results)
