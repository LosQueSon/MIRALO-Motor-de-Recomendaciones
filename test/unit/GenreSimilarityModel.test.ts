import { describe, expect, it } from "vitest";
import { GenreSimilarityModel } from "../../src/model/GenreSimilarityModel";

describe("GenreSimilarityModel", () => {
  it("builds co-occurrence relations and returns similar genres", () => {
    const model = new GenreSimilarityModel();

    model.train([
      { userId: "u1", favoriteGenres: ["Action", "Sci-Fi", "Adventure"] },
      { userId: "u2", favoriteGenres: ["Action", "Adventure"] },
      { userId: "u3", favoriteGenres: ["Sci-Fi", "Drama"] }
    ]);

    const similar = model.getSimilarGenres(["Action"]);

    expect(similar.length).toBeGreaterThan(0);
    expect(similar[0].genre).toBe("Adventure");
    expect(similar[0].score).toBeGreaterThan(similar[1]?.score ?? 0);
  });

  it("returns empty list when not trained", () => {
    const model = new GenreSimilarityModel();
    expect(model.getSimilarGenres(["Action"])).toEqual([]);
  });
});

