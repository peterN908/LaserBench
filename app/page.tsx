"use client";

import { useState, useEffect, useCallback } from "react";

type Direction = "right" | "left" | "up" | "down";
type Cell = "." | "/" | "\\";
type PuzzleSize = "small" | "medium" | "large";

interface Position {
  row: number;
  col: number;
}

interface LaserStep extends Position {
  direction: Direction;
}

interface ExitInfo {
  edge: "top" | "bottom" | "left" | "right";
  position: number | string;
}

function colToLetter(col: number): string {
  let result = "";
  let c = col;
  while (c > 0) {
    c--;
    result = String.fromCharCode(65 + (c % 26)) + result;
    c = Math.floor(c / 26);
  }
  return result;
}

const PUZZLE_CONFIG: Record<PuzzleSize, { rows: [number, number]; cols: [number, number]; mirrors: [number, number] }> = {
  small: { rows: [5, 6], cols: [6, 8], mirrors: [4, 6] },
  medium: { rows: [7, 9], cols: [9, 12], mirrors: [7, 10] },
  large: { rows: [10, 12], cols: [13, 16], mirrors: [12, 16] },
};

function generateGrid(rows: number, cols: number, mirrorCount: number): Cell[][] {
  const grid: Cell[][] = Array.from({ length: rows }, () =>
    Array.from({ length: cols }, () => ".")
  );

  let placed = 0;
  while (placed < mirrorCount) {
    const r = Math.floor(Math.random() * rows);
    const c = Math.floor(Math.random() * cols);
    if (grid[r][c] === ".") {
      grid[r][c] = Math.random() < 0.5 ? "/" : "\\";
      placed++;
    }
  }

  return grid;
}

function getNextDirection(current: Direction, mirror: "/" | "\\"): Direction {
  if (mirror === "/") {
    switch (current) {
      case "right": return "up";
      case "left": return "down";
      case "up": return "right";
      case "down": return "left";
    }
  } else {
    switch (current) {
      case "right": return "down";
      case "left": return "up";
      case "up": return "left";
      case "down": return "right";
    }
  }
}

function simulateLaser(
  grid: Cell[][],
  startRow: number,
  startDirection: Direction
): { path: LaserStep[]; exit: ExitInfo } {
  const rows = grid.length;
  const cols = grid[0].length;
  const path: LaserStep[] = [];

  let row = startRow;
  let col = 0;
  let direction = startDirection;

  while (true) {
    if (row < 0) {
      return { path, exit: { edge: "top", position: colToLetter(col + 1) } };
    }
    if (row >= rows) {
      return { path, exit: { edge: "bottom", position: colToLetter(col + 1) } };
    }
    if (col < 0) {
      return { path, exit: { edge: "left", position: row + 1 } };
    }
    if (col >= cols) {
      return { path, exit: { edge: "right", position: row + 1 } };
    }

    path.push({ row, col, direction });

    const cell = grid[row][col];
    if (cell === "/" || cell === "\\") {
      direction = getNextDirection(direction, cell);
    }

    switch (direction) {
      case "right": col++; break;
      case "left": col--; break;
      case "up": row--; break;
      case "down": row++; break;
    }

    if (path.length > 1000) break;
  }

  return { path, exit: { edge: "right", position: 1 } };
}

function generateAsciiGrid(
  grid: Cell[][],
  startRow: number,
  laserPath: LaserStep[] | null,
  currentStep: number
): string {
  const rows = grid.length;
  const cols = grid[0].length;

  const pathSet = new Set<string>();
  if (laserPath) {
    for (let i = 0; i <= currentStep && i < laserPath.length; i++) {
      pathSet.add(`${laserPath[i].row},${laserPath[i].col}`);
    }
  }

  let output = "    ";
  for (let c = 1; c <= cols; c++) {
    output += colToLetter(c) + " ";
  }
  output += "\n";

  output += "  +" + "-".repeat(cols * 2 + 1) + "+\n";

  for (let r = 0; r < rows; r++) {
    const rowNum = (r + 1).toString().padStart(2, " ");
    const arrow = r === startRow ? ">" : " ";
    output += rowNum + "|" + arrow;

    for (let c = 0; c < cols; c++) {
      const cell = grid[r][c];
      const isLit = pathSet.has(`${r},${c}`);
      if (isLit && cell === ".") {
        output += "* ";
      } else {
        output += cell + " ";
      }
    }
    output += "|\n";
  }

  output += "  +" + "-".repeat(cols * 2 + 1) + "+";

  return output;
}

function generatePuzzleAscii(grid: Cell[][], startRow: number): string {
  const rows = grid.length;
  const cols = grid[0].length;

  let output = "    ";
  for (let c = 1; c <= cols; c++) {
    output += colToLetter(c) + " ";
  }
  output += "\n";

  output += "  +" + "-".repeat(cols * 2 + 1) + "+\n";

  for (let r = 0; r < rows; r++) {
    const rowNum = (r + 1).toString().padStart(2, " ");
    const arrow = r === startRow ? ">" : " ";
    output += rowNum + "|" + arrow;

    for (let c = 0; c < cols; c++) {
      output += grid[r][c] + " ";
    }
    output += "|\n";
  }

  output += "  +" + "-".repeat(cols * 2 + 1) + "+";

  return output;
}

