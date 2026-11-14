// Guard for non-negotiable 10: hand-written UI copy contains no digits. Numbers on screen come from
// the API or from app/flow/sample.ts, never from text typed into a component (AGENTS.md §17.1.7).
// Parses each component with the TypeScript compiler and checks JSX text and string props.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const ROOT = __dirname;
// Props that hold layout or geometry, not words a person reads.
const NOT_COPY = new Set(["className", "d", "viewBox", "cx", "cy", "r", "x", "y", "rx", "strokeWidth", "key", "colSpan",
  "preserveAspectRatio", "width", "height", "style"]);

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name: string) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return files(path);
    return path.endsWith(".tsx") ? [path] : [];
  });
}

function copyWithDigits(path: string): string[] {
  const source = ts.createSourceFile(path, readFileSync(path, "utf-8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const found: string[] = [];
  const visit = (node: ts.Node) => {
    if (ts.isJsxText(node) && /\d/.test(node.text)) found.push(node.text.trim());
    if (ts.isJsxAttribute(node) && node.initializer && ts.isStringLiteral(node.initializer)
        && !NOT_COPY.has(node.name.getText()) && /\d/.test(node.initializer.text)) {
      found.push(`${node.name.getText()}="${node.initializer.text}"`);
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return found;
}

describe("UI copy has no typed-in numbers", () => {
  for (const file of files(ROOT)) {
    it(file.replace(ROOT, "src"), () => {
      expect(copyWithDigits(file)).toEqual([]);
    });
  }
});
