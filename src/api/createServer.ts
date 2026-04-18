import Fastify, { FastifyInstance } from "fastify";
import { MetricsRegistry } from "../metrics/MetricsRegistry";
import { ModelService } from "../service/ModelService";
import { RecommendationService } from "../service/RecommendationService";
import { registerHealthRoutes } from "./routes/health";
import { registerMetricsRoutes } from "./routes/metrics";
import { registerModelRoutes } from "./routes/model";
import { registerRecommendationRoutes } from "./routes/recommendations";

interface CreateServerDeps {
  recommendationService: RecommendationService;
  modelService: ModelService;
  metrics: MetricsRegistry;
}

const REQUEST_START_KEY = "__requestStartTimeMs";

export const createServer = (deps: CreateServerDeps): FastifyInstance => {
  const app = Fastify({ logger: true });

  app.addHook("onRequest", async (request) => {
    (request as unknown as Record<string, number>)[REQUEST_START_KEY] = Date.now();
  });

  app.addHook("onResponse", async (request, reply) => {
    const start = (request as unknown as Record<string, number>)[REQUEST_START_KEY] ?? Date.now();
    const latencyMs = Date.now() - start;
    const endpoint = `${request.method} ${request.routeOptions.url}`;
    deps.metrics.trackRequest(endpoint, reply.statusCode, latencyMs);
  });

  registerHealthRoutes(app, deps.modelService);
  registerRecommendationRoutes(app, deps.recommendationService);
  registerModelRoutes(app, deps.modelService);
  registerMetricsRoutes(app, deps.metrics);

  return app;
};

