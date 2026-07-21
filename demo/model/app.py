"""
FastAPI inference server for the trained iris classifier.

Endpoints:
    GET  /health          Liveness + readiness probe
    GET  /info            Model metadata (features, classes, training metrics)
    POST /predict         Single prediction
    POST /predict/batch   Batch predictions (up to 1 000 items)
"""
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "artifacts"))

# Loaded once at startup, shared across all requests
_model: Any = None
_metadata: dict[str, Any] = {}


# ── Startup / shutdown ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _model, _metadata

    model_path = ARTIFACTS_DIR / "model.joblib"
    meta_path = ARTIFACTS_DIR / "metadata.json"

    if not model_path.exists():
        raise RuntimeError(
            f"Model not found at '{model_path}'. "
            "Run 'python train.py' or 'make docker-train' first."
        )

    _model = joblib.load(model_path)
    _metadata = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    print(f"✓ Model loaded from {model_path}")

    yield  # server runs here

    _model = None


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Iris Classifier API",
    description="Predict iris species from sepal/petal measurements.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class Features(BaseModel):
    sepal_length: float = Field(..., gt=0, examples=[5.1], description="cm")
    sepal_width: float  = Field(..., gt=0, examples=[3.5], description="cm")
    petal_length: float = Field(..., gt=0, examples=[1.4], description="cm")
    petal_width: float  = Field(..., gt=0, examples=[0.2], description="cm")

    def to_array(self) -> list[float]:
        return [self.sepal_length, self.sepal_width, self.petal_length, self.petal_width]


class PredictRequest(BaseModel):
    features: Features


class BatchPredictRequest(BaseModel):
    items: list[Features] = Field(..., min_length=1, max_length=1000)


class Prediction(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    probabilities: dict[str, float]


class PredictResponse(BaseModel):
    prediction: Prediction


class BatchPredictResponse(BaseModel):
    predictions: list[Prediction]
    count: int


# ── Helpers ────────────────────────────────────────────────────────────────────

def _run_inference(features: list[float]) -> Prediction:
    X = np.array([features])
    class_id = int(_model.predict(X)[0])
    proba = _model.predict_proba(X)[0]
    class_names: list[str] = _metadata.get("class_names", [str(i) for i in range(len(proba))])

    return Prediction(
        class_id=class_id,
        class_name=class_names[class_id],
        confidence=round(float(proba[class_id]), 6),
        probabilities={name: round(float(p), 6) for name, p in zip(class_names, proba)},
    )


def _require_model() -> None:
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "model_loaded": _model is not None}


@app.get("/info", tags=["ops"])
def info():
    return {
        "feature_names": _metadata.get("feature_names", []),
        "class_names": _metadata.get("class_names", []),
        "training_params": _metadata.get("params", {}),
        "training_metrics": _metadata.get("metrics", {}),
    }


@app.post("/predict", response_model=PredictResponse, tags=["inference"])
def predict(req: PredictRequest):
    _require_model()
    return PredictResponse(prediction=_run_inference(req.features.to_array()))


@app.post("/predict/batch", response_model=BatchPredictResponse, tags=["inference"])
def predict_batch(req: BatchPredictRequest):
    _require_model()
    predictions = [_run_inference(item.to_array()) for item in req.items]
    return BatchPredictResponse(predictions=predictions, count=len(predictions))
