from decimal import Decimal

from traces.pricing import span_cost
from traces.tree import assert_span_bounds, build_span_tree, highlight_for, primary_failure


def test_span_cost_counts_cache_as_subset_of_input():
    cost = span_cost("gpt-4.1", input_tokens=12000, output_tokens=180, cache_read_tokens=10000)
    # fresh 2000 * $2 + cache 10000 * $0.50 + output 180 * $8, per 1M tokens
    assert cost == Decimal("0.010440")


def test_span_cost_without_model_is_zero():
    assert span_cost("", 100, 100) == Decimal("0.000000")


def test_tree_nests_children_in_input_order():
    spans = [
        {"span_id": "root", "parent_span_id": None, "name": "root", "start_ms": 0},
        {"span_id": "a", "parent_span_id": "root", "name": "a", "start_ms": 1},
        {"span_id": "b", "parent_span_id": "root", "name": "b", "start_ms": 2},
        {"span_id": "a1", "parent_span_id": "a", "name": "a1", "start_ms": 3},
    ]
    tree = build_span_tree(spans)
    assert [node["span_id"] for node in tree] == ["root"]
    assert [node["span_id"] for node in tree[0]["children"]] == ["a", "b"]
    assert tree[0]["children"][0]["children"][0]["span_id"] == "a1"


def test_primary_failure_prefers_earliest_leaf_over_agent_wrapper():
    spans = [
        {
            "span_id": "agent",
            "op": "gen_ai.invoke_agent",
            "status": "error",
            "start_ms": 0,
            "error_type": "ToolFailure",
            "error_message": "wrapper",
            "name": "invoke_agent",
        },
        {
            "span_id": "tool",
            "op": "gen_ai.execute_tool",
            "status": "error",
            "start_ms": 50,
            "error_type": "TimeoutError",
            "error_message": "timed out",
            "name": "execute_tool k8s.rollout_restart",
        },
        {
            "span_id": "later",
            "op": "gen_ai.chat",
            "status": "error",
            "start_ms": 80,
            "error_type": "RateLimitError",
            "error_message": "later",
            "name": "chat",
        },
    ]
    chosen = primary_failure(spans)
    assert chosen["span_id"] == "tool"
    highlight = highlight_for(spans, "error")
    assert highlight["recovered"] is False
    assert highlight["error_type"] == "TimeoutError"


def test_recovered_highlight_when_trace_is_ok():
    spans = [
        {
            "span_id": "tool",
            "op": "gen_ai.execute_tool",
            "status": "error",
            "start_ms": 10,
            "error_type": "ValidationError",
            "error_message": "bad",
            "name": "execute_tool k8s.scale",
        }
    ]
    highlight = highlight_for(spans, "ok")
    assert highlight["recovered"] is True


def test_bounds_reject_child_that_escapes_parent():
    spans = [
        {"span_id": "p", "parent_span_id": None, "name": "parent", "start_ms": 0, "duration_ms": 10},
        {"span_id": "c", "parent_span_id": "p", "name": "child", "start_ms": 8, "duration_ms": 5},
    ]
    try:
        assert_span_bounds(spans)
    except ValueError as exc:
        assert "escapes" in str(exc)
    else:
        raise AssertionError("expected bounds error")
