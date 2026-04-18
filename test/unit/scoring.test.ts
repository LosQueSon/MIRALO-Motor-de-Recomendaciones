import { describe, expect, it } from "vitest";
import { calculateItemScore } from "../../src/model/scoring";

describe("calculateItemScore", () => {
  it("combines direct, inferred and popularity scores", () => {
    const item = {
      itemId: "movie-1",
      type: "movie" as const,
      genres: ["Action", "Adventure"],
      popularityScore: 0.8
    };

    const score = calculateItemScore(item, ["Action"], ["Adventure"]);

    expect(score.directMatch).toBe(1);
    expect(score.inferredMatch).toBe(1);
    expect(score.popularity).toBe(0.8);
    expect(score.score).toBeCloseTo(0.97, 2);
  });

  it("handles empty user genres", () => {
    const item = {
      itemId: "series-1",
      type: "series" as const,
      genres: ["Mystery"],
      popularityScore: 0.5
    };

    const score = calculateItemScore(item, [], []);

    expect(score.directMatch).toBe(0);
    expect(score.inferredMatch).toBe(0);
    expect(score.score).toBeCloseTo(0.075, 3);
  });
});

