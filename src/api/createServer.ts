import Fastify, { FastifyInstance } from "fastify";
import { registerMLRoutes } from "./routes/ml";

export const createServer = (): FastifyInstance => {
  const app = Fastify({ logger: true });

  // Registrar rutas ML (MIRALO Recommendation Engine)
  registerMLRoutes(app);

  return app;
};

