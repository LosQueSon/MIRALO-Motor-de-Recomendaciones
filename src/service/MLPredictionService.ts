import { spawn } from "child_process";
import path from "path";
import { promisify } from "util";
import { exec as execCallback } from "child_process";
import * as fs from "fs";

const exec = promisify(execCallback);

export interface MLPredictionRequest {
  favoriteGenres: string[];
  topK?: number;
  threshold?: number;
}

export interface MLPrediction {
  movieId: number;
  title: string;
  genres: string[];
  predicted_probability: number;
  liked: boolean;
  reason: string;
}

export interface MLPredictionResponse {
  success: boolean;
  data?: MLPrediction[];
  error?: string;
}

/**
 * Servicio de predicción ML
 * Ejecuta el modelo de Python desde Node.js
 */
export class MLPredictionService {
  private pythonScriptPath: string;
  private modelsDir: string;
  private extractJSON(output: string): any {
      // Buscar la última línea que empiece con { o [ (el JSON real siempre está al final)
        const lines = output.split(/\r?\n/).map(l => l.trim());
        const jsonLine = [...lines].reverse().find(l => l.startsWith('{') || l.startsWith('['));

        if (!jsonLine) {
            throw new Error(`No JSON found in Python output: ${output.substring(0, 200)}`);
        }

        return JSON.parse(jsonLine);
  }

  constructor() {
    // Usar process.cwd() para resolver rutas relativas al root del proyecto en tiempo de ejecución.
    // Esto evita que la ruta apunte a 'dist/' después de compilar TypeScript.
    const projectRoot = process.cwd();
    this.pythonScriptPath = path.join(projectRoot, "ml", "training", "ml_model_predictor.py");
    this.modelsDir = path.join(projectRoot, "ml_models");
  }

  /**
   * Verifica si el modelo está entrenado
   */
  async isModelTrained(): Promise<boolean> {
    try {
      const modelPath = path.join(this.modelsDir, "xgb_recommender_model.joblib");
      const mlbPath = path.join(this.modelsDir, "mlb_genres.joblib");

      return fs.existsSync(modelPath) && fs.existsSync(mlbPath);
    } catch {
      return false;
    }
  }

