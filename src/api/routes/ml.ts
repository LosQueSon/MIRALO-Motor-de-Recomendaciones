import { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { MLPredictionService } from "../../service/MLPredictionService";

export const registerMLRoutes = (app: FastifyInstance): void => {
  const mlService = new MLPredictionService();

  /**
   * GET /ml/health
   * Verifica si el modelo está disponible
   */
  app.get<{ Querystring: {} }>(
    "/ml/health",
    async (request: FastifyRequest, reply: FastifyReply) => {
      const isTrained = await mlService.isModelTrained();
      
      return reply.status(isTrained ? 200 : 503).send({
        status: isTrained ? "ready" : "not_trained",
        message: isTrained 
          ? "ML model is ready" 
          : "ML model not trained yet. Run ml_model_training.py"
      });
    }
  );

  /**
   * POST /ml/predict
   * Predice películas para un usuario
   * 
   * Body (opciones):
   * {
   *   "favoriteGenres": ["Action", "Sci-Fi"],
   *   "topK": 10,
   *   "threshold": 0.5
   * }
   * O:
   * {
   *   "favoriteGenre": "Action",
   *   "topK": 10
   * }
   */
  app.post<{
    Body: {
      favoriteGenres?: string[];
      favoriteGenre?: string;
      topK?: number;
      threshold?: number;
    };
  }>(
    "/ml/predict",
    async (request: FastifyRequest<{
      Body: {
        favoriteGenres?: string[];
        favoriteGenre?: string;
        topK?: number;
        threshold?: number;
      };
    }>, reply: FastifyReply) => {
      // Convertir favoriteGenre singular a favoriteGenres array
      const genres = request.body.favoriteGenres || 
                     (request.body.favoriteGenre ? [request.body.favoriteGenre] : []);
      
      const predictions = await mlService.predictForUser({
        favoriteGenres: genres,
        topK: request.body.topK,
        threshold: request.body.threshold
      });
      
      if (!predictions.success) {
        return reply.status(400).send(predictions);
      }

      return reply.status(200).send({
        success: true,
        count: predictions.data?.length || 0,
        recommendations: predictions.data
      });
    }
  );

  app.post(
    "/ml/predict-room",
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const body = request.body as any;
        
        // Detectar si es un array directo o un objeto con propiedad "users"
        let users: Array<{ userId: string; favoriteGenres: string[] }>;
        let topK = 10;

        if (Array.isArray(body)) {
          // Estructura: array directo de usuarios
          users = body.map((user: any) => {
            const fg = user.favoriteGenres || (user.favoriteGenre ? [user.favoriteGenre] : []);
            // Normalizar: si el genero es 'other' o 'unknown' lo consideramos como lista vacía
            const normalized = (fg || []).map((g: string) => g?.toString?.().trim()).filter(Boolean).filter((g: string) => g.toLowerCase() !== 'other' && g.toLowerCase() !== 'unknown');
            return {
              userId: user.userId,
              favoriteGenres: normalized
            };
          });
        } else if (body.users) {
          // Estructura: { users: [...], topK: 10 }
          users = body.users.map((user: any) => {
            const fg = user.favoriteGenres || (user.favoriteGenre ? [user.favoriteGenre] : []);
            const normalized = (fg || []).map((g: string) => g?.toString?.().trim()).filter(Boolean).filter((g: string) => g.toLowerCase() !== 'other' && g.toLowerCase() !== 'unknown');
            return { userId: user.userId, favoriteGenres: normalized };
          });
          topK = body.topK || 10;
        } else {
          return reply.status(400).send({
            success: false,
            error: "Invalid request format. Expected array of users or object with 'users' property"
          });
        }

        const result = await mlService.predictForRoom(users, topK);
        
        if (!result.success) {
          return reply.status(400).send(result);
        }

        return reply.status(200).send({
          success: true,
          totalUsers: result.data.total_users,
          recommendationCount: result.data.recommendations?.length || 0,
          recommendations: result.data.recommendations
        });
      } catch (error) {
        return reply.status(400).send({
          success: false,
          error: error instanceof Error ? error.message : "Invalid request"
        });
      }
    }
  );

  /**
   * GET /ml/report
   * Obtiene el reporte de entrenamiento
   */
  app.get<{ Querystring: {} }>(
    "/ml/report",
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const report = await mlService.getTrainingReport();
        
        return reply.status(200).send({
          success: true,
          report: {
            timestamp: report.timestamp,
            dataset_info: report.dataset_info,
            xgboost_metrics: report.models_metrics[1],
            random_forest_metrics: report.models_metrics[0]
          }
        });
      } catch (error) {
        return reply.status(404).send({
          success: false,
          error: error instanceof Error ? error.message : "Unknown error"
        });
      }
    }
  );
};






