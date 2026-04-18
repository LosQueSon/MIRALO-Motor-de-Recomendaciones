import {
  GenreRelationsDocument,
  ItemMetadata,
  Recommendation,
  UserPreferenceProfile
} from "../../model/types";

export interface UserPreferenceRepository {
  findByUserId(userId: string): Promise<UserPreferenceProfile | null>;
  findAll(): Promise<UserPreferenceProfile[]>;
}

export interface ItemMetadataRepository {
  findAll(): Promise<ItemMetadata[]>;
}

export interface GenreRelationsRepository {
  findAll(): Promise<GenreRelationsDocument[]>;
  replaceAll(relations: GenreRelationsDocument[]): Promise<void>;
}

export interface RecommendationSnapshotRepository {
  save(userId: string, recommendations: Recommendation[]): Promise<void>;
}

