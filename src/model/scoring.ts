import { ItemMetadata } from "./types";

export interface ScoreWeights {
  w1: number;
  w2: number;
  w3: number;
}

export const DEFAULT_WEIGHTS: ScoreWeights = {
  w1: 0.55,
  w2: 0.3,
  w3: 0.15
};

export interface ItemScoreBreakdown {
  score: number;
  directMatch: number;
  inferredMatch: number;
  popularity: number;
}

export function calculateItemScore(
  item: ItemMetadata,
  favoriteGenres: string[],
  inferredGenres: string[],
  weights: ScoreWeights = DEFAULT_WEIGHTS
): ItemScoreBreakdown {
  const favoriteSet = new Set(favoriteGenres);
  const inferredSet = new Set(inferredGenres);

  const directMatches = item.genres.filter((genre) => favoriteSet.has(genre)).length;
  const inferredMatches = item.genres.filter((genre) => inferredSet.has(genre)).length;

  const directMatch = favoriteSet.size > 0 ? directMatches / favoriteSet.size : 0;
  const inferredMatch = inferredSet.size > 0 ? inferredMatches / inferredSet.size : 0;
  const popularity = Math.max(0, Math.min(1, item.popularityScore));

  const score =
    weights.w1 * directMatch +
    weights.w2 * inferredMatch +
    weights.w3 * popularity;

  return {
    score,
    directMatch,
    inferredMatch,
    popularity
  };
}

