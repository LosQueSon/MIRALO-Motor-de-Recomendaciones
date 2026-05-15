import "dotenv/config";

export interface AppConfig {
  port: number;
  nodeEnv: string;
}

export const getConfig = (): AppConfig => {
  const port = Number(process.env.PORT ?? 3000);
  const nodeEnv = process.env.NODE_ENV ?? "development";

  if (!Number.isFinite(port) || port <= 0) {
    throw new Error("PORT must be a positive number");
  }

  return { port, nodeEnv };
};

