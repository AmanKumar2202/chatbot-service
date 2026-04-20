from app.ml.model_loader import load_model
from app.ml.preprocess import preprocess 

def predict_intent(message: str) -> str:
    model, vectorizer = load_model()

    cleaned = preprocess(message)

    X = vectorizer.transform([cleaned])
    return model.predict(X)[0]