import { Collection, Db } from "mongodb";
import {
  GenreRelationsDocument,
  ItemMetadata,
  Recommendation,
  RecommendationSnapshot,
  UserPreferenceProfile
} from "../../model/types";
import {
  GenreRelationsRepository,
  ItemMetadataRepository,
  RecommendationSnapshotRepository,
  UserPreferenceRepository
} from "./interfaces";

export class MongoUserPreferenceRepository implements UserPreferenceRepository {
  private readonly collection: Collection<UserPreferenceProfile>;

  constructor(db: Db) {
    this.collection = db.collection<UserPreferenceProfile>("user_preference_profiles");
    void this.collection.createIndex({ userId: 1 }, { unique: true });
  }

  findByUserId(userId: string): Promise<UserPreferenceProfile | null> {
    return this.collection.findOne({ userId }, { projection: { _id: 0 } });
  }

  findAll(): Promise<UserPreferenceProfile[]> {
    return this.collection.find({}, { projection: { _id: 0 } }).toArray();
  }
}

export class MongoItemMetadataRepository implements ItemMetadataRepository {
  private readonly collection: Collection<ItemMetadata>;

  constructor(db: Db) {
    this.collection = db.collection<ItemMetadata>("item_metadata");
    void this.collection.createIndex({ itemId: 1 }, { unique: true });
  }

  findAll(): Promise<ItemMetadata[]> {
    return this.collection.find({}, { projection: { _id: 0 } }).toArray();
  }
}

export class MongoGenreRelationsRepository implements GenreRelationsRepository {
  private readonly collection: Collection<GenreRelationsDocument>;

  constructor(db: Db) {
    this.collection = db.collection<GenreRelationsDocument>("genre_relations");
    void this.collection.createIndex({ genre: 1 }, { unique: true });
  }

  findAll(): Promise<GenreRelationsDocument[]> {
    return this.collection.find({}, { projection: { _id: 0 } }).toArray();
  }

  async replaceAll(relations: GenreRelationsDocument[]): Promise<void> {
    await this.collection.deleteMany({});
    if (relations.length > 0) {
      await this.collection.insertMany(relations);
    }
  }
}

export class MongoRecommendationSnapshotRepository implements RecommendationSnapshotRepository {
  private readonly collection: Collection<RecommendationSnapshot>;

  constructor(db: Db) {
    this.collection = db.collection<RecommendationSnapshot>("recommendation_snapshots");
    void this.collection.createIndex({ userId: 1 });
    void this.collection.createIndex({ createdAt: -1 });
  }

  async save(userId: string, recommendations: Recommendation[]): Promise<void> {
    await this.collection.insertOne({
      userId,
      recommendations,
      createdAt: new Date()
    });
  }
}

