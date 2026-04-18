import {
  ItemMetadataRepository,
  UserPreferenceRepository
} from "../../data/repositories/interfaces";
import { Recommendation } from "../types";
import { RecommenderStrategy } from "./RecommenderStrategy";

export class RuleBasedRecommender implements RecommenderStrategy {
  constructor(
    private readonly userRepository: UserPreferenceRepository,
    private readonly itemRepository: ItemMetadataRepository
  ) {}

  async recommend(userId: string, limit: number): Promise<Recommendation[]> {
    const profile = await this.userRepository.findByUserId(userId);
    const items = await this.itemRepository.findAll();
    const favoriteGenres = new Set(profile?.favoriteGenres ?? []);

    const itemRecommendations = items
      .map((item) => {
        const matchCount = item.genres.filter((genre) => favoriteGenres.has(genre)).length;
        const directScore = favoriteGenres.size > 0 ? matchCount / favoriteGenres.size : 0;
        const score = 0.8 * directScore + 0.2 * Math.max(0, Math.min(1, item.popularityScore));

        return {
          itemId: item.itemId,
          score,
          type: item.type,
          reason:
            matchCount > 0
              ? `Recomendado por coincidencia directa con ${item.genres.filter((g) => favoriteGenres.has(g)).join(", ")}`
              : "Recomendado por popularidad mientras entrenamos el modelo"
        } as Recommendation;
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);

    const genreRecommendations = this.recommendGenres(items, favoriteGenres, limit);

    return [...itemRecommendations, ...genreRecommendations].slice(0, limit * 2);
  }

  private recommendGenres(
    items: Awaited<ReturnType<ItemMetadataRepository["findAll"]>>,
    favorites: Set<string>,
    limit: number
  ): Recommendation[] {
    const counts = new Map<string, number>();

    for (const item of items) {
      for (const genre of item.genres) {
        if (favorites.has(genre)) {
          continue;
        }
        counts.set(genre, (counts.get(genre) ?? 0) + 1);
      }
    }

    const maxCount = Math.max(1, ...counts.values());

    return [...counts.entries()]
      .map(([genre, count]) => ({
        itemId: genre,
        score: count / maxCount,
        type: "genre" as const,
        reason: "Genero sugerido por presencia en el catalogo"
      }))
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }
}

