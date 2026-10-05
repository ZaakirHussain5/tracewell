import type { SpanNode } from "../types";
import { formatDuration } from "../lib/format";

export function SpanTree({
  nodes,
  depth = 0,
  selectedId,
  failureIds,
  onSelect,
}: {
  nodes: SpanNode[];
  depth?: number;
  selectedId: string;
  failureIds: Set<string>;
  onSelect: (spanId: string) => void;
}) {
  return (
    <ul className={depth === 0 ? "tree" : "tree nested"}>
      {nodes.map((node) => {
        const classes = [
          "tree-item",
          node.status === "error" ? "is-error" : "",
          node.status !== "error" && failureIds.has(node.span_id) ? "on-failure-path" : "",
          node.span_id === selectedId ? "is-selected" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <li key={node.span_id}>
            <button type="button" className={classes} onClick={() => onSelect(node.span_id)}>
              <span className="op-dot" data-op={node.op} />
              <span className="tree-name">{node.name}</span>
              {node.status === "error" && <span className="pill bad">failed</span>}
              <span className="tree-meta">{formatDuration(node.duration_ms)}</span>
            </button>
            {node.children.length > 0 && (
              <SpanTree
                nodes={node.children}
                depth={depth + 1}
                selectedId={selectedId}
                failureIds={failureIds}
                onSelect={onSelect}
              />
            )}
          </li>
        );
      })}
    </ul>
  );
}
