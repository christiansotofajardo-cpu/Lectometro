from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="Lectometro API",
    description="API base para evaluación de fluidez y decodificación",
    version="1.0.0"
)

# -------------------------
# ROOT
# -------------------------

@app.get("/")
def root():
    return {
        "service": "lectometro",
        "status": "running",
        "endpoints": [
            "/health",
            "/docs",
            "/api/evaluar"
        ]
    }

# -------------------------
# HEALTH CHECK
# -------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "lectometro"
    }

# -------------------------
# EVALUACIÓN (placeholder)
# -------------------------

@app.post("/api/evaluar")
async def evaluar_audio(audio: UploadFile = File(...)):
    """
    Endpoint base para recibir audio.
    Por ahora devuelve respuesta simulada.
    """

    if not audio.filename.endswith(".wav"):
        return JSONResponse(
            status_code=400,
            content={"error": "Formato no permitido. Solo .wav"}
        )

    # Aquí luego irá:
    # - Guardado temporal
    # - Transcripción
    # - Cálculo velocidad
    # - Cálculo precisión
    # - Comparación norma

    return {
        "mensaje": "Audio recibido correctamente",
        "archivo": audio.filename,
        "evaluacion": {
            "velocidad_palabras_minuto": 78,
            "precision": 0.92,
            "nivel": "Adecuado"
        }
    }

# -------------------------
# RUN LOCAL (no afecta Docker)
# -------------------------

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
