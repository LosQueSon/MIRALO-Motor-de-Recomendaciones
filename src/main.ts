import { createServer } from "./api/createServer";
import { getConfig } from "./config/env";
import { MongoConnection } from "./data/mongo";
import {
  MongoGenreRelationsRepository,
  MongoItemMetadataRepository,
  MongoRecommendationSnapshotRepository,
  MongoUserPreferenceRepository
} from "./data/repositories/mongoRepositories";
import { MetricsRegistry } from "./metrics/MetricsRegistry";
import { GenreSimilarityModel } from "./model/GenreSimilarityModel";
import { GenreModelRecommender } from "./model/recommenders/GenreModelRecommender";
import { RuleBasedRecommender } from "./model/recommenders/RuleBasedRecommender";
import { ModelService } from "./service/ModelService";
import { RecommendationService } from "./service/RecommendationService";

const bootstrap = async (): Promise<void> => {
  const config = getConfig();
  const mongoConnection = new MongoConnection(config.mongoUri, config.mongoDbName);
  const db = await mongoConnection.connect();

  const userRepository = new MongoUserPreferenceRepository(db);
  const itemRepository = new MongoItemMetadataRepository(db);
  const genreRelationsRepository = new MongoGenreRelationsRepository(db);
  const snapshotRepository = new MongoRecommendationSnapshotRepository(db);

  const model = new GenreSimilarityModel();
  const metrics = new MetricsRegistry();

  const primaryStrategy = new GenreModelRecommender(
    userRepository,
    itemRepository,
    genreRelationsRepository,
    model
  );

  const fallbackStrategy = new RuleBasedRecommender(userRepository, itemRepository);

  const recommendationService = new RecommendationService(
    userRepository,
    primaryStrategy,
    fallbackStrategy,
    snapshotRepository,
    metrics
  );

  const modelService = new ModelService(userRepository, genreRelationsRepository, model);

  const app = createServer({
    recommendationService,
    modelService,
    metrics
  });

  const shutdown = async (): Promise<void> => {
    await app.close();
    await mongoConnection.close();
    process.exit(0);
  };

  process.on("SIGINT", () => {
    void shutdown();
  });

  process.on("SIGTERM", () => {
    void shutdown();
  });

  await app.listen({ port: config.port, host: "0.0.0.0" });
};

void bootstrap();

