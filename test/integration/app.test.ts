import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { FastifyInstance } from "fastify";
import { createServer } from "../../src/api/createServer";
import {
  InMemoryGenreRelationsRepository,
  InMemoryItemMetadataRepository,
  InMemoryRecommendationSnapshotRepository,
  InMemoryUserPreferenceRepository
} from "../../src/data/repositories/inMemoryRepositories";
import { MetricsRegistry } from "../../src/metrics/MetricsRegistry";
import { GenreSimilarityModel } from "../../src/model/GenreSimilarityModel";
import { GenreModelRecommender } from "../../src/model/recommenders/GenreModelRecommender";
import { RuleBasedRecommender } from "../../src/model/recommenders/RuleBasedRecommender";
import { ModelService } from "../../src/service/ModelService";
import { RecommendationService } from "../../src/service/RecommendationService";

const users = [
  { userId: "u1", favoriteGenres: ["Action", "Sci-Fi", "Adventure"] },
  { userId: "u2", favoriteGenres: ["Drama"] },
  { userId: "u3", favoriteGenres: [] },
  { userId: "u4", favoriteGenres: ["UnknownGenre"] }
];

const items = [
  { itemId: "m1", type: "movie" as const, genres: ["Action", "Adventure"], popularityScore: 0.9 },
  { itemId: "m2", type: "movie" as const, genres: ["Drama"], popularityScore: 0.7 },
  { itemId: "s1", type: "series" as const, genres: ["Sci-Fi"], popularityScore: 0.8 },
  { itemId: "s2", type: "series" as const, genres: ["Mystery"], popularityScore: 0.6 }
];

const buildApp = (): { app: FastifyInstance; modelService: ModelService } => {
  const userRepository = new InMemoryUserPreferenceRepository(users);
  const itemRepository = new InMemoryItemMetadataRepository(items);
  const relationsRepository = new InMemoryGenreRelationsRepository();
  const snapshotRepository = new InMemoryRecommendationSnapshotRepository();

  const model = new GenreSimilarityModel();
  const metrics = new MetricsRegistry();

  const primary = new GenreModelRecommender(userRepository, itemRepository, relationsRepository, model);
  const fallback = new RuleBasedRecommender(userRepository, itemRepository);

  const recommendationService = new RecommendationService(
    userRepository,
    primary,
    fallback,
    snapshotRepository,
    metrics
  );

  const modelService = new ModelService(userRepository, relationsRepository, model);

  const app = createServer({ recommendationService, modelService, metrics });
  return { app, modelService };
};

describe("API integration", () => {
  let app: FastifyInstance;
  let modelService: ModelService;

  beforeEach(async () => {
    const built = buildApp();
    app = built.app;
    modelService = built.modelService;
    await app.ready();
  });

  afterEach(async () => {
    await app.close();
  });

  it("handles user without genres using fallback", async () => {
    const response = await app.inject({ method: "GET", url: "/recommendations/u3?limit=5" });
    expect(response.statusCode).toBe(200);

    const payload = response.json();
    expect(payload.total).toBeGreaterThan(0);
  });

  it("supports unknown genres without failing", async () => {
    const response = await app.inject({ method: "GET", url: "/recommendations/u4?limit=3" });
    expect(response.statusCode).toBe(200);

    const payload = response.json();
    expect(payload.recommendations.movies.length + payload.recommendations.series.length).toBeGreaterThan(0);
  });

  it("returns model data after training", async () => {
    const trainResponse = await app.inject({ method: "POST", url: "/model/train" });
    expect(trainResponse.statusCode).toBe(200);

    const genresResponse = await app.inject({ method: "GET", url: "/model/genres" });
    expect(genresResponse.statusCode).toBe(200);

    const payload = genresResponse.json();
    expect(payload.totalGenres).toBeGreaterThan(0);
    expect(modelService.isTrained()).toBe(true);
  });

  it("maintains stability under high request volume", async () => {
    await modelService.train();

    const requests = Array.from({ length: 100 }, () =>
      app.inject({ method: "GET", url: "/recommendations/u1?limit=5" })
    );

    const responses = await Promise.all(requests);
    expect(responses.every((response) => response.statusCode === 200)).toBe(true);
  });

  it("exposes metrics endpoint", async () => {
    await app.inject({ method: "GET", url: "/recommendations/u1?limit=2" });
    const response = await app.inject({ method: "GET", url: "/metrics" });

    expect(response.statusCode).toBe(200);
    const payload = response.json();
    expect(payload.recommendations_generated).toBeGreaterThan(0);
  });
});

