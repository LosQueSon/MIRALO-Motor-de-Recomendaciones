import { FastifyInstance } from "fastify";
import { ModelService } from "../../service/ModelService";

export const registerModelRoutes = (app: FastifyInstance, modelService: ModelService): void => {
  app.post("/model/train", async () => {
    const result = await modelService.train();
    return {
      status: "trained",
      ...result
    };
  });

  app.get("/model/genres", async () => {
    const relations = await modelService.getGenreRelations();
    return {
      totalGenres: relations.length,
      relations
    };
  });
};