  /**
   * Obtiene el reporte de entrenamiento
   */
  async getTrainingReport(): Promise<any> {
    try {
      const reportPath = path.join(this.modelsDir, "training_report.json");
      const content = fs.readFileSync(reportPath, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      throw new Error("Training report not found. Run python ml_model_training.py first");
    }
  }

  /**
   * Predice películas para un usuario basado en sus géneros
   */
  async predictForUser(
    request: MLPredictionRequest
  ): Promise<MLPredictionResponse> {
    try {
      const isTrained = await this.isModelTrained();
      if (!isTrained) {
        return {
          success: false,
          error: "Model not trained yet. Run ml_model_training.py first"
        };
      }

      const topK = request.topK || 10;
      const threshold = request.threshold || 0.5;
      const genres = JSON.stringify(request.favoriteGenres);

      // Ejecutar predictor de Python
      const predictions = await this.executePythonPredictor(genres, topK, threshold);

      return {
        success: true,
        data: predictions
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error"
      };
    }
  }

  /**
   * Predice para un grupo de usuarios (sala)
   */
  async predictForRoom(
    users: Array<{ userId: string; favoriteGenres: string[] }>,
    topK?: number
  ): Promise<any> {
    try {
      const isTrained = await this.isModelTrained();
      if (!isTrained) {
        return {
          success: false,
          error: "Model not trained yet. Run ml_model_training.py first"
        };
      }

      const usersJson = JSON.stringify(users);
      const k = topK || 10;

      // Ejecutar predictor de Python para sala
      const predictions = await this.executePythonRoomPredictor(usersJson, k);

      return {
        success: true,
        data: predictions
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error"
      };
    }
  }

  /**
   * Ejecuta el script de predicción de Python
   */
  private async executePythonPredictor(
    genres: string,
    topK: number,
    threshold: number
  ): Promise<MLPrediction[]> {
    return new Promise((resolve, reject) => {
      // Escapar rutas para Python usando raw strings
      const scriptDir = path.dirname(this.pythonScriptPath).replace(/\\/g, "\\\\");

      const pythonScript = `
import sys
import json

# Agregar directorio al path
sys.path.insert(0, r'${scriptDir}')

try:
    # Importar el predictor
    from ml_model_predictor import MiraloMLPredictor
    
    # Crear predictor y cargar modelos
    predictor = MiraloMLPredictor()
    predictor.load_movies()
    
    # Parsear géneros
    genres = json.loads(${JSON.stringify(genres)})
    
    # Hacer predicción
    predictions = predictor.predict_for_user(
        favorite_genres=genres,
        top_k=${topK},
        threshold=${threshold}
    )
    
    # Retornar resultado
    print(json.dumps(predictions, default=str))
    
except ImportError as e:
    print(json.dumps({"error": f"Import error: {str(e)}"}))
except Exception as e:
    print(json.dumps({"error": f"{type(e).__name__}: {str(e)}"}))
`;

      const pythonProcess = spawn("python", ["-c", pythonScript], {
        cwd: path.dirname(this.pythonScriptPath)
      });

      let output = "";
      let errorOutput = "";

      pythonProcess.stdout?.on("data", (data) => {
        output += data.toString();
      });

      pythonProcess.stderr?.on("data", (data) => {
        errorOutput += data.toString();
      });

      pythonProcess.on("close", (code) => {
        const trimmedOutput = output.trim();
        const trimmedError = errorOutput.trim();

        // Log para debugging
        console.log("[Python Output]:", trimmedOutput);
        if (trimmedError) {
          console.log("[Python Error]:", trimmedError);
        }

        if (code !== 0 || !trimmedOutput) {
          const err = trimmedError || `Process exited with code ${code}`;
          reject(new Error(`Python execution failed: ${err}`));
        } else {
          try {
              const predictions = this.extractJSON(trimmedOutput);
            if (predictions.error) {
              reject(new Error(`Python error: ${predictions.error}`));
            } else if (Array.isArray(predictions)) {
              resolve(predictions);
            } else {
              reject(new Error("Invalid response format from Python"));
            }
          } catch (parseError) {
            reject(new Error(`Failed to parse Python output: ${trimmedOutput.substring(0, 200)}`));
          }
        }
      });
    });
  }

  /**
   * Ejecuta el script de predicción para sala
   */
  private async executePythonRoomPredictor(
    usersJson: string,
    topK: number
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      // Escapar rutas para Python usando raw strings
      const scriptDir = path.dirname(this.pythonScriptPath).replace(/\\/g, "\\\\");

      const pythonScript = `
import sys
import json
import os

# Agregar directorio al path
sys.path.insert(0, r'${scriptDir}')

try:
    # Importar el predictor
    from ml_model_predictor import MiraloMLPredictor
    
    # Crear predictor y cargar modelos
    predictor = MiraloMLPredictor()
    predictor.load_movies()
    
    # Parsear usuarios
    users = json.loads(${JSON.stringify(usersJson)})
    
    # Hacer predicción
    result = predictor.predict_for_room(
        room_users_data=users,
        top_k=${topK}
    )
    
    # Retornar resultado
    print(json.dumps(result, default=str))
    
except ImportError as e:
    print(json.dumps({"error": f"Import error: {str(e)}"}))
except Exception as e:
    print(json.dumps({"error": f"{type(e).__name__}: {str(e)}"}))
`;

      const pythonProcess = spawn("python", ["-c", pythonScript], {
        cwd: path.dirname(this.pythonScriptPath)
      });

      let output = "";
      let errorOutput = "";

      pythonProcess.stdout?.on("data", (data) => {
        output += data.toString();
      });

      pythonProcess.stderr?.on("data", (data) => {
        errorOutput += data.toString();
      });

      pythonProcess.on("close", (code) => {
        const trimmedOutput = output.trim();
        const trimmedError = errorOutput.trim();

        // Log para debugging
        console.log("[Python Output]:", trimmedOutput);
        if (trimmedError) {
          console.log("[Python Error]:", trimmedError);
        }

        if (code !== 0 || !trimmedOutput) {
          const err = trimmedError || `Process exited with code ${code}`;
          reject(new Error(`Python execution failed: ${err}`));
        } else {
          try {
              const result = this.extractJSON(trimmedOutput);
            if (result.error) {
              reject(new Error(`Python error: ${result.error}`));
            } else {
              resolve(result);
            }
          } catch (parseError) {
            reject(new Error(`Failed to parse Python output: ${trimmedOutput.substring(0, 200)}`));
          }
        }
      });
    });
  }
}





