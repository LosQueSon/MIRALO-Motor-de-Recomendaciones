import "dotenv/config";

export interface AppConfig {
  port: number;
  mongoUri: string;
  mongoDbName: string;
}

export const getConfig = (): AppConfig => {
  const port = Number(process.env.PORT ?? 3000);
  const mongoUri = process.env.MONGO_URI ?? "mongodb://localhost:27017";
  const mongoDbName = process.env.MONGO_DB_NAME ?? "recommendation_engine";

  if (!Number.isFinite(port) || port <= 0) {
    throw new Error("PORT must be a positive number");
  }

  if (!mongoUri.trim() || !mongoDbName.trim()) {
    throw new Error("MONGO_URI and MONGO_DB_NAME are required");
  }

  return { port, mongoUri, mongoDbName };
};

