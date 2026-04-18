import { getConfig } from "../src/config/env";
import { MongoConnection } from "../src/data/mongo";
import { UserPreferenceProfile } from "../src/model/types";

const checkDb = async (): Promise<void> => {
  const config = getConfig();
  const mongo = new MongoConnection(config.mongoUri, config.mongoDbName);
  const db = await mongo.connect();

  try {
    await db.command({ ping: 1 });

    const users = await db
      .collection<UserPreferenceProfile>("user_preference_profiles")
      .find({}, { projection: { _id: 0 } })
      .toArray();
    const itemsCount = await db.collection("item_metadata").countDocuments();
    const relationsCount = await db.collection("genre_relations").countDocuments();

    console.log("Conexion Mongo OK");
    console.log(`Base de datos: ${config.mongoDbName}`);
    console.log(`Usuarios en user_preference_profiles: ${users.length}`);
    console.log(`Items en item_metadata: ${itemsCount}`);
    console.log(`Relaciones en genre_relations: ${relationsCount}`);

    for (const user of users) {
      console.log(`- ${user.userId}: [${user.favoriteGenres.join(", ")}]`);
    }
  } finally {
    await mongo.close();
  }
};

void checkDb();


