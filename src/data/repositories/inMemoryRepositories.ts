import {
  GenreRelationsDocument,
  ItemMetadata,
  Recommendation,
  UserPreferenceProfile
} from "../../model/types";
import {
  GenreRelationsRepository,
  ItemMetadataRepository,
  RecommendationSnapshotRepository,
  UserPreferenceRepository
} from "./interfaces";

export class InMemoryUserPreferenceRepository implements UserPreferenceRepository {
  constructor(private readonly profiles: UserPreferenceProfile[]) {}

  async findByUserId(userId: string): Promise<UserPreferenceProfile | null> {
    return this.profiles.find((profile) => profile.userId === userId) ?? null;
  }

  async findAll(): Promise<UserPreferenceProfile[]> {
    return [...this.profiles];
  }
}

export class InMemoryItemMetadataRepository implements ItemMetadataRepository {
  constructor(private readonly items: ItemMetadata[]) {}

  async findAll(): Promise<ItemMetadata[]> {
    return [...this.items];
  }
}

export class InMemoryGenreRelationsRepository implements GenreRelationsRepository {
  constructor(private relations: GenreRelationsDocument[] = []) {}

  async findAll(): Promise<GenreRelationsDocument[]> {
    return [...this.relations];
  }

  async replaceAll(relations: GenreRelationsDocument[]): Promise<void> {
    this.relations = [...relations];
  }
}

export class InMemoryRecommendationSnapshotRepository implements RecommendationSnapshotRepository {
  public readonly snapshots: Array<{ userId: string; recommendations: Recommendation[] }> = [];

  async save(userId: string, recommendations: Recommendation[]): Promise<void> {
    this.snapshots.push({ userId, recommendations });
  }
}

