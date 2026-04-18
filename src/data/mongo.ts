import { Db, MongoClient } from "mongodb";

export class MongoConnection {
  private client: MongoClient;

  constructor(private readonly uri: string, private readonly dbName: string) {
    this.client = new MongoClient(this.uri);
  }

  async connect(): Promise<Db> {
    await this.client.connect();
    return this.client.db(this.dbName);
  }

  async close(): Promise<void> {
    await this.client.close();
  }
}

