import { createServer } from "./api/createServer";
import { getConfig } from "./config/env";

const bootstrap = async (): Promise<void> => {
  const config = getConfig();

  const app = createServer();

  const port = config.port || 3000;

  try {
    await app.listen({ port, host: "0.0.0.0" });
    console.log(`✅ MIRALO ML Server escuchando en puerto ${port}`);
    console.log(`📊 GET  /ml/health`);
    console.log(`🎬 POST /ml/predict`);
    console.log(`👥 POST /ml/predict-room`);
    console.log(`📈 GET  /ml/report`);
  } catch (err) {
    console.error("Error iniciando servidor:", err);
    process.exit(1);
  }
};

void bootstrap();

