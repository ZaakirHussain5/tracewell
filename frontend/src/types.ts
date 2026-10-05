export type SpanStatus = "ok" | "error";

export interface Span {
  span_id: string;
  parent_span_id: string | null;
  op: string;
  name: string;
  status: SpanStatus;
  start_ms: number;
  duration_ms: number;
  agent_name: string;
  model: string;
  tool_name: string;
  provider: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cost_usd: string | number;
  input_text: string;
  output_text: string;
  error_type: string;
  error_message: string;
  attributes: Record<string, string | number | boolean | null>;
}

export interface SpanNode extends Span {
  children: SpanNode[];
}

export interface TraceSummary {
  trace_id: string;
  name: string;
  status: SpanStatus;
  environment: string;
  release: string;
  conversation_id: string;
  agent_name: string;
  started_at: string;
  duration_ms: number;
  input_summary: string;
  output_summary: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_read_tokens: number;
  total_cost_usd: string | number;
  error_span_count: number;
  leaf_error_count: number;
}

export interface ModelRollup {
  model: string;
  provider: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cost_usd: string | number;
  errors: number;
}

export interface AgentRollup {
  agent_name: string;
  traces: number;
  errors: number;
  cost_usd: string | number;
  tokens: number;
}

export interface Overview {
  project: { slug: string; name: string; description: string };
  agents: { name: string; description: string }[];
  conversations: {
    conversation_id: string;
    trace_count: number;
    error_count: number;
    title: string;
    last_started_at: string;
  }[];
  stats: {
    trace_count: number;
    error_count: number;
    error_rate: number;
    input_tokens: number;
    output_tokens: number;
    cache_read_tokens: number;
    cost_usd: string | number;
    leaf_errors: number;
    by_model: ModelRollup[];
    by_agent: AgentRollup[];
  };
  traces: TraceSummary[];
}

export interface Highlight {
  span_id: string;
  op: string;
  name: string;
  error_type: string;
  error_message: string;
  recovered: boolean;
}

export interface TraceDetail {
  trace: TraceSummary;
  spans: Span[];
  tree: SpanNode[];
  highlight: Highlight | null;
}
