export type ItemType = "movie" | "series";
export type RecommendationType = ItemType | "genre";

export interface UserPreferenceProfile {
  userId: string;
  favoriteGenres: string[];
}

export interface ItemMetadata {
  itemId: string;
  type: ItemType;
  genres: string[];
  popularityScore: number;
}

export interface GenreRelation {
  genre: string;
  score: number;
}

export interface GenreRelationsDocument {
  genre: string;
  relatedGenres: GenreRelation[];
}

export interface Recommendation {
  itemId: string;
  score: number;
  type: RecommendationType;
  reason: string;
}

export interface RecommendationSnapshot {
  userId: string;
  recommendations: Recommendation[];
  createdAt: Date;
}

