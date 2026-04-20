import joblib
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

MODEL_PATH = os.path.join(BASE_DIR, "saved_models", "model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "saved_models", "vectorizer.pkl")

model = None
vectorizer = None


def load_model():
    global model, vectorizer

    if model is None or vectorizer is None:
        model = joblib.load(MODEL_PATH)
        vectorizer = joblib.load(VECTORIZER_PATH)

    return model, vectorizer