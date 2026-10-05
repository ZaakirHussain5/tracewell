"""Strata Ops demo traces.

Each trace is one agent run inside the on-call console. Spans follow the
Sentry agent hierarchy: gen_ai.invoke_agent wraps sibling gen_ai.chat and
gen_ai.execute_tool spans, and those sit beside http.server and db.query spans
in the same trace. Child intervals are strictly inside their parent.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from traces.pricing import span_cost
from traces.tree import LEAF_OPS, assert_span_bounds

PROJECT = {
    "slug": "strata-ops",
    "name": "Strata Ops",
    "description": (
        "On-call console for Strata Ops. Agents triage pages, run runbooks, "
        "and review deploys. Seeded demo traffic shaped like Sentry agent traces: "
        "nested LLM and tool spans beside HTTP and database spans."
    ),
}

AGENTS = [
    {
        "name": "Incident Commander",
        "description": "Classifies pages, pulls operational context, and decides whether a runbook should take over.",
    },
    {
        "name": "Runbook Agent",
        "description": "Executes a named runbook with internal tools and reports what changed.",
    },
    {
        "name": "Change Reviewer",
        "description": "Reads a pull request diff and posts a review focused on operability risk.",
    },
    {
        "name": "Docs Agent",
        "description": "Answers operator questions from internal docs through an MCP search tool.",
    },
]

RELEASE = "strata-ops@2026.9.28"
ENV = "production"

# Stable ids so the UI and tests can deep-link the interesting runs.
TRACE_PAGE = "a11ce001a11ce001a11ce001a11ce001"
TRACE_RESTART = "a11ce002a11ce002a11ce002a11ce002"
TRACE_RATE_LIMIT = "a11ce003a11ce003a11ce003a11ce003"
TRACE_REVIEW = "a11ce004a11ce004a11ce004a11ce004"
TRACE_FAILOVER = "a11ce005a11ce005a11ce005a11ce005"
TRACE_SCALE = "a11ce006a11ce006a11ce006a11ce006"
TRACE_DOCS = "a11ce007a11ce007a11ce007a11ce007"
TRACE_CACHE = "a11ce008a11ce008a11ce008a11ce008"

CONV_ONCALL = "conv_oncall_441"
CONV_DEPLOY = "conv_deploy_88"
CONV_FAILOVER = "conv_failover_12"
CONV_SCALE = "conv_scale_7"

_ANCHOR = datetime(2026, 10, 4, 11, 5, tzinfo=timezone.utc)


def _at(minutes: int) -> datetime:
    return _ANCHOR + timedelta(minutes=minutes)


class _Store:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.n = 0
        self.keys: dict[str, str] = {}
        self.spans: list[dict] = []

    def add(
        self,
        key: str,
        parent: str | None,
        *,
        op: str,
        name: str,
        status: str,
        start_ms: int,
        duration_ms: int,
        agent_name: str = "",
        model: str = "",
        response_model: str = "",
        tool_name: str = "",
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        input_text: str = "",
        output_text: str = "",
        error_type: str = "",
        error_message: str = "",
        attributes: dict | None = None,
    ) -> dict:
        self.n += 1
        span_id = f"{self.prefix}{self.n:04x}"
        parent_span_id = self.keys[parent] if parent else None
        cost = (
            span_cost(model, input_tokens, output_tokens, cache_read_tokens)
            if model
            else Decimal("0.000000")
        )
        attrs: dict = dict(attributes or {})
        attrs["sentry.op"] = op
        if op.startswith("gen_ai."):
            attrs["gen_ai.operation.name"] = op.split(".", 1)[1]
        if agent_name:
            attrs["gen_ai.agent.name"] = agent_name
        if model:
            attrs["gen_ai.request.model"] = model
            if response_model:
                attrs["gen_ai.response.model"] = response_model
            attrs["gen_ai.provider.name"] = provider
            attrs["gen_ai.usage.input_tokens"] = input_tokens
            attrs["gen_ai.usage.output_tokens"] = output_tokens
            if cache_read_tokens:
                attrs["gen_ai.usage.cache_read.input_tokens"] = cache_read_tokens
        if tool_name:
            attrs["gen_ai.tool.name"] = tool_name
            attrs["gen_ai.operation.name"] = "execute_tool"
        if error_type:
            attrs["error.type"] = error_type
        span = {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "op": op,
            "name": name,
            "status": status,
            "start_ms": start_ms,
            "duration_ms": duration_ms,
            "agent_name": agent_name,
            "model": model,
            "tool_name": tool_name,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cost_usd": cost,
            "input_text": input_text,
            "output_text": output_text,
            "error_type": error_type,
            "error_message": error_message,
            "attributes": attrs,
        }
        self.keys[key] = span_id
        self.spans.append(span)
        return span


def _finish(
    *,
    trace_id: str,
    name: str,
    status: str,
    started_at: datetime,
    conversation_id: str,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    store: _Store,
) -> dict:
    spans = store.spans
    assert_span_bounds(spans)
    duration = max(span["start_ms"] + span["duration_ms"] for span in spans)
    return {
        "trace_id": trace_id,
        "name": name,
        "status": status,
        "environment": ENV,
        "release": RELEASE,
        "conversation_id": conversation_id,
        "agent_name": agent_name,
        "started_at": started_at,
        "duration_ms": duration,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "total_input_tokens": sum(span["input_tokens"] for span in spans),
        "total_output_tokens": sum(span["output_tokens"] for span in spans),
        "total_cache_read_tokens": sum(span["cache_read_tokens"] for span in spans),
        "total_cost_usd": sum((span["cost_usd"] for span in spans), Decimal("0")),
        "error_span_count": sum(1 for span in spans if span["status"] == "error"),
        "leaf_error_count": sum(
            1 for span in spans if span["status"] == "error" and span["op"] in LEAF_OPS
        ),
        "spans": spans,
    }


def _page() -> dict:
    s = _Store("b10000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/incidents",
        status="ok",
        start_ms=0,
        duration_ms=4820,
        input_text="POST /api/incidents",
        output_text="200 application/json",
        attributes={
            "http.method": "POST",
            "http.route": "/api/incidents",
            "http.status_code": 200,
        },
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Incident Commander",
        status="ok",
        start_ms=40,
        duration_ms=4660,
        agent_name="Incident Commander",
        input_text="Checkout API p95 crossed 1.8s in us-east-1. Page from SLO burn.",
        output_text="Latency is concentrated in checkout-api dependency calls to payments-db. No restart recommended.",
    )
    s.add(
        "classify",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1-mini",
        status="ok",
        start_ms=80,
        duration_ms=340,
        agent_name="Incident Commander",
        model="gpt-4.1-mini",
        response_model="gpt-4.1-mini-2026-04-14",
        provider="openai",
        input_tokens=640,
        output_tokens=80,
        input_text="Classify this page: checkout p95 1.8s, us-east-1, SLO burn.",
        output_text='{"severity":"sev2","service":"checkout-api","action":"investigate"}',
    )
    s.add(
        "db",
        "agent",
        op="db.query",
        name="SELECT runbooks",
        status="ok",
        start_ms=450,
        duration_ms=70,
        input_text="SELECT id, title FROM runbooks WHERE service = 'checkout-api'",
        output_text="2 rows: checkout-latency, checkout-restart",
        attributes={"db.system": "postgresql", "db.name": "strata", "db.operation": "SELECT"},
    )
    s.add(
        "pd",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool pagerduty.get_incident",
        status="ok",
        start_ms=540,
        duration_ms=560,
        agent_name="Incident Commander",
        tool_name="pagerduty.get_incident",
        input_text='{"incident_id":"PINC441"}',
        output_text='{"title":"Checkout p95 burn","urgency":"high","status":"triggered"}',
    )
    s.add(
        "plan",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=1140,
        duration_ms=960,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=2100,
        output_tokens=320,
        input_text="Incident PINC441 is triggered. Runbooks: checkout-latency, checkout-restart. What should we query?",
        output_text="Query Grafana for checkout-api dependency latency over 30m, grouped by downstream.",
    )
    s.add(
        "graf",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool grafana.query_range",
        status="ok",
        start_ms=2140,
        duration_ms=1060,
        agent_name="Incident Commander",
        tool_name="grafana.query_range",
        input_text='{"expr":"histogram_quantile(0.95, checkout_downstream_latency)","window":"30m"}',
        output_text="payments-db p95 1.4s; inventory p95 80ms; fraud p95 40ms.",
    )
    s.add(
        "sum",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=3240,
        duration_ms=1260,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=2480,
        output_tokens=410,
        input_text="Grafana says payments-db dominates checkout latency. Summarize for the on-call channel.",
        output_text="Sev2 checkout latency is downstream of payments-db. Do not restart checkout-api. Page the data primary.",
    )
    return _finish(
        trace_id=TRACE_PAGE,
        name="Triage checkout API latency page",
        status="ok",
        started_at=_at(7),
        conversation_id=CONV_ONCALL,
        agent_name="Incident Commander",
        input_summary="Checkout API p95 crossed 1.8s in us-east-1.",
        output_summary="Latency sits on payments-db. Restarting checkout-api would not help.",
        store=s,
    )


def _restart() -> dict:
    s = _Store("b20000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/incidents/PINC441/act",
        status="error",
        start_ms=0,
        duration_ms=9100,
        input_text="POST /api/incidents/PINC441/act",
        output_text="500 application/json",
        error_type="AgentRunError",
        error_message="Runbook step failed.",
        attributes={
            "http.method": "POST",
            "http.route": "/api/incidents/{id}/act",
            "http.status_code": 500,
        },
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Incident Commander",
        status="error",
        start_ms=30,
        duration_ms=8970,
        agent_name="Incident Commander",
        input_text="Operator asked to roll checkout-api anyway after the latency page.",
        output_text="Restart failed. A human was paged.",
        error_type="ToolFailure",
        error_message="k8s.rollout_restart timed out.",
    )
    s.add(
        "chat1",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=60,
        duration_ms=840,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=1800,
        output_tokens=160,
        input_text="Operator override: restart checkout-api in payments.",
        output_text="Check the deployment is healthy, then call k8s.rollout_restart.",
    )
    s.add(
        "get",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool k8s.get_deployment",
        status="ok",
        start_ms=960,
        duration_ms=440,
        agent_name="Incident Commander",
        tool_name="k8s.get_deployment",
        input_text='{"namespace":"payments","name":"checkout-api"}',
        output_text='{"replicas":6,"ready":6,"image":"checkout-api:2026.9.27"}',
    )
    s.add(
        "chat2",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=1450,
        duration_ms=750,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=1320,
        output_tokens=90,
        input_text="Deployment checkout-api is 6/6 ready. Proceed?",
        output_text="Yes. Restart it and wait for ready replicas.",
    )
    s.add(
        "restart",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool k8s.rollout_restart",
        status="error",
        start_ms=2260,
        duration_ms=6000,
        agent_name="Incident Commander",
        tool_name="k8s.rollout_restart",
        input_text='{"namespace":"payments","name":"checkout-api","timeout_s":6}',
        output_text="",
        error_type="TimeoutError",
        error_message="Timed out after 6s waiting for deployment/checkout-api to become ready in namespace payments.",
    )
    s.add(
        "chat3",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=8300,
        duration_ms=500,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=980,
        output_tokens=140,
        input_text="k8s.rollout_restart raised TimeoutError. What should we tell the channel?",
        output_text="The restart did not finish. Stop retrying automatically and page the checkout primary.",
    )
    s.add(
        "slack",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool slack.post_message",
        status="ok",
        start_ms=8820,
        duration_ms=160,
        agent_name="Incident Commander",
        tool_name="slack.post_message",
        input_text='{"channel":"#incidents","text":"checkout-api restart timed out; paging primary"}',
        output_text='{"ts":"1760000000.0001","ok":true}',
    )
    return _finish(
        trace_id=TRACE_RESTART,
        name="Restart checkout-api after latency page",
        status="error",
        started_at=_at(23),
        conversation_id=CONV_ONCALL,
        agent_name="Incident Commander",
        input_summary="Operator override: roll checkout-api in payments.",
        output_summary="k8s.rollout_restart timed out. The channel was notified.",
        store=s,
    )


def _rate_limit() -> dict:
    s = _Store("b30000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/incidents/PINC441/summarize",
        status="error",
        start_ms=0,
        duration_ms=1400,
        input_text="POST /api/incidents/PINC441/summarize",
        output_text="503 application/json",
        error_type="AgentRunError",
        error_message="Model call failed.",
        attributes={
            "http.method": "POST",
            "http.route": "/api/incidents/{id}/summarize",
            "http.status_code": 503,
        },
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Incident Commander",
        status="error",
        start_ms=20,
        duration_ms=1330,
        agent_name="Incident Commander",
        input_text="Write a customer-impact note for PINC441.",
        output_text="",
        error_type="RateLimitError",
        error_message="The model call was rate limited.",
    )
    s.add(
        "pd",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool pagerduty.get_incident",
        status="ok",
        start_ms=40,
        duration_ms=360,
        agent_name="Incident Commander",
        tool_name="pagerduty.get_incident",
        input_text='{"incident_id":"PINC441"}',
        output_text='{"status":"acknowledged","title":"Checkout p95 burn"}',
    )
    s.add(
        "chat",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="error",
        start_ms=430,
        duration_ms=870,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="",
        provider="openai",
        input_tokens=1600,
        output_tokens=0,
        input_text="Summarize customer impact for an acknowledged checkout latency incident.",
        output_text="",
        error_type="RateLimitError",
        error_message="OpenAI returned 429 Too Many Requests after 2 retries.",
    )
    return _finish(
        trace_id=TRACE_RATE_LIMIT,
        name="Summarize customer impact for PINC441",
        status="error",
        started_at=_at(35),
        conversation_id=CONV_ONCALL,
        agent_name="Incident Commander",
        input_summary="Write a customer-impact note for the checkout incident.",
        output_summary="The model provider rate limited the summary call.",
        store=s,
    )


def _review() -> dict:
    s = _Store("b40000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/reviews",
        status="ok",
        start_ms=0,
        duration_ms=22000,
        input_text="POST /api/reviews",
        output_text="200 application/json",
        attributes={"http.method": "POST", "http.route": "/api/reviews", "http.status_code": 200},
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Change Reviewer",
        status="ok",
        start_ms=50,
        duration_ms=21750,
        agent_name="Change Reviewer",
        input_text="Review PR 1842 for operability risk.",
        output_text="Posted a review asking for a pool-size dashboard and a rollback note.",
    )
    s.add(
        "diff",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool github.get_pull_diff",
        status="ok",
        start_ms=80,
        duration_ms=820,
        agent_name="Change Reviewer",
        tool_name="github.get_pull_diff",
        input_text='{"repo":"strata/checkout","pull":1842}',
        output_text="Diff raises the payments-db pool from 20 to 80 connections and adds no metric.",
    )
    s.add(
        "chat",
        "agent",
        op="gen_ai.chat",
        name="chat claude-sonnet-4.5",
        status="ok",
        start_ms=1000,
        duration_ms=18000,
        agent_name="Change Reviewer",
        model="claude-sonnet-4.5",
        response_model="claude-sonnet-4-5-20250929",
        provider="anthropic",
        input_tokens=18000,
        output_tokens=2400,
        input_text="Full diff of PR 1842 attached. Focus on pool exhaustion and rollback.",
        output_text="Request a connection-pool saturation panel and an explicit rollback to 20 before merge.",
    )
    s.add(
        "post",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool github.create_review",
        status="ok",
        start_ms=19200,
        duration_ms=1800,
        agent_name="Change Reviewer",
        tool_name="github.create_review",
        input_text='{"pull":1842,"event":"REQUEST_CHANGES"}',
        output_text='{"review_id":9912,"state":"CHANGES_REQUESTED"}',
    )
    return _finish(
        trace_id=TRACE_REVIEW,
        name="Review PR 1842 connection pool change",
        status="ok",
        started_at=_at(0),
        conversation_id=CONV_DEPLOY,
        agent_name="Change Reviewer",
        input_summary="Review the checkout payments-db pool increase.",
        output_summary="Changes requested: add a saturation panel and a rollback note.",
        store=s,
    )


def _failover() -> dict:
    s = _Store("b50000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/incidents",
        status="ok",
        start_ms=0,
        duration_ms=12000,
        input_text="POST /api/incidents",
        output_text="200 application/json",
        attributes={"http.method": "POST", "http.route": "/api/incidents", "http.status_code": 200},
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Incident Commander",
        status="ok",
        start_ms=40,
        duration_ms=11760,
        agent_name="Incident Commander",
        input_text="Replica lag on payments primary is 45s.",
        output_text="Runbook Agent confirmed lag is falling. No failover.",
    )
    s.add(
        "classify",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1-mini",
        status="ok",
        start_ms=80,
        duration_ms=420,
        agent_name="Incident Commander",
        model="gpt-4.1-mini",
        response_model="gpt-4.1-mini-2026-04-14",
        provider="openai",
        input_tokens=520,
        output_tokens=70,
        input_text="Alert: payments primary replica lag 45s.",
        output_text='{"severity":"sev2","service":"payments-db","action":"runbook"}',
    )
    s.add(
        "alerts",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool pagerduty.list_alerts",
        status="ok",
        start_ms=540,
        duration_ms=660,
        agent_name="Incident Commander",
        tool_name="pagerduty.list_alerts",
        input_text='{"service":"payments-db","since":"1h"}',
        output_text="1 open alert: replica_lag_seconds > 30.",
    )
    s.add(
        "decide",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=1260,
        duration_ms=840,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=1400,
        output_tokens=180,
        input_text="Only replica lag is firing. Hand off to the db-lag runbook?",
        output_text="Yes. Hand off to Runbook Agent with runbook db-replica-lag.",
    )
    s.add(
        "child",
        "agent",
        op="gen_ai.invoke_agent",
        name="invoke_agent Runbook Agent",
        status="ok",
        start_ms=2200,
        duration_ms=7600,
        agent_name="Runbook Agent",
        input_text="Run db-replica-lag for payments.",
        output_text="Lag fell from 45s to 6s during the check. No failover.",
    )
    s.add(
        "db",
        "child",
        op="db.query",
        name="SELECT runbook db-replica-lag",
        status="ok",
        start_ms=2300,
        duration_ms=200,
        input_text="SELECT body FROM runbooks WHERE slug = 'db-replica-lag'",
        output_text="Steps: read pg_stat_replication, post lag to Slack, do not failover under 60s.",
        attributes={"db.system": "postgresql", "db.name": "strata", "db.operation": "SELECT"},
    )
    s.add(
        "childchat",
        "child",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=2550,
        duration_ms=1650,
        agent_name="Runbook Agent",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=1100,
        output_tokens=150,
        input_text="Runbook says measure replication before any failover.",
        output_text="Call postgres.check_replication on payments.",
    )
    s.add(
        "pg",
        "child",
        op="gen_ai.execute_tool",
        name="execute_tool postgres.check_replication",
        status="ok",
        start_ms=4300,
        duration_ms=2700,
        agent_name="Runbook Agent",
        tool_name="postgres.check_replication",
        input_text='{"cluster":"payments","threshold_s":60}',
        output_text='{"lag_s":6,"state":"streaming","failover":false}',
    )
    s.add(
        "childsum",
        "child",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=7100,
        duration_ms=1900,
        agent_name="Runbook Agent",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=900,
        output_tokens=160,
        input_text="Replication lag is 6s and streaming. Fail over?",
        output_text="No. Lag is under the 60s threshold. Tell the channel it is recovering.",
    )
    s.add(
        "slack",
        "child",
        op="gen_ai.execute_tool",
        name="execute_tool slack.post_message",
        status="ok",
        start_ms=9100,
        duration_ms=500,
        agent_name="Runbook Agent",
        tool_name="slack.post_message",
        input_text='{"channel":"#data-primary","text":"payments replica lag 6s, no failover"}',
        output_text='{"ok":true}',
    )
    s.add(
        "final",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=9900,
        duration_ms=1600,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=760,
        output_tokens=120,
        input_text="Runbook Agent reports lag 6s and no failover.",
        output_text="Close the loop: sev2 is recovering, data primary already notified.",
    )
    return _finish(
        trace_id=TRACE_FAILOVER,
        name="Hand off payments replica lag to runbook",
        status="ok",
        started_at=_at(185),
        conversation_id=CONV_FAILOVER,
        agent_name="Incident Commander",
        input_summary="Payments primary replica lag is 45s.",
        output_summary="Nested runbook measured lag at 6s and skipped failover.",
        store=s,
    )


def _scale() -> dict:
    s = _Store("b60000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/runbooks/scale",
        status="ok",
        start_ms=0,
        duration_ms=6400,
        input_text="POST /api/runbooks/scale",
        output_text="200 application/json",
        attributes={"http.method": "POST", "http.route": "/api/runbooks/scale", "http.status_code": 200},
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Runbook Agent",
        status="ok",
        start_ms=30,
        duration_ms=6270,
        agent_name="Runbook Agent",
        input_text="Scale checkout-api to match the operator note.",
        output_text="First scale call was invalid. Retried with 4 replicas and succeeded.",
    )
    s.add(
        "chat1",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=60,
        duration_ms=740,
        agent_name="Runbook Agent",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=700,
        output_tokens=80,
        input_text="Note says 'scale down hard'. Current replicas: 6.",
        output_text="Call k8s.scale with replicas -1 to drain.",
    )
    s.add(
        "bad",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool k8s.scale",
        status="error",
        start_ms=860,
        duration_ms=340,
        agent_name="Runbook Agent",
        tool_name="k8s.scale",
        input_text='{"namespace":"payments","name":"checkout-api","replicas":-1}',
        output_text="",
        error_type="ValidationError",
        error_message="spec.replicas must be >= 0, got -1.",
    )
    s.add(
        "chat2",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=1260,
        duration_ms=740,
        agent_name="Runbook Agent",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=640,
        output_tokens=70,
        input_text="k8s.scale rejected replicas -1. Pick a legal value.",
        output_text="Retry with replicas 4.",
    )
    s.add(
        "good",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool k8s.scale",
        status="ok",
        start_ms=2060,
        duration_ms=740,
        agent_name="Runbook Agent",
        tool_name="k8s.scale",
        input_text='{"namespace":"payments","name":"checkout-api","replicas":4}',
        output_text='{"replicas":4,"ready":4}',
    )
    s.add(
        "chat3",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=2860,
        duration_ms=1140,
        agent_name="Runbook Agent",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=500,
        output_tokens=110,
        input_text="Scale to 4 succeeded after a validation error.",
        output_text="Report the bad argument and the successful retry. Do not hide the failed call.",
    )
    return _finish(
        trace_id=TRACE_SCALE,
        name="Scale checkout-api and recover a bad argument",
        status="ok",
        started_at=_at(237),
        conversation_id=CONV_SCALE,
        agent_name="Runbook Agent",
        input_summary="Scale checkout-api from an operator note.",
        output_summary="replicas -1 was rejected. A retry at 4 replicas succeeded.",
        store=s,
    )


def _docs() -> dict:
    s = _Store("b70000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/ask",
        status="ok",
        start_ms=0,
        duration_ms=3100,
        input_text="POST /api/ask",
        output_text="200 application/json",
        attributes={"http.method": "POST", "http.route": "/api/ask", "http.status_code": 200},
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Docs Agent",
        status="ok",
        start_ms=20,
        duration_ms=2980,
        agent_name="Docs Agent",
        input_text="How does the agent decide to page a human?",
        output_text="It pages a human when a tool fails closed or a runbook says not to retry.",
    )
    s.add(
        "ask",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1-mini",
        status="ok",
        start_ms=40,
        duration_ms=260,
        agent_name="Docs Agent",
        model="gpt-4.1-mini",
        response_model="gpt-4.1-mini-2026-04-14",
        provider="openai",
        input_tokens=280,
        output_tokens=40,
        input_text="How does the agent decide to page a human?",
        output_text="Search the on-call policy docs.",
    )
    s.add(
        "mcp",
        "agent",
        op="gen_ai.execute_tool",
        name="execute_tool mcp.search_docs",
        status="ok",
        start_ms=340,
        duration_ms=1460,
        agent_name="Docs Agent",
        tool_name="mcp.search_docs",
        input_text='{"server":"strata-docs","query":"when to page a human"}',
        output_text="Policy: page a human if a mutating tool errors or the runbook forbids a retry.",
        attributes={"mcp.server": "strata-docs"},
    )
    s.add(
        "answer",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1-mini",
        status="ok",
        start_ms=1860,
        duration_ms=1040,
        agent_name="Docs Agent",
        model="gpt-4.1-mini",
        response_model="gpt-4.1-mini-2026-04-14",
        provider="openai",
        input_tokens=860,
        output_tokens=150,
        input_text="Docs: page a human when a mutating tool errors or a runbook forbids retry.",
        output_text="The agent pages a human when a mutating tool fails, or when the runbook says not to retry.",
    )
    return _finish(
        trace_id=TRACE_DOCS,
        name="Answer when the agent pages a human",
        status="ok",
        started_at=_at(155),
        conversation_id="",
        agent_name="Docs Agent",
        input_summary="How does the agent decide to page a human?",
        output_summary="It pages when a mutating tool fails or the runbook forbids a retry.",
        store=s,
    )


def _cache() -> dict:
    s = _Store("b80000000000")
    s.add(
        "http",
        None,
        op="http.server",
        name="POST /api/incidents/PINC441/followup",
        status="ok",
        start_ms=0,
        duration_ms=2600,
        input_text="POST /api/incidents/PINC441/followup",
        output_text="200 application/json",
        attributes={
            "http.method": "POST",
            "http.route": "/api/incidents/{id}/followup",
            "http.status_code": 200,
        },
    )
    s.add(
        "agent",
        "http",
        op="gen_ai.invoke_agent",
        name="invoke_agent Incident Commander",
        status="ok",
        start_ms=20,
        duration_ms=2480,
        agent_name="Incident Commander",
        input_text="Any customer impact from PINC441?",
        output_text="Checkout error rate stayed flat. Impact is latency, not failures.",
    )
    s.add(
        "chat",
        "agent",
        op="gen_ai.chat",
        name="chat gpt-4.1",
        status="ok",
        start_ms=40,
        duration_ms=2360,
        agent_name="Incident Commander",
        model="gpt-4.1",
        response_model="gpt-4.1-2026-04-14",
        provider="openai",
        input_tokens=12000,
        output_tokens=180,
        cache_read_tokens=10000,
        input_text="Follow-up on PINC441. System prompt and incident transcript are cached. Any customer impact?",
        output_text="No error-rate regression. Customers saw slower checkout, not failed payments.",
    )
    return _finish(
        trace_id=TRACE_CACHE,
        name="Follow up on customer impact for PINC441",
        status="ok",
        started_at=_at(37),
        conversation_id=CONV_ONCALL,
        agent_name="Incident Commander",
        input_summary="Any customer impact from the checkout incident?",
        output_summary="Latency only. Most of the prompt was served from cache.",
        store=s,
    )


def demo_traces() -> list[dict]:
    traces = [_review(), _page(), _restart(), _rate_limit(), _cache(), _docs(), _failover(), _scale()]
    ids = [trace["trace_id"] for trace in traces]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate trace_id")
    return traces
