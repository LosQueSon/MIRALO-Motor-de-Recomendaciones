import { GenreRelation, GenreRelationsDocument, UserPreferenceProfile } from "./types";

export class GenreSimilarityModel {
  private relationMap: Map<string, GenreRelation[]> = new Map();
  private trained = false;

  train(users: UserPreferenceProfile[]): void {
    const coOccurrence = new Map<string, Map<string, number>>();

    for (const user of users) {
      const genres = [...new Set(user.favoriteGenres)].filter((genre) => genre.trim().length > 0);
      for (let i = 0; i < genres.length; i += 1) {
        for (let j = i + 1; j < genres.length; j += 1) {
          this.incrementPair(coOccurrence, genres[i], genres[j]);
          this.incrementPair(coOccurrence, genres[j], genres[i]);
        }
      }
    }

    const nextMap = new Map<string, GenreRelation[]>();

    for (const [genre, neighbors] of coOccurrence) {
      const total = [...neighbors.values()].reduce((acc, value) => acc + value, 0);
      const relations: GenreRelation[] = [...neighbors.entries()]
        .map(([relatedGenre, count]) => ({
          genre: relatedGenre,
          score: total > 0 ? count / total : 0
        }))
        .sort((a, b) => b.score - a.score);

      nextMap.set(genre, relations);
    }

    this.relationMap = nextMap;
    this.trained = true;
  }

  loadRelations(relations: GenreRelationsDocument[]): void {
    const nextMap = new Map<string, GenreRelation[]>();
    for (const relation of relations) {
      nextMap.set(relation.genre, [...relation.relatedGenres].sort((a, b) => b.score - a.score));
    }
    this.relationMap = nextMap;
    this.trained = relations.length > 0;
  }

  getSimilarGenres(genres: string[]): GenreRelation[] {
    if (!this.trained) {
      return [];
    }

    const favoriteSet = new Set(genres);
    const scores = new Map<string, number>();

    for (const genre of genres) {
      const related = this.relationMap.get(genre) ?? [];
      for (const relation of related) {
        if (favoriteSet.has(relation.genre)) {
          continue;
        }
        scores.set(relation.genre, (scores.get(relation.genre) ?? 0) + relation.score);
      }
    }

    return [...scores.entries()]
      .map(([genre, score]) => ({ genre, score }))
      .sort((a, b) => b.score - a.score);
  }

  getRelations(): GenreRelationsDocument[] {
    return [...this.relationMap.entries()].map(([genre, relatedGenres]) => ({
      genre,
      relatedGenres
    }));
  }

  isTrained(): boolean {
    return this.trained;
  }

  private incrementPair(
    matrix: Map<string, Map<string, number>>,
    source: string,
    target: string
  ): void {
    if (!matrix.has(source)) {
      matrix.set(source, new Map());
    }

    const row = matrix.get(source)!;
    row.set(target, (row.get(target) ?? 0) + 1);
  }
}

