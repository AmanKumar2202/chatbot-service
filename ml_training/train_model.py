import json
import os
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Import preprocessing
from app.ml.preprocess import preprocess  



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "training_data.json")
MODEL_DIR = os.path.join(BASE_DIR, "..", "saved_models")

MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")


os.makedirs(MODEL_DIR, exist_ok=True)


#LOAD DATA


with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [preprocess(item["text"]) for item in data]
labels = [item["label"] for item in data]




vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),   # Unigrams + bigrams (better accuracy)
    max_features=1000     # Limit features
)

X = vectorizer.fit_transform(texts)


# MODEL TRAINING


model = LogisticRegression(max_iter=200)
model.fit(X, labels)


#SAVE MODEL


joblib.dump(model, MODEL_PATH)
joblib.dump(vectorizer, VECTORIZER_PATH)

print("Model trained and saved successfully!")
print(f" Model path: {MODEL_PATH}")
print(f" Vectorizer path: {VECTORIZER_PATH}")