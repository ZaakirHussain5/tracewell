from django.db import transaction

from traces.models import Agent, Project, Span, Trace
from traces.seed_data import AGENTS, PROJECT, demo_traces


def load_demo() -> dict:
    """Replace the Strata Ops project so reseeding is idempotent."""
    built = demo_traces()
    with transaction.atomic():
        Project.objects.filter(slug=PROJECT["slug"]).delete()
        project = Project.objects.create(**PROJECT)
        for agent in AGENTS:
            Agent.objects.create(project=project, **agent)
        span_count = 0
        for spec in built:
            spans = spec.pop("spans")
            trace = Trace.objects.create(project=project, **spec)
            Span.objects.bulk_create(Span(trace=trace, **span) for span in spans)
            span_count += len(spans)
    return {"project": project.slug, "traces": len(built), "spans": span_count}
