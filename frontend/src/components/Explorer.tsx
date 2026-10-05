import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { fetchOverview } from "../api";
import { formatCost, formatDuration, formatPercent, formatTokens, formatWhen, asNumber } from "../lib/format";
import type { Overview } from "../types";

export function Explorer() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const agent = params.get("agent") ?? "";
  const conversation = params.get("conversation") ?? "";
  const q = params.get("q") ?? "";
  const [draft, setDraft] = useState(q);
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setDraft(q);
  }, [q]);

  useEffect(() => {
    const query = new URLSearchParams();
    if (status) query.set("status", status);
    if (agent) query.set("agent", agent);
    if (conversation) query.set("conversation", conversation);
    if (q) query.set("q", q);
    let cancelled = false;
    setError("");
    fetchOverview(query)
      .then((body) => {
        if (!cancelled) setData(body);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load traces");
      });
    return () => {
      cancelled = true;
    };
  }, [status, agent, conversation, q]);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  };

  return (
    <div className="page">
      <section className="intro">
        <div>
          <h1>{data?.project.name ?? "Traces"}</h1>
          <p>{data?.project.description ?? "Loading seeded agent runs…"}</p>
        </div>
      </section>

      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          setParam("q", draft.trim());
        }}
      >
        <label>
          Status
          <select value={status} onChange={(event) => setParam("status", event.target.value)}>
            <option value="">All runs</option>
            <option value="error">Failed runs</option>
            <option value="ok">Successful runs</option>
          </select>
        </label>
        <label>
          Agent
          <select value={agent} onChange={(event) => setParam("agent", event.target.value)}>
            <option value="">All agents</option>
            {(data?.agents ?? []).map((item) => (
              <option key={item.name} value={item.name}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="search">
          Search
          <input
            value={draft}
            placeholder="latency, restart, runbook…"
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button type="submit">Apply</button>
        {(status || agent || conversation || q) && (
          <button
            type="button"
            className="ghost"
            onClick={() => {
              setDraft("");
              setParams(new URLSearchParams());
            }}
          >
            Clear
          </button>
        )}
      </form>

      {error && <p className="banner bad">{error}</p>}

      {data && (
        <>
          <section className="stats">
            <Stat label="Runs" value={String(data.stats.trace_count)} />
            <Stat label="Failed runs" value={String(data.stats.error_count)} tone="bad" />
            <Stat label="Error rate" value={formatPercent(data.stats.error_rate)} />
            <Stat
              label="Tokens"
              value={formatTokens(data.stats.input_tokens + data.stats.output_tokens)}
              hint={`${formatTokens(data.stats.cache_read_tokens)} cache read`}
            />
            <Stat label="Cost" value={formatCost(data.stats.cost_usd)} />
            <Stat label="Failed steps" value={String(data.stats.leaf_errors)} tone="bad" />
          </section>

          <section className="panel">
            <header className="panel-head">
              <h2>Cost by model</h2>
              <p>Cache-read tokens are included in input tokens, then priced at the cache rate.</p>
            </header>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Calls</th>
                    <th>Input</th>
                    <th>Cache read</th>
                    <th>Output</th>
                    <th>Errors</th>
                    <th>Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {data.stats.by_model.map((row) => (
                    <tr key={row.model}>
                      <td>
                        <strong>{row.model}</strong>
                        <span className="muted"> {row.provider}</span>
                      </td>
                      <td>{row.calls}</td>
                      <td>{formatTokens(row.input_tokens)}</td>
                      <td>{formatTokens(row.cache_read_tokens)}</td>
                      <td>{formatTokens(row.output_tokens)}</td>
                      <td>{row.errors ? <span className="pill bad">{row.errors}</span> : "0"}</td>
                      <td>{formatCost(row.cost_usd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <header className="panel-head">
              <h2>Conversations</h2>
              <p>Turns that share a conversation id stay grouped across traces.</p>
            </header>
            <div className="chips">
              {data.conversations.map((item) => (
                <button
                  key={item.conversation_id}
                  type="button"
                  className={item.conversation_id === conversation ? "chip active" : "chip"}
                  onClick={() =>
                    setParam("conversation", item.conversation_id === conversation ? "" : item.conversation_id)
                  }
                >
                  <strong>{item.conversation_id}</strong>
                  <span>
                    {item.trace_count} turns
                    {item.error_count ? ` · ${item.error_count} failed` : ""}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="panel">
            <header className="panel-head">
              <h2>Runs</h2>
              <p>
                {data.traces.length} matching {data.traces.length === 1 ? "trace" : "traces"}
                {data.stats.by_agent.length
                  ? ` · ${data.stats.by_agent
                      .map((row) => `${row.agent_name} ${formatCost(row.cost_usd)}`)
                      .join(" · ")}`
                  : ""}
              </p>
            </header>
            {data.traces.length === 0 ? (
              <p className="empty">No runs match these filters.</p>
            ) : (
              <div className="table-wrap">
                <table className="runs">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Run</th>
                      <th>Agent</th>
                      <th>Duration</th>
                      <th>Tokens</th>
                      <th>Cost</th>
                      <th>When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.traces.map((trace) => (
                      <tr key={trace.trace_id} className={trace.status === "error" ? "row-error" : ""}>
                        <td>
                          <span className={trace.status === "error" ? "pill bad" : "pill ok"}>
                            {trace.status === "error" ? "failed" : "ok"}
                          </span>
                        </td>
                        <td>
                          <Link to={`/traces/${trace.trace_id}`}>{trace.name}</Link>
                          <div className="muted">{trace.input_summary}</div>
                          {trace.leaf_error_count > 0 && (
                            <div className="leaf-note">
                              {trace.leaf_error_count} failed {trace.leaf_error_count === 1 ? "step" : "steps"}
                              {trace.status === "ok" ? " · recovered" : ""}
                            </div>
                          )}
                        </td>
                        <td>{trace.agent_name}</td>
                        <td>{formatDuration(trace.duration_ms)}</td>
                        <td>{formatTokens(trace.total_input_tokens + trace.total_output_tokens)}</td>
                        <td>{formatCost(asNumber(trace.total_cost_usd))}</td>
                        <td>{formatWhen(trace.started_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "bad";
}) {
  return (
    <article className={tone === "bad" ? "stat tone-bad" : "stat"}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <em>{hint}</em>}
    </article>
  );
}
