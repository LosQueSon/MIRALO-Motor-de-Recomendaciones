import { FastifyInstance } from "fastify";
import { MetricsRegistry } from "../../metrics/MetricsRegistry";

export const registerMetricsRoutes = (app: FastifyInstance, metrics: MetricsRegistry): void => {
  app.get("/metrics", async () => metrics.snapshot());
};

