import { FastifyInstance } from "fastify";
import { RecommendationService } from "../../service/RecommendationService";

interface RecommendationParams {
  userId: string;
}

interface RecommendationQuery {
  limit?: string;
}

export const registerRecommendationRoutes = (
  app: FastifyInstance,
  recommendationService: RecommendationService
): void => {
  app.get<{ Params: RecommendationParams; Querystring: RecommendationQuery }>(
    "/recommendations/:userId",
    async (request) => {
      const limit = Math.max(1, Number.parseInt(request.query.limit ?? "10", 10) || 10);
      const { userId } = request.params;

      const recommendations = await recommendationService.recommend(userId, limit);

      return {
        userId,
        total: recommendations.length,
        recommendations: {
          movies: recommendations.filter((rec) => rec.type === "movie"),
          series: recommendations.filter((rec) => rec.type === "series"),
          genres: recommendations.filter((rec) => rec.type === "genre")
        }
      };
    }
  );
};