export default function Home() {
  const [grid, setGrid] = useState<Cell[][] | null>(null);
  const [startRow, setStartRow] = useState(0);
  const [laserPath, setLaserPath] = useState<LaserStep[] | null>(null);
  const [exitInfo, setExitInfo] = useState<ExitInfo | null>(null);
  const [currentStep, setCurrentStep] = useState(-1);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);
  const [copied, setCopied] = useState(false);
  const [puzzleSize, setPuzzleSize] = useState<PuzzleSize>("medium");

  const generateNewPuzzle = useCallback((size: PuzzleSize = puzzleSize) => {
    const config = PUZZLE_CONFIG[size];
    const rows = config.rows[0] + Math.floor(Math.random() * (config.rows[1] - config.rows[0] + 1));
    const cols = config.cols[0] + Math.floor(Math.random() * (config.cols[1] - config.cols[0] + 1));
    const mirrorCount = config.mirrors[0] + Math.floor(Math.random() * (config.mirrors[1] - config.mirrors[0] + 1));
    const newGrid = generateGrid(rows, cols, mirrorCount);
    const newStartRow = Math.floor(Math.random() * rows);

    const { path, exit } = simulateLaser(newGrid, newStartRow, "right");

    setGrid(newGrid);
    setStartRow(newStartRow);
    setLaserPath(path);
    setExitInfo(exit);
    setCurrentStep(-1);
    setIsAnimating(false);
    setShowAnswer(false);
    setCopied(false);
  }, []);

  useEffect(() => {
    generateNewPuzzle();
  }, [generateNewPuzzle]);

  useEffect(() => {
    if (isAnimating && laserPath && currentStep < laserPath.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStep((prev) => prev + 1);
      }, 100);
      return () => clearTimeout(timer);
    } else if (isAnimating && laserPath && currentStep >= laserPath.length - 1) {
      setIsAnimating(false);
      setShowAnswer(true);
    }
  }, [isAnimating, currentStep, laserPath]);

  const fireLaser = () => {
    setCurrentStep(-1);
    setShowAnswer(false);
    setTimeout(() => {
      setIsAnimating(true);
      setCurrentStep(0);
    }, 50);
  };

  const copyToClipboard = async () => {
    if (!grid) return;
    const ascii = generatePuzzleAscii(grid, startRow);
    const fullText = `A laser starts at the left edge where the arrow is, moving right (-->).
It moves in straight lines and bounces off mirrors:
  '/' and '\\' turn it 90° as in typical mirror puzzles.
The beam stops when it exits the grid. Which edge and at what row/col?

Row/Col indices start from 1 at top-left.

${ascii}`;

    await navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!grid) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-900">
        <p className="text-zinc-400 font-mono">Loading puzzle...</p>
      </div>
    );
  }

  const displayAscii = generateAsciiGrid(
    grid,
    startRow,
    isAnimating || showAnswer ? laserPath : null,
    showAnswer ? (laserPath?.length ?? 0) - 1 : currentStep
  );

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-900 p-8 font-mono">
      <div className="max-w-2xl w-full">
        <h1 className="text-2xl font-bold text-zinc-100 mb-4">Laser Mirror Puzzle</h1>

        <div className="text-zinc-400 text-sm mb-6 space-y-1">
          <p>A laser starts at the left edge where the arrow is, moving right (--&gt;).</p>
          <p>It moves in straight lines and bounces off mirrors:</p>
          <p className="pl-4">&apos;/&apos; and &apos;\&apos; turn it 90° as in typical mirror puzzles.</p>
          <p>The beam stops when it exits the grid. Which edge and at what row/col?</p>
          <p className="text-zinc-500">Row/Col indices start from 1 at top-left.</p>
        </div>

        <div className="bg-zinc-800 rounded-lg p-6 mb-6">
          <pre className="text-zinc-100 text-sm leading-relaxed whitespace-pre select-all">
            {displayAscii}
          </pre>
        </div>

        {showAnswer && exitInfo && (
          <div className="bg-green-900/30 border border-green-700 rounded-lg p-4 mb-6">
            <p className="text-green-400 font-semibold">
              Answer: Exits {exitInfo.edge} edge at {exitInfo.edge === "top" || exitInfo.edge === "bottom" ? "column" : "row"} {exitInfo.position}
            </p>
          </div>
        )}

        <div className="flex gap-2 mb-4">
          <span className="text-zinc-400 text-sm py-2 pr-2">Size:</span>
          {(["small", "medium", "large"] as const).map((size) => (
            <button
              key={size}
              onClick={() => {
                setPuzzleSize(size);
                generateNewPuzzle(size);
              }}
              disabled={isAnimating}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                puzzleSize === size
                  ? "bg-blue-600 text-white"
                  : "bg-zinc-700 hover:bg-zinc-600 text-zinc-300"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              {size.charAt(0).toUpperCase() + size.slice(1)}
            </button>
          ))}
        </div>

        <div className="flex gap-4 flex-wrap">
          <button
            onClick={fireLaser}
            disabled={isAnimating}
            className="px-6 py-3 bg-red-600 hover:bg-red-500 disabled:bg-red-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            {isAnimating ? "Firing..." : "Fire Laser"}
          </button>

          <button
            onClick={() => generateNewPuzzle()}
            disabled={isAnimating}
            className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 disabled:bg-zinc-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            New Puzzle
          </button>

          <button
            onClick={copyToClipboard}
            className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg font-medium transition-colors"
          >
            {copied ? "Copied!" : "Copy ASCII"}
          </button>
        </div>

        <p className="text-zinc-500 text-xs mt-6">
          Refresh the page or click &quot;New Puzzle&quot; for a new challenge.
        </p>
      </div>
    </div>
  );
}
