import hashlib
import json
import threading
from pathlib import Path

import joblib
import sklearn


BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE_DIR / "saved_models" / "model.pkl"
VECTORIZER_PATH = BASE_DIR / "saved_models" / "vectorizer.pkl"
METADATA_PATH = BASE_DIR / "saved_models" / "metadata.json"
DATA_PATH = BASE_DIR / "ml_training" / "training_data.json"

model = None
vectorizer = None
metadata = None
_load_lock = threading.RLock()


class ModelArtifactError(RuntimeError):
    """Raised when trained model artifacts are missing, stale, or unreadable."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_metadata(payload: dict) -> None:
    required = {
        "artifact_version",
        "sklearn_version",
        "classes",
        "dataset_sha256",
        "model_sha256",
        "vectorizer_sha256",
    }
    missing = required.difference(payload)
    if missing:
        raise ModelArtifactError(f"Model metadata is missing fields: {sorted(missing)}")
    if payload["artifact_version"] != 1:
        raise ModelArtifactError("Unsupported model artifact metadata version")
    if payload["sklearn_version"] != sklearn.__version__:
        raise ModelArtifactError(
            "Model was trained with a different scikit-learn version; retrain it"
        )
    checks = {
        MODEL_PATH: payload["model_sha256"],
        VECTORIZER_PATH: payload["vectorizer_sha256"],
        DATA_PATH: payload["dataset_sha256"],
    }
    for path, expected in checks.items():
        if not path.exists() or _sha256(path) != expected:
            raise ModelArtifactError(f"Stale or corrupt model input/artifact: {path.name}")


def load_model():
    global model, vectorizer, metadata
    if model is not None and vectorizer is not None:
        return model, vectorizer
    with _load_lock:
        if model is not None and vectorizer is not None:
            return model, vectorizer
        try:
            payload = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            _validate_metadata(payload)
            loaded_model = joblib.load(MODEL_PATH)
            loaded_vectorizer = joblib.load(VECTORIZER_PATH)
            if sorted(map(str, loaded_model.classes_)) != payload["classes"]:
                raise ModelArtifactError("Model classes do not match artifact metadata")
        except ModelArtifactError:
            raise
        except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise ModelArtifactError(
                "Model artifacts are missing or incompatible; run "
                "`python -m ml_training.train_model`."
            ) from exc
        except Exception as exc:
            raise ModelArtifactError("Model artifacts could not be loaded safely") from exc
        model = loaded_model
        vectorizer = loaded_vectorizer
        metadata = payload
        return model, vectorizer


def model_is_loaded() -> bool:
    return model is not None and vectorizer is not None


def model_metadata() -> dict | None:
    return dict(metadata) if metadata else None
