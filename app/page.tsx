"use client";

import React, { useState, useEffect, useCallback } from "react";

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

interface BenchmarkResult {
  model: string;
  accuracy: number;
  correct: number;
  total: number;
  provider: string;
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

const PUZZLE_CONFIG: Record<PuzzleSize, { rows: [number, number]; cols: [number, number]; mirrors: [number, number]; minBounces: number }> = {
  small: { rows: [5, 6], cols: [6, 8], mirrors: [4, 6], minBounces: 3 },
  medium: { rows: [7, 9], cols: [9, 12], mirrors: [7, 10], minBounces: 5 },
  large: { rows: [10, 12], cols: [13, 16], mirrors: [18, 24], minBounces: 8 },
};

// Benchmark results from testing
const BENCHMARK_RESULTS: BenchmarkResult[] = [
  { model: "Gemini 3 Pro", accuracy: 94, correct: 47, total: 50, provider: "Google" },
  { model: "Claude Opus 4.5", accuracy: 74, correct: 37, total: 50, provider: "Anthropic" },
  { model: "Claude Sonnet 4.5", accuracy: 52, correct: 26, total: 50, provider: "Anthropic" },
  { model: "Gemini Flash", accuracy: 42, correct: 21, total: 50, provider: "Google" },
  { model: "GPT-5.1", accuracy: 26, correct: 13, total: 50, provider: "OpenAI" },
];

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
): { path: LaserStep[]; exit: ExitInfo; bounces: number } {
  const rows = grid.length;
  const cols = grid[0].length;
  const path: LaserStep[] = [];

  let row = startRow;
  let col = 0;
  let direction = startDirection;
  let bounces = 0;

  while (true) {
    if (row < 0) {
      return { path, exit: { edge: "top", position: colToLetter(col + 1) }, bounces };
    }
    if (row >= rows) {
      return { path, exit: { edge: "bottom", position: colToLetter(col + 1) }, bounces };
    }
    if (col < 0) {
      return { path, exit: { edge: "left", position: row + 1 }, bounces };
    }
    if (col >= cols) {
      return { path, exit: { edge: "right", position: row + 1 }, bounces };
    }

    path.push({ row, col, direction });

    const cell = grid[row][col];
    if (cell === "/" || cell === "\\") {
      direction = getNextDirection(direction, cell);
      bounces++;
    }

    switch (direction) {
      case "right": col++; break;
      case "left": col--; break;
      case "up": row--; break;
      case "down": row++; break;
    }

    if (path.length > 1000) break;
  }

  return { path, exit: { edge: "right", position: 1 }, bounces };
}

