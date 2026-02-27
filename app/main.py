from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import io

import numpy as np
import soundfile as sf

app = FastAPI(
    title="Lectometro API",
    description="API base para evaluación de fluidez y decodificación",
    version="1.0.0",
)

# -------------------------
# ROOT
# -------------------------
@app.get("/")
def root():
    return {
        "service": "lectometro",
        "status": "running",
        "endpoints": ["/health", "/docs", "/api/evaluar"],
    }

# -------------------------
# HEALTH CHECK
# -------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "lectometro"}

# -------------------------
# EVALUACIÓN (audio real: duración + RMS + flags)
# -------------------------
@app.post("/api/evaluar")
async def evaluar_audio(audio: UploadFile = File(...)):
    """
    Recibe un archivo WAV, lo lee en memoria y devuelve:
    - sample rate
    - duración en segundos
    - tamaño del archivo
    - RMS (energía)
    - flags de calidad (muy corto / silencioso)

    Luego aquí enchufamos ASR + alineación + WCPM + exactitud.
    """

    filename = (audio.filename or "").lower()
    if not filename.endswith(".wav"):
        return JSONResponse(
            status_code=400,
            content={"error": "Formato no permitido. Solo .wav"},
        )

    raw = await audio.read()
    size_bytes = len(raw)

    try:
        # Leer wav desde memoria
        data, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)

        # Si viene estéreo o multicanal, lo pasamos a mono
        if hasattr(data, "ndim") and data.ndim > 1:
            data = data.mean(axis=1)

        # Duración
        duration_sec = float(len(data) / sr) if sr else 0.0

        # RMS (energía)
        rms = float(np.sqrt(np.mean(np.square(data)))) if len(data) else 0.0

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "No pude leer el WAV. ¿Está corrupto o no es WAV PCM?",
                "detail": str(e),
            },
        )

    # Flags simples de calidad (ajustables después con datos reales)
    flag_audio_muy_corto = duration_sec < 2.0
    flag_audio_silencioso = rms < 0.005  # umbral inicial

    return {
        "mensaje": "Audio recibido y leído",
        "archivo": audio.filename,
        "audio_info": {
            "sample_rate": sr,
            "duration_sec": round(duration_sec, 3),
            "size_kb": round(size_bytes / 1024, 1),
            "rms": round(rms, 6),
            "flags": {
                "audio_muy_corto": flag_audio_muy_corto,
                "audio_silencioso": flag_audio_silencioso,
            },
        },
        "next": "Luego enchufamos ASR + alineación + WCPM + exactitud.",
    }
