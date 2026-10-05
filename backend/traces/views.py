from django.db.models import Count, Q, Sum
from django.http import JsonResponse

from traces.models import Project, Span, Trace
from traces.seed_data import PROJECT
from traces.tree import build_span_tree, highlight_for


def health(_request):
    Project.objects.exists()
    return JsonResponse({"status": "ok"})


def _project():
    return Project.objects.filter(slug=PROJECT["slug"]).first()


def _filter_traces(project: Project, params):
    qs = project.traces.all()
    status = params.get("status", "")
    if status in {"ok", "error"}:
        qs = qs.filter(status=status)
    agent = params.get("agent", "").strip()
    if agent:
        qs = qs.filter(agent_name=agent)
    conversation = params.get("conversation", "").strip()
    if conversation:
        qs = qs.filter(conversation_id=conversation)
    query = params.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(input_summary__icontains=query)
            | Q(output_summary__icontains=query)
            | Q(agent_name__icontains=query)
        )
    return qs


def _trace_summary(trace: Trace) -> dict:
    return {
        "trace_id": trace.trace_id,
        "name": trace.name,
        "status": trace.status,
        "environment": trace.environment,
        "release": trace.release,
        "conversation_id": trace.conversation_id,
        "agent_name": trace.agent_name,
        "started_at": trace.started_at,
        "duration_ms": trace.duration_ms,
        "input_summary": trace.input_summary,
        "output_summary": trace.output_summary,
        "total_input_tokens": trace.total_input_tokens,
        "total_output_tokens": trace.total_output_tokens,
        "total_cache_read_tokens": trace.total_cache_read_tokens,
        "total_cost_usd": trace.total_cost_usd,
        "error_span_count": trace.error_span_count,
        "leaf_error_count": trace.leaf_error_count,
    }


def _span_dict(span: Span) -> dict:
    return {
        "span_id": span.span_id,
        "parent_span_id": span.parent_span_id,
        "op": span.op,
        "name": span.name,
        "status": span.status,
        "start_ms": span.start_ms,
        "duration_ms": span.duration_ms,
        "agent_name": span.agent_name,
        "model": span.model,
        "tool_name": span.tool_name,
        "provider": span.provider,
        "input_tokens": span.input_tokens,
        "output_tokens": span.output_tokens,
        "cache_read_tokens": span.cache_read_tokens,
        "cost_usd": span.cost_usd,
        "input_text": span.input_text,
        "output_text": span.output_text,
        "error_type": span.error_type,
        "error_message": span.error_message,
        "attributes": span.attributes,
    }


def _stats(qs):
    aggregate = qs.aggregate(
        trace_count=Count("id"),
        error_count=Count("id", filter=Q(status="error")),
        input_tokens=Sum("total_input_tokens"),
        output_tokens=Sum("total_output_tokens"),
        cache_read_tokens=Sum("total_cache_read_tokens"),
        cost=Sum("total_cost_usd"),
        leaf_errors=Sum("leaf_error_count"),
    )
    trace_count = aggregate["trace_count"] or 0
    error_count = aggregate["error_count"] or 0
    ids = list(qs.values_list("id", flat=True))
    by_model = []
    if ids:
        rows = (
            Span.objects.filter(trace_id__in=ids)
            .exclude(model="")
            .values("model", "provider")
            .annotate(
                calls=Count("id"),
                input_tokens=Sum("input_tokens"),
                output_tokens=Sum("output_tokens"),
                cache_read_tokens=Sum("cache_read_tokens"),
                cost=Sum("cost_usd"),
                errors=Count("id", filter=Q(status="error")),
            )
            .order_by("-cost")
        )
        for row in rows:
            by_model.append(
                {
                    "model": row["model"],
                    "provider": row["provider"],
                    "calls": row["calls"],
                    "input_tokens": row["input_tokens"] or 0,
                    "output_tokens": row["output_tokens"] or 0,
                    "cache_read_tokens": row["cache_read_tokens"] or 0,
                    "cost_usd": row["cost"] or 0,
                    "errors": row["errors"],
                }
            )
    by_agent = [
        {
            "agent_name": row["agent_name"],
            "traces": row["traces"],
            "errors": row["errors"],
            "cost_usd": row["cost"] or 0,
            "tokens": (row["input_tokens"] or 0) + (row["output_tokens"] or 0),
        }
        for row in qs.values("agent_name")
        .annotate(
            traces=Count("id"),
            errors=Count("id", filter=Q(status="error")),
            cost=Sum("total_cost_usd"),
            input_tokens=Sum("total_input_tokens"),
            output_tokens=Sum("total_output_tokens"),
        )
        .order_by("-cost")
    ]
    return {
        "trace_count": trace_count,
        "error_count": error_count,
        "error_rate": (error_count / trace_count) if trace_count else 0,
        "input_tokens": aggregate["input_tokens"] or 0,
        "output_tokens": aggregate["output_tokens"] or 0,
        "cache_read_tokens": aggregate["cache_read_tokens"] or 0,
        "cost_usd": aggregate["cost"] or 0,
        "leaf_errors": aggregate["leaf_errors"] or 0,
        "by_model": by_model,
        "by_agent": by_agent,
    }


def _conversations(project: Project):
    grouped: dict[str, dict] = {}
    for trace in project.traces.exclude(conversation_id="").order_by("started_at"):
        bucket = grouped.get(trace.conversation_id)
        if bucket is None:
            bucket = {
                "conversation_id": trace.conversation_id,
                "trace_count": 0,
                "error_count": 0,
                "title": trace.name,
                "last_started_at": trace.started_at,
            }
            grouped[trace.conversation_id] = bucket
        bucket["trace_count"] += 1
        if trace.status == "error":
            bucket["error_count"] += 1
        bucket["title"] = trace.name
        bucket["last_started_at"] = trace.started_at
    return sorted(grouped.values(), key=lambda item: item["last_started_at"], reverse=True)


def overview(request):
    project = _project()
    if project is None:
        return JsonResponse(
            {"detail": "Demo project is not seeded. Run python manage.py seed_demo."},
            status=404,
        )
    filtered = _filter_traces(project, request.GET)
    return JsonResponse(
        {
            "project": {
                "slug": project.slug,
                "name": project.name,
                "description": project.description,
            },
            "agents": [
                {"name": agent.name, "description": agent.description}
                for agent in project.agents.all()
            ],
            "conversations": _conversations(project),
            "stats": _stats(filtered),
            "traces": [_trace_summary(trace) for trace in filtered],
        }
    )


def trace_detail(_request, trace_id: str):
    project = _project()
    if project is None:
        return JsonResponse({"detail": "Demo project is not seeded."}, status=404)
    trace = project.traces.filter(trace_id=trace_id).first()
    if trace is None:
        return JsonResponse({"detail": "Trace not found."}, status=404)
    spans = [_span_dict(span) for span in trace.spans.all()]
    return JsonResponse(
        {
            "trace": _trace_summary(trace),
            "spans": spans,
            "tree": build_span_tree(spans),
            "highlight": highlight_for(spans, trace.status),
        }
    )
