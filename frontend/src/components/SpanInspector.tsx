import { formatCost, formatDuration, formatTokens } from "../lib/format";
import type { SpanNode } from "../types";

export function SpanInspector({ span }: { span: SpanNode | null }) {
  if (!span) return null;
  const tokens = span.input_tokens + span.output_tokens;
  return (
    <section className="inspector">
      <header className="panel-head">
        <h2>
          <span className="op-dot" data-op={span.op} />
          {span.name}
        </h2>
        <p>
          {span.op} · {formatDuration(span.duration_ms)}
          {span.agent_name ? ` · ${span.agent_name}` : ""}
          {span.status === "error" ? " · failed" : ""}
        </p>
      </header>
      {span.status === "error" && (
        <div className="banner bad">
          <strong>{span.error_type || "Error"}</strong>
          <span>{span.error_message}</span>
        </div>
      )}
      <div className="inspector-grid">
        <div>
          <h3>Input</h3>
          <pre>{span.input_text || "—"}</pre>
        </div>
        <div>
          <h3>Output</h3>
          <pre>{span.output_text || "—"}</pre>
        </div>
      </div>
      {(tokens > 0 || span.model) && (
        <dl className="kv">
          <div>
            <dt>Model</dt>
            <dd>{span.model || "—"}</dd>
          </div>
          <div>
            <dt>Input tokens</dt>
            <dd>{formatTokens(span.input_tokens)}</dd>
          </div>
          <div>
            <dt>Cache read</dt>
            <dd>{formatTokens(span.cache_read_tokens)}</dd>
          </div>
          <div>
            <dt>Output tokens</dt>
            <dd>{formatTokens(span.output_tokens)}</dd>
          </div>
          <div>
            <dt>Cost</dt>
            <dd>{formatCost(span.cost_usd)}</dd>
          </div>
        </dl>
      )}
      <h3>Attributes</h3>
      <dl className="attrs">
        {Object.entries(span.attributes).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
