"""Pure helpers for nesting spans and picking the failure to highlight."""

LEAF_OPS = {"gen_ai.chat", "gen_ai.execute_tool", "db.query", "http.client"}


def build_span_tree(spans: list[dict]) -> list[dict]:
    """Nest flat spans by parent_span_id. Input order is preserved among siblings."""
    nodes: list[dict] = []
    by_id: dict[str, dict] = {}
    for span in spans:
        node = {**span, "children": []}
        nodes.append(node)
        by_id[span["span_id"]] = node
    roots: list[dict] = []
    for node in nodes:
        parent_id = node.get("parent_span_id") or None
        parent = by_id.get(parent_id) if parent_id else None
        if parent is None or parent is node:
            roots.append(node)
        else:
            parent["children"].append(node)
    return roots


def primary_failure(spans: list[dict]) -> dict | None:
    """Earliest leaf error (tool, model, db, http client), else earliest error span."""
    errors = [span for span in spans if span.get("status") == "error"]
    if not errors:
        return None
    leaves = [span for span in errors if span.get("op") in LEAF_OPS]
    pool = leaves or errors
    return min(pool, key=lambda span: (span.get("start_ms", 0), span.get("span_id", "")))


def highlight_for(spans: list[dict], trace_status: str) -> dict | None:
    chosen = primary_failure(spans)
    if chosen is None:
        return None
    return {
        "span_id": chosen["span_id"],
        "op": chosen["op"],
        "name": chosen["name"],
        "error_type": chosen.get("error_type") or "",
        "error_message": chosen.get("error_message") or "",
        "recovered": trace_status == "ok",
    }


def assert_span_bounds(spans: list[dict]) -> None:
    by_id = {span["span_id"]: span for span in spans}
    if len(by_id) != len(spans):
        raise ValueError("duplicate span_id")
    for span in spans:
        end = span["start_ms"] + span["duration_ms"]
        parent_id = span.get("parent_span_id")
        if not parent_id:
            continue
        parent = by_id.get(parent_id)
        if parent is None:
            raise ValueError(f"{span['name']} parent {parent_id} missing")
        parent_end = parent["start_ms"] + parent["duration_ms"]
        if span["start_ms"] < parent["start_ms"] or end > parent_end:
            raise ValueError(
                f"{span['name']} ({span['start_ms']}-{end}) escapes "
                f"{parent['name']} ({parent['start_ms']}-{parent_end})"
            )
