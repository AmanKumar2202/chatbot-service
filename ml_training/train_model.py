import json
import os
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

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


X_train, X_test, y_train, y_test = train_test_split(X, labels, test_size=0.2, random_state=42, stratify=labels)
evaluation_model = LogisticRegression(max_iter=500, class_weight="balanced", random_state=42)
evaluation_model.fit(X_train, y_train)
predictions = evaluation_model.predict(X_test)
print(f"Validation accuracy: {accuracy_score(y_test, predictions):.3f}")
print(classification_report(y_test, predictions, zero_division=0))

# Fit the deployable model on all validated data.
model = LogisticRegression(max_iter=500, class_weight="balanced", random_state=42)
model.fit(X, labels)


#SAVE MODEL


joblib.dump(model, MODEL_PATH)
joblib.dump(vectorizer, VECTORIZER_PATH)

print("Model trained and saved successfully!")
print(f" Model path: {MODEL_PATH}")
print(f" Vectorizer path: {VECTORIZER_PATH}")
