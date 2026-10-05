from django.db import models


class Project(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Agent(models.Model):
    project = models.ForeignKey(Project, related_name="agents", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="uniq_agent_name_per_project"),
        ]

    def __str__(self) -> str:
        return self.name


class Trace(models.Model):
    project = models.ForeignKey(Project, related_name="traces", on_delete=models.CASCADE)
    trace_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=16)
    environment = models.CharField(max_length=32, default="production")
    release = models.CharField(max_length=64, blank=True)
    conversation_id = models.CharField(max_length=64, blank=True)
    agent_name = models.CharField(max_length=120, blank=True)
    started_at = models.DateTimeField()
    duration_ms = models.PositiveIntegerField()
    input_summary = models.TextField(blank=True)
    output_summary = models.TextField(blank=True)
    total_input_tokens = models.PositiveIntegerField(default=0)
    total_output_tokens = models.PositiveIntegerField(default=0)
    total_cache_read_tokens = models.PositiveIntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    error_span_count = models.PositiveIntegerField(default=0)
    leaf_error_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["conversation_id"]),
            models.Index(fields=["-started_at"]),
        ]

    def __str__(self) -> str:
        return self.name


class Span(models.Model):
    trace = models.ForeignKey(Trace, related_name="spans", on_delete=models.CASCADE)
    span_id = models.CharField(max_length=16)
    parent_span_id = models.CharField(max_length=16, blank=True, null=True)
    op = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=16)
    start_ms = models.PositiveIntegerField()
    duration_ms = models.PositiveIntegerField()
    agent_name = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=80, blank=True)
    tool_name = models.CharField(max_length=120, blank=True)
    provider = models.CharField(max_length=40, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    input_text = models.TextField(blank=True)
    output_text = models.TextField(blank=True)
    error_type = models.CharField(max_length=120, blank=True)
    error_message = models.TextField(blank=True)
    attributes = models.JSONField(default=dict)

    class Meta:
        ordering = ["start_ms", "id"]
        constraints = [
            models.UniqueConstraint(fields=["trace", "span_id"], name="uniq_span_per_trace"),
        ]
        indexes = [
            models.Index(fields=["trace", "status"]),
            models.Index(fields=["model"]),
        ]

    def __str__(self) -> str:
        return self.name
