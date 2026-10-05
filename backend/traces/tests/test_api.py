from django.test import TestCase

from traces.seed import load_demo
from traces.seed_data import CONV_ONCALL, TRACE_RATE_LIMIT, TRACE_RESTART, TRACE_SCALE


class SeededApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_demo()

    def test_health(self):
        response = self.client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_overview_is_strata_ops(self):
        body = self.client.get("/api/overview").json()
        assert body["project"]["slug"] == "strata-ops"
        assert body["project"]["name"] == "Strata Ops"
        assert {agent["name"] for agent in body["agents"]} == {
            "Incident Commander",
            "Runbook Agent",
            "Change Reviewer",
            "Docs Agent",
        }
        assert body["stats"]["trace_count"] == 8
        assert body["stats"]["error_count"] == 2
        conversations = {item["conversation_id"] for item in body["conversations"]}
        assert CONV_ONCALL in conversations
        oncall = next(item for item in body["conversations"] if item["conversation_id"] == CONV_ONCALL)
        assert oncall["trace_count"] == 4
        assert oncall["error_count"] == 2

    def test_cost_rollup_matches_spans_and_models(self):
        body = self.client.get("/api/overview").json()
        from decimal import Decimal

        from traces.models import Span, Trace

        traces = list(Trace.objects.all())
        assert sum((trace.total_cost_usd for trace in traces), Decimal("0")) == Decimal(
            body["stats"]["cost_usd"]
        )
        for trace in traces:
            span_cost = sum((span.cost_usd for span in trace.spans.all()), Decimal("0"))
            assert trace.total_cost_usd == span_cost
        models = {row["model"] for row in body["stats"]["by_model"]}
        assert "claude-sonnet-4.5" in models
        assert "gpt-4.1" in models
        claude = next(row for row in body["stats"]["by_model"] if row["model"] == "claude-sonnet-4.5")
        assert Decimal(claude["cost_usd"]) == Decimal("0.090000")
        assert Span.objects.filter(op="db.query").exists()
        assert Span.objects.filter(op="http.server").count() == 8

    def test_error_filter_excludes_recovered_run(self):
        body = self.client.get("/api/overview", {"status": "error"}).json()
        ids = {trace["trace_id"] for trace in body["traces"]}
        assert ids == {TRACE_RESTART, TRACE_RATE_LIMIT}
        assert body["stats"]["trace_count"] == 2

    def test_search_finds_restart(self):
        body = self.client.get("/api/overview", {"q": "roll checkout-api"}).json()
        assert [trace["trace_id"] for trace in body["traces"]] == [TRACE_RESTART]

    def test_restart_trace_highlights_nested_tool_failure(self):
        response = self.client.get(f"/api/traces/{TRACE_RESTART}")
        assert response.status_code == 200
        body = response.json()
        assert body["trace"]["status"] == "error"
        assert body["highlight"]["recovered"] is False
        assert body["highlight"]["error_type"] == "TimeoutError"
        assert body["highlight"]["name"] == "execute_tool k8s.rollout_restart"

        def names(nodes):
            found = []
            for node in nodes:
                found.append(node["name"])
                found.extend(names(node["children"]))
            return found

        assert "execute_tool k8s.rollout_restart" in names(body["tree"])
        root = body["tree"][0]
        assert root["op"] == "http.server"
        agent = root["children"][0]
        assert agent["op"] == "gen_ai.invoke_agent"
        assert agent["status"] == "error"
        tool = next(child for child in agent["children"] if child["tool_name"] == "k8s.rollout_restart")
        assert tool["status"] == "error"
        assert tool["attributes"]["gen_ai.tool.name"] == "k8s.rollout_restart"
        assert tool["attributes"]["error.type"] == "TimeoutError"
        # The model call after the timeout still succeeded. Failure stays on the tool.
        later = [child for child in agent["children"] if child["start_ms"] > tool["start_ms"]]
        assert later
        assert all(child["status"] == "ok" for child in later)

    def test_recovered_scale_keeps_trace_ok_and_flags_tool(self):
        body = self.client.get(f"/api/traces/{TRACE_SCALE}").json()
        assert body["trace"]["status"] == "ok"
        assert body["highlight"]["recovered"] is True
        assert body["highlight"]["error_type"] == "ValidationError"
        assert body["trace"]["leaf_error_count"] == 1

    def test_failover_nests_runbook_agent(self):
        body = self.client.get("/api/traces/a11ce005a11ce005a11ce005a11ce005").json()
        agent = body["tree"][0]["children"][0]
        nested = next(child for child in agent["children"] if child["op"] == "gen_ai.invoke_agent")
        assert nested["agent_name"] == "Runbook Agent"
        assert any(child["op"] == "db.query" for child in nested["children"])
        assert any(child["tool_name"] == "postgres.check_replication" for child in nested["children"])

    def test_missing_trace(self):
        response = self.client.get("/api/traces/does-not-exist")
        assert response.status_code == 404

    def test_reseed_is_idempotent(self):
        first = load_demo()
        second = load_demo()
        assert first == second
        assert self.client.get("/api/overview").json()["stats"]["trace_count"] == 8
