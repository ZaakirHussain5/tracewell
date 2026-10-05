import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { fetchTrace } from "../api";
import { formatCost, formatDuration, formatTokens } from "../lib/format";
import { buildSpanTree, costByModel, failurePathIds, findSpan, waterfallRows } from "../lib/spans";
import type { TraceDetail as TracePayload } from "../types";
import { SpanInspector } from "./SpanInspector";
import { SpanTree } from "./SpanTree";
import { Waterfall } from "./Waterfall";

export function TraceDetail() {
  const { traceId = "" } = useParams();
  const [data, setData] = useState<TracePayload | null>(null);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState("");

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError("");
    fetchTrace(traceId)
      .then((body) => {
        if (cancelled) return;
        setData(body);
        setSelectedId(body.highlight?.span_id || body.tree[0]?.span_id || "");
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load trace");
      });
    return () => {
      cancelled = true;
    };
  }, [traceId]);

  const tree = useMemo(() => (data ? buildSpanTree(data.spans) : []), [data]);
  const failureIds = useMemo(() => failurePathIds(tree), [tree]);
  const rows = useMemo(() => waterfallRows(tree, data?.trace.duration_ms ?? 0), [tree, data]);
  const models = useMemo(() => (data ? costByModel(data.spans) : []), [data]);
  const selected = findSpan(tree, selectedId);

  if (error) {
    return (
      <div className="page">
        <p className="banner bad">{error}</p>
        <Link to="/">Back to runs</Link>
      </div>
    );
  }
  if (!data) return <div className="page">Loading trace…</div>;

  const trace = data.trace;
  return (
    <div className="page">
      <p className="crumb">
        <Link to="/">Runs</Link>
        <span>/</span>
        <span>{trace.trace_id.slice(0, 8)}</span>
      </p>
      <header className="detail-head">
        <div>
          <h1>{trace.name}</h1>
          <p>
            {trace.agent_name} · {trace.environment} · {trace.release}
            {trace.conversation_id ? ` · ${trace.conversation_id}` : ""}
          </p>
        </div>
        <span className={trace.status === "error" ? "pill bad" : "pill ok"}>
          {trace.status === "error" ? "failed" : "ok"}
        </span>
      </header>

      {data.highlight && (
        <div className={data.highlight.recovered ? "banner warn" : "banner bad"}>
          <strong>
            {data.highlight.recovered ? "Recovered after a failed step" : "Failed at this step"}
          </strong>
          <span>
            {data.highlight.name}
            {data.highlight.error_type ? ` — ${data.highlight.error_type}` : ""}
            {data.highlight.error_message ? `. ${data.highlight.error_message}` : ""}
          </span>
          <button type="button" onClick={() => setSelectedId(data.highlight?.span_id ?? "")}>
            Show span
          </button>
        </div>
      )}

      <section className="stats">
        <article className="stat">
          <span>Duration</span>
          <strong>{formatDuration(trace.duration_ms)}</strong>
        </article>
        <article className="stat">
          <span>Input tokens</span>
          <strong>{formatTokens(trace.total_input_tokens)}</strong>
        </article>
        <article className="stat">
          <span>Output tokens</span>
          <strong>{formatTokens(trace.total_output_tokens)}</strong>
        </article>
        <article className="stat">
          <span>Cache read</span>
          <strong>{formatTokens(trace.total_cache_read_tokens)}</strong>
        </article>
        <article className="stat">
          <span>Cost</span>
          <strong>{formatCost(trace.total_cost_usd)}</strong>
        </article>
      </section>

      <p className="summary">
        <strong>In.</strong> {trace.input_summary} <strong>Out.</strong> {trace.output_summary}
      </p>

      <div className="split">
        <section className="panel">
          <header className="panel-head">
            <h2>Span tree</h2>
            <p>LLM calls and tool calls are siblings under the agent. HTTP and database spans stay in the same trace.</p>
          </header>
          <SpanTree nodes={tree} selectedId={selectedId} failureIds={failureIds} onSelect={setSelectedId} />
        </section>
        <section className="panel">
          <header className="panel-head">
            <h2>Waterfall</h2>
            <p>Bars use offsets from the start of the run. Failed spans stay red.</p>
          </header>
          <Waterfall rows={rows} totalMs={trace.duration_ms} selectedId={selectedId} onSelect={setSelectedId} />
          <h3 className="subhead">Cost in this run</h3>
          {models.length === 0 ? (
            <p className="empty">No model calls.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Calls</th>
                  <th>Tokens</th>
                  <th>Cost</th>
                </tr>
              </thead>
              <tbody>
                {models.map((row) => (
                  <tr key={row.model}>
                    <td>{row.model}</td>
                    <td>{row.calls}</td>
                    <td>{formatTokens(row.inputTokens + row.outputTokens)}</td>
                    <td>{formatCost(row.costUsd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <SpanInspector span={selected} />
    </div>
  );
}
