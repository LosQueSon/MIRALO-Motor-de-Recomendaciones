import {
  RecommendationSnapshotRepository,
  UserPreferenceRepository
} from "../data/repositories/interfaces";
import { MetricsRegistry } from "../metrics/MetricsRegistry";
import { Recommendation } from "../model/types";
import { RecommenderStrategy } from "../model/recommenders/RecommenderStrategy";

export class RecommendationService {
  constructor(
    private readonly userRepository: UserPreferenceRepository,
    private readonly primaryStrategy: RecommenderStrategy,
    private readonly fallbackStrategy: RecommenderStrategy,
    private readonly snapshotRepository: RecommendationSnapshotRepository,
    private readonly metrics: MetricsRegistry
  ) {}

  async recommend(userId: string, limit = 10): Promise<Recommendation[]> {
    const profile = await this.userRepository.findByUserId(userId);
    const shouldUseFallback = !profile || profile.favoriteGenres.length === 0;

    const strategy = shouldUseFallback ? this.fallbackStrategy : this.primaryStrategy;

    const recommendations = await strategy.recommend(userId, limit);
    await this.snapshotRepository.save(userId, recommendations);

    this.metrics.trackRecommendations(recommendations.map((recommendation) => recommendation.score));

    return recommendations;
  }
}

