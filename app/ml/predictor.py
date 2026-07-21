from app.ml.model_loader import load_model
from app.ml.preprocess import preprocess 

def predict_intent(message: str) -> tuple[str, float]:
    model, vectorizer = load_model()

    cleaned = preprocess(message)

    X = vectorizer.transform([cleaned])
    probabilities = model.predict_proba(X)[0]
    best_index = probabilities.argmax()
    return str(model.classes_[best_index]), float(probabilities[best_index])
