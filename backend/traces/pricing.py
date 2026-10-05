"""Model prices used to roll token counts up to USD.

Rates are USD per 1M tokens. Cache-read tokens are a subset of input tokens,
matching Sentry's rule that cache and reasoning counts are not added on top of
the input/output totals.
"""

from decimal import Decimal, ROUND_HALF_UP

MILLION = Decimal(1_000_000)

PRICES: dict[str, dict[str, Decimal]] = {
    "gpt-4.1": {
        "input": Decimal("2"),
        "output": Decimal("8"),
        "cache_read": Decimal("0.5"),
    },
    "gpt-4.1-mini": {
        "input": Decimal("0.4"),
        "output": Decimal("1.6"),
        "cache_read": Decimal("0.1"),
    },
    "claude-sonnet-4.5": {
        "input": Decimal("3"),
        "output": Decimal("15"),
        "cache_read": Decimal("0.3"),
    },
}


def span_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
) -> Decimal:
    if not model:
        return Decimal("0.000000")
    price = PRICES[model]
    cache = min(max(cache_read_tokens, 0), max(input_tokens, 0))
    fresh = max(input_tokens, 0) - cache
    usd = (
        Decimal(fresh) * price["input"]
        + Decimal(cache) * price["cache_read"]
        + Decimal(max(output_tokens, 0)) * price["output"]
    ) / MILLION
    return usd.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
