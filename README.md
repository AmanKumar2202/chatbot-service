# 🤖 AI Chatbot (Custom ML-Based, No LLM APIs)

🚀 A custom-built AI chatbot that generates human-like responses using machine learning and a knowledge-aware generation system — without relying on external LLM APIs.

---

## 🌟 Highlights

* 🧠 ML-based intent classification (TF-IDF + Logistic Regression)
* 📄 Topic-aware paragraph generation (~200 words)
* 📧 Formal message generation (professional emails)
* 📚 Knowledge injection for domain-specific responses
* 🔁 Dynamic response variation (non-repetitive)
* ⚡ FastAPI backend for real-time interaction

---

## 🧠 How It Works

```text
User Input
   ↓
Preprocessing
   ↓
TF-IDF Vectorization
   ↓
ML Model (Intent Classification)
   ↓
Generator (Paragraph / Formal Message)
   ↓
Response
```

---

## ✨ Features

### 🔹 1. Intelligent Intent Detection

* Handles multiple input variations
* Learns patterns from training data

---

### 🔹 2. Topic-Aware Content Generation

* Generates structured paragraphs
* Injects domain-specific knowledge

**Example:**
Input:

```json
{
  "message": "generate a paragraph on artificial intelligence"
}
```

Output:

> Artificial intelligence is an important subject that plays a significant role in modern life. It involves machine learning, deep learning, and neural networks...

---

### 🔹 3. Formal Message Generator

* Generates professional emails/messages
* Extracts recipient and intent automatically

---

### 🔹 4. Knowledge Injection Engine

* Enhances responses with real-world information
* Makes outputs more relevant and meaningful

---

### 🔹 5. Modular ML Architecture

* Separate training and inference pipelines
* Clean and scalable design

---

## 🏗️ Project Structure

```bash
chatbot-service/
│
├── app/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   ├── ml/
│   └── models/
│
├── ml_training/
├── saved_models/   # (ignored in git)
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

* Python
* FastAPI
* scikit-learn
* joblib
* Regex (for extraction)

---

## ▶️ Getting Started

### 1️⃣ Clone the repo

```bash
git clone <your-repo-url>
cd chatbot-service
```

---

### 2️⃣ Create virtual environment

```bash
py -3.11 -m venv venv
venv\Scripts\activate
```

---

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Train the model

```bash
python -m ml_training.train_model
```

---

### 5️⃣ Run the server

```bash
uvicorn app.main:app --reload
```

---

### 6️⃣ Test API

Open:

```
http://localhost:8000/docs
```

---

## 🧪 API Endpoint

**POST** `/api/chatbot/respond`

### Sample Request:

```json
{
  "message": "write a formal message to manager for leave",
  "user_id": "u1"
}
```

---

## 📊 What Makes This Different?

| Feature                   | Normal Chatbot | This Project |
| ------------------------- | -------------- | ------------ |
| Rule-based                | ❌              | ❌            |
| ML-based intent detection | ❌              | ✅            |
| Topic-aware generation    | ❌              | ✅            |
| Knowledge injection       | ❌              | ✅            |
| Dynamic responses         | ❌              | ✅            |

---

## 🚀 Future Improvements

* 🔹 Semantic similarity using embeddings
* 🔹 Dynamic knowledge base (JSON / DB)
* 🔹 Context-aware conversations

---

## 🎯 Key Takeaway

This project demonstrates how to build an intelligent chatbot using machine learning and structured generation techniques without relying on external AI APIs.

---

## 👨‍💻 Author

**Aman Kumar**
