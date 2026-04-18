import { Recommendation } from "../types";

export interface RecommenderStrategy {
  recommend(userId: string, limit: number): Promise<Recommendation[]>;
}

