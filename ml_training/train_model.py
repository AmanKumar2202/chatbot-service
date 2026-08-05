import json
import hashlib
import os
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

from app.ml.preprocess import preprocess


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "training_data.json"
MODEL_DIR = BASE_DIR.parent / "saved_models"
MODEL_PATH = MODEL_DIR / "model.pkl"
VECTORIZER_PATH = MODEL_DIR / "vectorizer.pkl"
METADATA_PATH = MODEL_DIR / "metadata.json"
MIN_EXAMPLES_PER_INTENT = 50


def load_and_augment_data() -> tuple[list[str], list[str]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
    grouped: dict[str, list[str]] = {}
    for item in data:
        grouped.setdefault(item["label"], []).append(item["text"])

    prefixes = ["please ", "can you ", "could you ", "I need you to ", ""]
    suffixes = ["", " please", " for me", " right now", " thanks"]
    expanded: list[tuple[str, str]] = []
    for label, examples in grouped.items():
        variants = list(examples)
        index = 0
        while len(variants) < MIN_EXAMPLES_PER_INTENT:
            source = examples[index % len(examples)]
            prefix = prefixes[index % len(prefixes)]
            suffix = suffixes[(index // len(prefixes)) % len(suffixes)]
            variants.append(f"{prefix}{source}{suffix}".strip())
            index += 1
        expanded.extend((preprocess(text), label) for text in variants)
    texts, labels = zip(*expanded)
    return list(texts), list(labels)


def build_candidates():
    return {
        "logistic_regression": LogisticRegression(
            max_iter=500, class_weight="balanced", C=4.0
        ),
        "calibrated_linear_svc": CalibratedClassifierCV(
            LinearSVC(class_weight="balanced"), cv=3
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_joblib_dump(value, target: Path) -> None:
    with tempfile.NamedTemporaryFile(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(value, temporary_path)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_json_dump(value: dict, target: Path) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        json.dump(value, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def train() -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    texts, labels = load_and_augment_data()
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42, stratify=labels
    )
    evaluation_vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=3_000)
    train_features = evaluation_vectorizer.fit_transform(train_texts)
    test_features = evaluation_vectorizer.transform(test_texts)

    scores = {}
    for name, candidate in build_candidates().items():
        candidate.fit(train_features, train_labels)
        scores[name] = accuracy_score(test_labels, candidate.predict(test_features))

    selected_name = max(scores, key=scores.get)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=3_000)
    features = vectorizer.fit_transform(texts)
    model = build_candidates()[selected_name]
    model.fit(features, labels)
    _atomic_joblib_dump(model, MODEL_PATH)
    _atomic_joblib_dump(vectorizer, VECTORIZER_PATH)

    metadata = {
        "artifact_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "selected_model": selected_name,
        "validation_scores": {name: round(float(score), 6) for name, score in scores.items()},
        "training_examples": len(texts),
        "classes": sorted(set(labels)),
        "dataset_sha256": _sha256(DATA_PATH),
        "model_sha256": _sha256(MODEL_PATH),
        "vectorizer_sha256": _sha256(VECTORIZER_PATH),
        "feature_count": len(vectorizer.vocabulary_),
    }
    _atomic_json_dump(metadata, METADATA_PATH)

    print(f"Training examples: {len(texts)}")
    for name, score in scores.items():
        print(f"{name} validation accuracy: {score:.3f}")
    print(f"Selected model: {selected_name}")
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Metadata saved to: {METADATA_PATH}")


if __name__ == "__main__":
    train()
