import { formatDuration } from "../lib/format";
import type { WaterfallRow } from "../lib/spans";

export function Waterfall({
  rows,
  totalMs,
  selectedId,
  onSelect,
}: {
  rows: WaterfallRow[];
  totalMs: number;
  selectedId: string;
  onSelect: (spanId: string) => void;
}) {
  return (
    <div className="waterfall">
      <div className="waterfall-scale">
        <span>0</span>
        <span>{formatDuration(Math.round(totalMs / 2))}</span>
        <span>{formatDuration(totalMs)}</span>
      </div>
      {rows.map((row) => (
        <button
          key={row.span.span_id}
          type="button"
          className={row.span.span_id === selectedId ? "wf-row is-selected" : "wf-row"}
          onClick={() => onSelect(row.span.span_id)}
        >
          <span className="wf-label" style={{ paddingLeft: row.depth * 12 }}>
            {row.span.name}
          </span>
          <span className="wf-track">
            <span
              className={row.span.status === "error" ? "wf-bar is-error" : "wf-bar"}
              data-op={row.span.op}
              style={{ left: `${row.leftPct}%`, width: `${row.widthPct}%` }}
              title={`${row.span.name} · ${formatDuration(row.span.duration_ms)}`}
            />
          </span>
        </button>
      ))}
    </div>
  );
}
