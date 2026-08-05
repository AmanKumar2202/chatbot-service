from dataclasses import dataclass
import time

from app.core.metrics import CLASSIFIER_LATENCY
from app.ml.model_loader import load_model
from app.ml.preprocess import preprocess


@dataclass(frozen=True)
class Prediction:
    intent: str
    confidence: float


def predict_intent(message: str) -> Prediction:
    started = time.perf_counter()
    try:
        model, vectorizer = load_model()
        features = vectorizer.transform([preprocess(message)])
        probabilities = model.predict_proba(features)[0]
        best_index = int(probabilities.argmax())
        return Prediction(
            intent=str(model.classes_[best_index]),
            confidence=float(probabilities[best_index]),
        )
    finally:
        CLASSIFIER_LATENCY.observe(time.perf_counter() - started)
