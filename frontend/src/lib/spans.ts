import { asNumber } from "./format";
import type { Span, SpanNode } from "../types";

export function buildSpanTree(spans: Span[]): SpanNode[] {
  const nodes: SpanNode[] = [];
  const byId = new Map<string, SpanNode>();
  for (const span of spans) {
    const node: SpanNode = { ...span, children: [] };
    nodes.push(node);
    byId.set(span.span_id, node);
  }
  const roots: SpanNode[] = [];
  for (const node of nodes) {
    const parent = node.parent_span_id ? byId.get(node.parent_span_id) : undefined;
    if (!parent || parent === node) roots.push(node);
    else parent.children.push(node);
  }
  return roots;
}

export function failurePathIds(tree: SpanNode[]): Set<string> {
  const ids = new Set<string>();
  const walk = (node: SpanNode): boolean => {
    const childFailed = node.children.some(walk);
    const failed = node.status === "error" || childFailed;
    if (failed) ids.add(node.span_id);
    return failed;
  };
  tree.forEach(walk);
  return ids;
}

export interface WaterfallRow {
  span: SpanNode;
  depth: number;
  leftPct: number;
  widthPct: number;
}

export function waterfallRows(tree: SpanNode[], totalMs: number): WaterfallRow[] {
  const rows: WaterfallRow[] = [];
  const walk = (nodes: SpanNode[], depth: number) => {
    for (const node of nodes) {
      const left = totalMs > 0 ? (node.start_ms / totalMs) * 100 : 0;
      const rawWidth = totalMs > 0 ? (node.duration_ms / totalMs) * 100 : 0;
      const width = Math.min(Math.max(rawWidth, 0.6), Math.max(100 - left, 0.6));
      rows.push({ span: node, depth, leftPct: left, widthPct: width });
      walk(node.children, depth + 1);
    }
  };
  walk(tree, 0);
  return rows;
}

export interface ModelCost {
  model: string;
  provider: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  costUsd: number;
  errors: number;
}

export function costByModel(spans: Span[]): ModelCost[] {
  const grouped = new Map<string, ModelCost>();
  for (const span of spans) {
    if (!span.model) continue;
    const current = grouped.get(span.model) ?? {
      model: span.model,
      provider: span.provider,
      calls: 0,
      inputTokens: 0,
      outputTokens: 0,
      cacheReadTokens: 0,
      costUsd: 0,
      errors: 0,
    };
    current.calls += 1;
    current.inputTokens += span.input_tokens;
    current.outputTokens += span.output_tokens;
    current.cacheReadTokens += span.cache_read_tokens;
    current.costUsd += asNumber(span.cost_usd);
    if (span.status === "error") current.errors += 1;
    grouped.set(span.model, current);
  }
  return [...grouped.values()].sort((a, b) => b.costUsd - a.costUsd);
}

export function findSpan(tree: SpanNode[], spanId: string): SpanNode | null {
  for (const node of tree) {
    if (node.span_id === spanId) return node;
    const nested = findSpan(node.children, spanId);
    if (nested) return nested;
  }
  return null;
}
