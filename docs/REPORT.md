# Tracewell and the Sentry Agent Tracing role

Tracewell is a small trace explorer built around the same question Sentry Agent Tracing answers: when an agent run goes wrong, which step did it, and what did that step cost?

Sentry's model is not a separate log of prompts. An agent run is a distributed trace. `gen_ai.invoke_agent` wraps the run. Each model request is a sibling `gen_ai.chat` span. Each tool or MCP call is a sibling `gen_ai.execute_tool` span. Those spans sit next to the HTTP request and the database queries the agent caused. Tokens and cost hang off the model spans. A conversation id groups turns that belong to the same chat. Tracewell implements that shape for one seeded product, Strata Ops, instead of ingesting a live SDK.

## The role, mapped onto this app

| Agent Tracing concern | Where Tracewell shows it |
| --- | --- |
| One run, many steps | A trace is one Strata Ops request. The span tree is the decision path. |
| `gen_ai.invoke_agent` | Every run has an agent span named `invoke_agent {agent}`. The payments-lag run nests a second one for Runbook Agent. |
| `gen_ai.chat` as a sibling of tools | Model spans end before the tool they request. Tool time is not folded into model latency. |
| `gen_ai.execute_tool`, including MCP | PagerDuty, Kubernetes, Grafana, GitHub, Slack, Postgres, and `mcp.search_docs`. |
| Same trace as the rest of the app | The root span is `http.server`. Runbook lookup is `db.query` under the agent that issued it. |
| Failure on the step that broke | `highlight` picks the earliest leaf error (`chat`, `execute_tool`, `db`, `http.client`), not the agent wrapper that only failed because a child failed. The tree and waterfall mark that span, and ancestors on the path. |
| Recovered runs | The scale run returns HTTP 200 and trace status `ok`, but `k8s.scale` with `replicas: -1` stays `error` / `ValidationError`. The banner says the run recovered. |
| Tokens and cost | Input, output, and cache-read totals per span, per trace, and per model. Cache-read tokens are a subset of input tokens and use a lower rate, which is how Sentry avoids double-counting. |
| Conversations | `conv_oncall_441` ties the latency triage, the failed restart, the rate-limited summary, and the cached follow-up into one incident thread. |
| Attributes a UI can trust | Spans carry `gen_ai.operation.name`, `gen_ai.request.model`, `gen_ai.provider.name`, `gen_ai.agent.name`, `gen_ai.tool.name`, `gen_ai.usage.*`, and `error.type`. |

The interesting failed run is `a11ce002a11ce002a11ce002a11ce002` ("Restart checkout-api after latency page"). The HTTP span and the Incident Commander span are both `error`, but the leaf cause is `execute_tool k8s.rollout_restart` / `TimeoutError` after six seconds. The chat span after it succeeded and posted to Slack. A flat "agent failed" status would hide that the model was fine and the Kubernetes call was not.

## Strata Ops

Strata Ops is the demo tenant: an on-call console whose agents triage pages, execute runbooks, and review deploys. Four agents are seeded (Incident Commander, Runbook Agent, Change Reviewer, Docs Agent). Eight traces cover the cases above. Costs use a small public-style price table in `backend/traces/pricing.py` so the UI numbers are reproducible without calling a provider.

Nothing here is a Sentry ingest pipeline. There is no SDK, no sampling, and no span storage format beyond Postgres rows shaped like the semantic conventions. `python manage.py seed_demo` replaces the project so the dataset stays fixed.

## Architecture

- **API** (`backend/`): Django, Postgres in Compose, SQLite when `DATABASE_URL` is unset. Read API only. Tree building, failure selection, and price math are pure functions with unit tests. API tests load the seed and check nesting, highlight selection, cost rollups, filters, and idempotent reseed.
- **UI** (`frontend/`): React and TypeScript. The explorer is the run list, model cost, and conversation chips. The trace page is the nested tree, a waterfall positioned by `start_ms`, and a span inspector for input, output, tokens, cost, and attributes. Span-tree and formatting tests run in Vitest.
- **Compose**: API published on **43110**, UI on **43111**. The UI nginx proxies `/api` to the API so the browser stays same-origin.
- **CI**: GitHub Actions. Backend tests run against Postgres 16. Frontend job runs Vitest, `tsc`, and the production build.

## What I would keep pressing on if this were the tracing product

- **The failure is a span, not a trace flag.** Operators need the leaf. Wrappers should show that they contain a failure without stealing the highlight.
- **Cost has to follow the usage attributes.** Cache-read and reasoning tokens are subsets. A second addition double-bills the same tokens.
- **Prompts are PII.** This demo stores input and output so the inspector is useful. A real product gates that on `send_default_pii` / `recordInputs` and still keeps timing, status, model, and token counts when the text is dropped.
- **Conversations are not trace ids.** The on-call thread reuses one conversation id across four traces. Deriving it from the trace id would merge the wrong turns.
- **Agent spans do not replace APM.** The restart timeout is only obvious because the tool span, the HTTP 500, and the later successful Slack span are in one waterfall.

## Out of scope

Live ingest, SDK auto-instrumentation, head-based sampling, auth, and multi-tenant writes. The API is a read model over a seed. The point of the POC is the trace you open when a Strata Ops agent fails, and the attributes that make that view possible.