function generateColoredAsciiGrid(
  grid: Cell[][],
  startRow: number,
  laserPath: LaserStep[] | null,
  currentStep: number
): React.ReactNode {
  const rows = grid.length;
  const cols = grid[0].length;

  const pathSet = new Set<string>();
  if (laserPath) {
    for (let i = 0; i <= currentStep && i < laserPath.length; i++) {
      pathSet.add(`${laserPath[i].row},${laserPath[i].col}`);
    }
  }

  const elements: React.ReactNode[] = [];
  let key = 0;

  // Column headers
  elements.push(<span key={key++} className="text-white">{"    "}</span>);
  for (let c = 1; c <= cols; c++) {
    elements.push(<span key={key++} className="text-white">{colToLetter(c) + " "}</span>);
  }
  elements.push("\n");

  // Top border
  elements.push(<span key={key++} className="text-white">{"  +" + "-".repeat(cols * 2 + 1) + "+\n"}</span>);

  // Grid rows
  for (let r = 0; r < rows; r++) {
    const rowNum = (r + 1).toString().padStart(2, " ");
    elements.push(<span key={key++} className="text-white">{rowNum}</span>);
    elements.push(<span key={key++} className="text-white">{"|"}</span>);

    // Arrow indicator
    if (r === startRow) {
      elements.push(<span key={key++} className="text-green-400 font-bold">{">"}</span>);
    } else {
      elements.push(<span key={key++}>{" "}</span>);
    }

    for (let c = 0; c < cols; c++) {
      const cell = grid[r][c];
      const isLit = pathSet.has(`${r},${c}`);

      if (isLit && cell === ".") {
        // Laser path on empty cell
        elements.push(<span key={key++} className="text-red-500 font-bold">{"* "}</span>);
      } else if (cell === "/") {
        // Forward slash mirror
        const mirrorClass = isLit ? "text-yellow-300 font-bold" : "text-yellow-500";
        elements.push(<span key={key++} className={mirrorClass}>{"/ "}</span>);
      } else if (cell === "\\") {
        // Backslash mirror
        const mirrorClass = isLit ? "text-yellow-300 font-bold" : "text-yellow-500";
        elements.push(<span key={key++} className={mirrorClass}>{"\\ "}</span>);
      } else {
        // Empty cell
        elements.push(<span key={key++} className="text-zinc-500">{". "}</span>);
      }
    }
    elements.push(<span key={key++} className="text-white">{"|"}</span>);
    elements.push("\n");
  }

  // Bottom border
  elements.push(<span key={key++} className="text-white">{"  +" + "-".repeat(cols * 2 + 1) + "+"}</span>);

  return elements;
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

function BenchmarkChart({ results }: { results: BenchmarkResult[] }) {
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);
  const maxAccuracy = 100;

  const getBarColor = (accuracy: number) => {
    if (accuracy >= 90) return "bg-green-500";
    if (accuracy >= 70) return "bg-yellow-500";
    if (accuracy >= 50) return "bg-orange-500";
    return "bg-red-500";
  };

  const sortedResults = [...results].sort((a, b) => b.accuracy - a.accuracy);

  return (
    <div className="bg-zinc-800 rounded-lg p-6">
      <h3 className="text-lg font-bold text-zinc-100 mb-4">Benchmark Results</h3>
      <p className="text-zinc-400 text-sm mb-6">Large puzzles (10-12 rows, 13-16 cols, 12-16 mirrors)</p>

      <div className="space-y-3">
        {sortedResults.map((result, index) => (
          <div
            key={result.model}
            className="relative"
            onMouseEnter={() => setHoveredBar(index)}
            onMouseLeave={() => setHoveredBar(null)}
          >
            <div className="flex items-center gap-3">
              <div className="w-32 text-sm text-zinc-300 truncate" title={result.model}>
                {result.model}
              </div>
              <div className="flex-1 h-8 bg-zinc-700 rounded-lg overflow-hidden relative">
                <div
                  className={`h-full ${getBarColor(result.accuracy)} transition-all duration-300 rounded-lg`}
                  style={{ width: `${(result.accuracy / maxAccuracy) * 100}%` }}
                />
                <div className="absolute inset-0 flex items-center justify-end pr-3">
                  <span className="text-sm font-bold text-white drop-shadow-lg">
                    {result.accuracy}%
                  </span>
                </div>
              </div>
            </div>

            {/* Tooltip */}
            {hoveredBar === index && (
              <div className="absolute left-36 top-0 z-10 bg-zinc-900 border border-zinc-600 rounded-lg p-3 shadow-xl min-w-48">
                <p className="text-zinc-100 font-semibold">{result.model}</p>
                <p className="text-zinc-400 text-sm">Provider: {result.provider}</p>
                <p className="text-zinc-400 text-sm">
                  Score: {result.correct}/{result.total} ({result.accuracy}%)
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-4 text-xs text-zinc-500">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-green-500 rounded" />
          <span>90%+</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-yellow-500 rounded" />
          <span>70-89%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-orange-500 rounded" />
          <span>50-69%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-red-500 rounded" />
          <span>&lt;50%</span>
        </div>
      </div>
    </div>
  );
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
  const [puzzleSize, setPuzzleSize] = useState<PuzzleSize>("large");

  const generateNewPuzzle = useCallback((size: PuzzleSize = puzzleSize) => {
    const config = PUZZLE_CONFIG[size];
    const rows = config.rows[0] + Math.floor(Math.random() * (config.rows[1] - config.rows[0] + 1));
    const cols = config.cols[0] + Math.floor(Math.random() * (config.cols[1] - config.cols[0] + 1));
    const mirrorCount = config.mirrors[0] + Math.floor(Math.random() * (config.mirrors[1] - config.mirrors[0] + 1));

    // Generate puzzles and keep the most complex one (highest bounces)
    const maxAttempts = 100;
    let bestGrid: Cell[][] = [];
    let bestStartRow = 0;
    let bestPath: LaserStep[] = [];
    let bestExit: ExitInfo = { edge: "right", position: 1 };
    let bestBounces = 0;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const candidateGrid = generateGrid(rows, cols, mirrorCount);
      const candidateStartRow = Math.floor(Math.random() * rows);
      const result = simulateLaser(candidateGrid, candidateStartRow, "right");

      if (result.bounces > bestBounces) {
        bestGrid = candidateGrid;
        bestStartRow = candidateStartRow;
        bestPath = result.path;
        bestExit = result.exit;
        bestBounces = result.bounces;
      }

      // Early exit if we find a really good puzzle
      if (bestBounces >= config.minBounces * 2) {
        break;
      }
    }

    setGrid(bestGrid);
    setStartRow(bestStartRow);
    setLaserPath(bestPath);
    setExitInfo(bestExit);
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

  const displayAscii = generateColoredAsciiGrid(
    grid,
    startRow,
    isAnimating || showAnswer ? laserPath : null,
    showAnswer ? (laserPath?.length ?? 0) - 1 : currentStep
  );

  return (
    <div className="flex min-h-screen flex-col items-center bg-zinc-900 p-8 font-mono">
      <div className="max-w-2xl w-full">
        {/* Header with GitHub link */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-zinc-100">LaserBench</h1>
          <a
            href="https://github.com/peterN908/LaserBench"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-zinc-400 hover:text-zinc-100 transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
            </svg>
            <span className="text-sm">GitHub</span>
          </a>
        </div>

        <p className="text-zinc-400 text-sm mb-6">
          A benchmark for testing LLM spatial reasoning through laser mirror puzzles.
        </p>

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

        <div className="flex gap-4 flex-wrap mb-8">
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

        {/* Benchmark Results Chart */}
        <BenchmarkChart results={BENCHMARK_RESULTS} />

        <p className="text-zinc-500 text-xs mt-6 text-center">
          Refresh the page or click &quot;New Puzzle&quot; for a new challenge.
        </p>
      </div>
    </div>
  );
}
