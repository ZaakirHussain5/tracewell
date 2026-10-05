import { describe, expect, it } from "vitest";

import type { Span } from "../types";
import { buildSpanTree, costByModel, failurePathIds, waterfallRows } from "./spans";

function span(partial: Partial<Span> & Pick<Span, "span_id" | "name" | "op">): Span {
  return {
    parent_span_id: null,
    status: "ok",
    start_ms: 0,
    duration_ms: 10,
    agent_name: "",
    model: "",
    tool_name: "",
    provider: "",
    input_tokens: 0,
    output_tokens: 0,
    cache_read_tokens: 0,
    cost_usd: "0",
    input_text: "",
    output_text: "",
    error_type: "",
    error_message: "",
    attributes: {},
    ...partial,
  };
}

describe("span tree", () => {
  const spans = [
    span({ span_id: "http", name: "POST", op: "http.server", duration_ms: 100 }),
    span({
      span_id: "agent",
      parent_span_id: "http",
      name: "invoke_agent Incident Commander",
      op: "gen_ai.invoke_agent",
      status: "error",
      start_ms: 5,
      duration_ms: 90,
    }),
    span({
      span_id: "chat",
      parent_span_id: "agent",
      name: "chat gpt-4.1",
      op: "gen_ai.chat",
      model: "gpt-4.1",
      provider: "openai",
      start_ms: 10,
      duration_ms: 20,
      input_tokens: 100,
      output_tokens: 20,
      cost_usd: "0.000360",
    }),
    span({
      span_id: "tool",
      parent_span_id: "agent",
      name: "execute_tool k8s.rollout_restart",
      op: "gen_ai.execute_tool",
      status: "error",
      start_ms: 40,
      duration_ms: 40,
      error_type: "TimeoutError",
    }),
  ];

  it("nests tool and chat spans under the agent, under HTTP", () => {
    const tree = buildSpanTree(spans);
    expect(tree.map((node) => node.span_id)).toEqual(["http"]);
    expect(tree[0].children.map((node) => node.span_id)).toEqual(["agent"]);
    expect(tree[0].children[0].children.map((node) => node.span_id)).toEqual(["chat", "tool"]);
  });

  it("marks the failure path from the HTTP root down to the tool", () => {
    const ids = failurePathIds(buildSpanTree(spans));
    expect([...ids].sort()).toEqual(["agent", "http", "tool"]);
  });

  it("places the failed tool later on the waterfall than the chat span", () => {
    const rows = waterfallRows(buildSpanTree(spans), 100);
    const tool = rows.find((row) => row.span.span_id === "tool");
    const chat = rows.find((row) => row.span.span_id === "chat");
    if (!tool || !chat) throw new Error("expected chat and tool rows");
    expect(tool.depth).toBe(2);
    expect(tool.leftPct).toBeGreaterThan(chat.leftPct);
    expect(tool.widthPct).toBe(40);
  });

  it("rolls cost and tokens up by model", () => {
    const rows = costByModel(spans);
    expect(rows).toHaveLength(1);
    expect(rows[0].model).toBe("gpt-4.1");
    expect(rows[0].calls).toBe(1);
    expect(rows[0].inputTokens).toBe(100);
    expect(rows[0].costUsd).toBeCloseTo(0.00036);
  });
});
