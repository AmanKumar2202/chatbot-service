from prometheus_client import Counter, Gauge, Histogram


CLASSIFIER_LATENCY = Histogram(
    "chatbot_classifier_seconds", "Classifier inference latency"
)
EMBEDDING_LATENCY = Histogram(
    "chatbot_embedding_seconds", "Sentence embedding latency"
)
CHROMA_LATENCY = Histogram(
    "chatbot_chroma_seconds", "Chroma operation latency", ["operation"]
)
RATE_LIMIT_REJECTIONS = Counter(
    "chatbot_rate_limit_rejections_total", "Rejected rate-limited operations", ["transport"]
)
THREADPOOL_BORROWED = Gauge(
    "chatbot_threadpool_borrowed_tokens", "AnyIO thread-pool tokens currently borrowed"
)
