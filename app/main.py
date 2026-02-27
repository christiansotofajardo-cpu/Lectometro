from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import io
import os

import numpy as np
import soundfile as sf

app = FastAPI(
    title="Lectometro API",
    description="API base para evaluación de fluidez y decodificación",
    version="1.1.0",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def _load_text_words(forma: str) -> list[str]:
    forma = forma.upper().strip()
    if forma not in {"2A", "2B"}:
        raise ValueError("forma debe ser 2A o 2B")

    fname = "fluidez_2A.txt" if forma == "2A" else "fluidez_2B.txt"
    path = os.path.join(DATA_DIR, fname)

    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}. Sube el archivo a app/data/{fname}")

    with open(path, "r", encoding="utf-8") as f:
        txt = f.read().strip()

    # tokenización simple por espacios (suficiente para WPM base)
    words = [w for w in txt.replace("\n", " ").split(" ") if w.strip()]
    return words

def _classify_wpm(wpm: float) -> str:
    # Clasificación provisoria (ajustaremos por 1°/2° básico y con datos reales)
    if wpm >= 85:
        return "BUENO"
    if wpm >= 55:
        return "REGULAR"
    return "MALO"

@app.get("/")
def root():
    return {
        "service": "lectometro",
        "status": "running",
        "endpoints": ["/health", "/docs", "/api/evaluar"],
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "lectometro"}

@app.post("/api/evaluar")
async def evaluar(
    tipo: str = Form(...),         # "FL" o "DEC"
    forma: str = Form(...),        # "2A" o "2B"
    id_sujeto: str = Form(""),     # opcional
    audio: UploadFile = File(...),
):
    tipo = (tipo or "").upper().strip()
    forma = (forma or "").upper().strip()

    if tipo not in {"FL", "DEC"}:
        return JSONResponse(status_code=400, content={"error": "tipo debe ser FL o DEC"})
    if forma not in {"2A", "2B"}:
        return JSONResponse(status_code=400, content={"error": "forma debe ser 2A o 2B"})

    filename = (audio.filename or "").lower()
    if not filename.endswith(".wav"):
        return JSONResponse(status_code=400, content={"error": "Formato no permitido. Solo .wav"})

    raw = await audio.read()
    size_bytes = len(raw)

    # --- Leer WAV ---
    try:
        data, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
        if hasattr(data, "ndim") and data.ndim > 1:
            data = data.mean(axis=1)  # mono
        duration_sec = float(len(data) / sr) if sr else 0.0
        rms = float(np.sqrt(np.mean(np.square(data)))) if len(data) else 0.0
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "No pude leer el WAV. ¿Está corrupto o no es WAV PCM?",
                "detail": str(e),
            },
        )

    # --- Flags simples ---
    flag_audio_muy_corto = duration_sec < 2.0
    flag_audio_silencioso = rms < 0.005

    base = {
        "id_sujeto": id_sujeto,
        "tipo": tipo,
        "forma": forma,
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
    }

    # --- FL: WPM base por texto canónico ---
    if tipo == "FL":
        try:
            words = _load_text_words(forma)
            n_words = len(words)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

        if duration_sec <= 0.1:
            wpm = 0.0
        else:
            wpm = (n_words / duration_sec) * 60.0

        base["fluidez"] = {
            "n_palabras_texto": n_words,
            "wpm_texto": round(wpm, 2),
            "categoria_provisoria": _classify_wpm(wpm),
            "nota": "WPM base (sin ASR). Luego será WCPM con alineación y exactitud.",
        }
        return base

    # --- DEC: por ahora solo calidad de audio (luego ASR + lista 16 palabras) ---
    base["decodificacion"] = {
        "nota": "Por ahora solo calidad/duración. Luego: ASR + comparación con lista (16) + exactitud.",
    }
    return base
