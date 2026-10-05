# Tracewell

Tracewell is an agent trace explorer for **Strata Ops**, a seeded on-call console. It shows one agent run as a nested trace: the HTTP request, the agent span, each LLM call, each tool call, and database work in between. Failed steps stay highlighted. Token counts and model cost roll up from the same spans.

This is a proof of concept for the product surface of [Sentry Agent Tracing](https://docs.sentry.io/concepts/key-terms/agent-tracing/): `gen_ai.invoke_agent`, `gen_ai.chat`, and `gen_ai.execute_tool` spans inside a normal distributed trace, with inputs, outputs, latency, and cost on each step. The mapping write-up is in [docs/REPORT.md](docs/REPORT.md).

## Run with Docker

```bash
docker compose up --build
```

- UI: http://localhost:43111
- API: http://localhost:43110/api/health

Postgres is internal to Compose. The API container migrates and loads the Strata Ops demo on startup.

## Run locally

Backend (SQLite by default, Postgres when `DATABASE_URL` is set):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 43110
```

Frontend (proxies `/api` to port 43110):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:43111.

## Tests

```bash
cd backend && pytest
cd frontend && npm test && npm run typecheck
```

GitHub Actions runs the backend tests against Postgres 16 and the frontend tests, typecheck, and production build.

## What the demo contains

Eight traces in project **Strata Ops**:

| Run | What it shows |
| --- | --- |
| Triage checkout API latency page | Successful agent loop: classify, runbook query, PagerDuty, Grafana |
| Restart checkout-api after latency page | Failed `k8s.rollout_restart` (`TimeoutError`) inside an otherwise continued loop |
| Summarize customer impact for PINC441 | Model `RateLimitError` after a successful tool call |
| Review PR 1842 connection pool change | Expensive `claude-sonnet-4.5` review |
| Hand off payments replica lag to runbook | Nested `invoke_agent` plus a Postgres check |
| Scale checkout-api and recover a bad argument | Trace stays ok; the invalid `k8s.scale` span stays failed |
| Answer when the agent pages a human | MCP `execute_tool` |
| Follow up on customer impact for PINC441 | Cache-read tokens priced as a subset of input tokens |

The checkout incident turns share conversation `conv_oncall_441`.

## API

- `GET /api/health`
- `GET /api/overview?status=&agent=&conversation=&q=`
- `GET /api/traces/<trace_id>`

`seed_demo` replaces the Strata Ops project, so loading it again does not duplicate rows.
