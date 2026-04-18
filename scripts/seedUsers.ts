import { readFile } from "node:fs/promises";
import path from "node:path";
import { getConfig } from "../src/config/env";
import { MongoConnection } from "../src/data/mongo";
import { UserPreferenceProfile } from "../src/model/types";

interface SeedUser {
  userId?: string;
  id?: string;
  _id?: string | { $oid?: string };
  favoriteGenres: string[];
}

const defaultSeedPath = path.resolve(process.cwd(), "scripts", "data", "users.seed.json");

const normalizeGenres = (genres: string[]): string[] => {
  const cleaned = genres
    .map((genre) => genre.trim())
    .filter((genre) => genre.length > 0);

  return Array.from(new Set(cleaned));
};

const parseSeedUsers = (data: string): SeedUser[] => {
  const parsed = JSON.parse(data) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("El archivo de seed debe contener un arreglo JSON");
  }

  return parsed as SeedUser[];
};

const toProfile = (user: SeedUser, index: number): UserPreferenceProfile => {
  const oidValue = typeof user._id === "string" ? user._id : user._id?.$oid;
  const userId = user.userId ?? user.id ?? oidValue;
  if (!userId || userId.trim().length === 0) {
    throw new Error(`Registro invalido en posicion ${index}: falta userId o id`);
  }

  if (!Array.isArray(user.favoriteGenres)) {
    throw new Error(`Registro invalido para ${userId}: favoriteGenres debe ser un arreglo`);
  }

  return {
    userId: userId.trim(),
    favoriteGenres: normalizeGenres(user.favoriteGenres)
  };
};

const seedUsers = async (): Promise<void> => {
  const config = getConfig();
  const seedFilePath = process.env.SEED_USERS_FILE
    ? path.resolve(process.cwd(), process.env.SEED_USERS_FILE)
    : defaultSeedPath;
  const seedData = await readFile(seedFilePath, "utf-8");
  const seedUsersData = parseSeedUsers(seedData);

  const mongo = new MongoConnection(config.mongoUri, config.mongoDbName);
  const db = await mongo.connect();

  try {
    const collection = db.collection<UserPreferenceProfile>("user_preference_profiles");

    let upserted = 0;
    let updated = 0;

    for (const [index, user] of seedUsersData.entries()) {
      const profile = toProfile(user, index);
      const result = await collection.updateOne(
        { userId: profile.userId },
        { $set: profile },
        { upsert: true }
      );

      if (result.upsertedCount > 0) {
        upserted += 1;
      } else if (result.modifiedCount > 0) {
        updated += 1;
      }
    }

    const totalProfiles = await collection.countDocuments();
    console.log(
      `Seed completado. Archivo=${seedFilePath}, Procesados=${seedUsersData.length}, Nuevos=${upserted}, Actualizados=${updated}, TotalEnColeccion=${totalProfiles}`
    );
  } finally {
    await mongo.close();
  }
};

void seedUsers();



