import { FastifyInstance } from "fastify";
import { ModelService } from "../../service/ModelService";

export const registerHealthRoutes = (app: FastifyInstance, modelService: ModelService): void => {
  app.get("/health", async () => ({
    status: "ok",
    modelTrained: modelService.isTrained(),
    timestamp: new Date().toISOString()
  }));
};

