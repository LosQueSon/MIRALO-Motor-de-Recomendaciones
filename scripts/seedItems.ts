import { readFile } from "node:fs/promises";
import path from "node:path";
import { getConfig } from "../src/config/env";
import { MongoConnection } from "../src/data/mongo";
import { ItemMetadata } from "../src/model/types";

interface SeedItem {
  itemId: string;
  type: "movie" | "series";
  genres: string[];
  popularityScore: number;
}

const defaultSeedPath = path.resolve(process.cwd(), "scripts", "data", "items.seed.json");

const normalizeGenres = (genres: string[]): string[] => {
  const cleaned = genres
    .map((genre) => genre.trim())
    .filter((genre) => genre.length > 0);

  return Array.from(new Set(cleaned));
};

const parseSeedItems = (data: string): SeedItem[] => {
  const parsed = JSON.parse(data) as unknown;
  if (!Array.isArray(parsed)) {
    throw new Error("El archivo de seed de items debe contener un arreglo JSON");
  }

  return parsed as SeedItem[];
};

const toItem = (item: SeedItem, index: number): ItemMetadata => {
  if (!item.itemId || item.itemId.trim().length === 0) {
    throw new Error(`Item invalido en posicion ${index}: falta itemId`);
  }

  if (item.type !== "movie" && item.type !== "series") {
    throw new Error(`Item invalido ${item.itemId}: type debe ser movie o series`);
  }

  if (!Array.isArray(item.genres)) {
    throw new Error(`Item invalido ${item.itemId}: genres debe ser un arreglo`);
  }

  if (!Number.isFinite(item.popularityScore)) {
    throw new Error(`Item invalido ${item.itemId}: popularityScore debe ser numerico`);
  }

  return {
    itemId: item.itemId.trim(),
    type: item.type,
    genres: normalizeGenres(item.genres),
    popularityScore: Math.max(0, Math.min(1, item.popularityScore))
  };
};

const seedItems = async (): Promise<void> => {
  const config = getConfig();
  const seedFilePath = process.env.SEED_ITEMS_FILE
    ? path.resolve(process.cwd(), process.env.SEED_ITEMS_FILE)
    : defaultSeedPath;

  const seedData = await readFile(seedFilePath, "utf-8");
  const seedItemsData = parseSeedItems(seedData);

  const mongo = new MongoConnection(config.mongoUri, config.mongoDbName);
  const db = await mongo.connect();

  try {
    const collection = db.collection<ItemMetadata>("item_metadata");

    let upserted = 0;
    let updated = 0;

    for (const [index, seedItem] of seedItemsData.entries()) {
      const item = toItem(seedItem, index);

      const result = await collection.updateOne(
        { itemId: item.itemId },
        { $set: item },
        { upsert: true }
      );

      if (result.upsertedCount > 0) {
        upserted += 1;
      } else if (result.modifiedCount > 0) {
        updated += 1;
      }
    }

    const totalItems = await collection.countDocuments();
    console.log(
      `Seed items completado. Archivo=${seedFilePath}, Procesados=${seedItemsData.length}, Nuevos=${upserted}, Actualizados=${updated}, TotalEnColeccion=${totalItems}`
    );
  } finally {
    await mongo.close();
  }
};

void seedItems();

