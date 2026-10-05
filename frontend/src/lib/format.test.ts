import { describe, expect, it } from "vitest";

import { formatCost, formatDuration, formatTokens } from "./format";

describe("format", () => {
  it("renders sub-cent model cost with four decimals", () => {
    expect(formatCost("0.000512")).toBe("$0.0005");
    expect(formatCost("0.010440")).toBe("$0.01");
    expect(formatCost(0.09)).toBe("$0.09");
    expect(formatCost(0)).toBe("$0.00");
  });

  it("compacts token counts", () => {
    expect(formatTokens(180)).toBe("180");
    expect(formatTokens(12000)).toBe("12k");
    expect(formatTokens(18000)).toBe("18k");
  });

  it("renders span durations", () => {
    expect(formatDuration(160)).toBe("160ms");
    expect(formatDuration(6000)).toBe("6.0s");
    expect(formatDuration(22000)).toBe("22s");
  });
});
