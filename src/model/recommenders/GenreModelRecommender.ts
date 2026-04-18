import {
  GenreRelationsRepository,
  ItemMetadataRepository,
  UserPreferenceRepository
} from "../../data/repositories/interfaces";
import { calculateItemScore } from "../scoring";
import { Recommendation } from "../types";
import { GenreSimilarityModel } from "../GenreSimilarityModel";
import { RecommenderStrategy } from "./RecommenderStrategy";

export class GenreModelRecommender implements RecommenderStrategy {
  constructor(
    private readonly userRepository: UserPreferenceRepository,
    private readonly itemRepository: ItemMetadataRepository,
    private readonly relationsRepository: GenreRelationsRepository,
    private readonly model: GenreSimilarityModel
  ) {}

  async recommend(userId: string, limit: number): Promise<Recommendation[]> {
    const profile = await this.userRepository.findByUserId(userId);
    const favoriteGenres = profile?.favoriteGenres ?? [];

    if (favoriteGenres.length === 0) {
      return [];
    }

    if (!this.model.isTrained()) {
      const storedRelations = await this.relationsRepository.findAll();
      if (storedRelations.length > 0) {
        this.model.loadRelations(storedRelations);
      }
    }

    const inferredGenres = this.model.getSimilarGenres(favoriteGenres).slice(0, limit);
    const inferredGenreNames = inferredGenres.map((genre) => genre.genre);

    const items = await this.itemRepository.findAll();

    const itemRecommendations = items
      .map((item) => {
        const breakdown = calculateItemScore(item, favoriteGenres, inferredGenreNames);
        const directGenres = item.genres.filter((genre) => favoriteGenres.includes(genre));
        const inferredMatches = item.genres.filter((genre) => inferredGenreNames.includes(genre));

        const reason =
          directGenres.length > 0
            ? `Recomendado porque te gusta ${directGenres[0]} y se relaciona con ${inferredMatches[0] ?? directGenres[0]}`
            : `Recomendado por afinidad con genero inferido ${inferredMatches[0] ?? "similar"}`;

        return {
          itemId: item.itemId,
          score: Number(breakdown.score.toFixed(4)),
          type: item.type,
          reason
        } as Recommendation;
      })
      .filter((recommendation) => recommendation.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);

    const genreRecommendations = inferredGenres.slice(0, limit).map((relation) => ({
      itemId: relation.genre,
      score: Number(relation.score.toFixed(4)),
      type: "genre" as const,
      reason: `Genero inferido a partir de tus gustos en ${favoriteGenres.join(", ")}`
    }));

    return [...itemRecommendations, ...genreRecommendations].slice(0, limit * 2);
  }
}

