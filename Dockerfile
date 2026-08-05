FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    PORT=8000 \
    HF_HOME=/service/.cache/huggingface \
    GUNICORN_TIMEOUT=120

ARG ARGOS_LANGUAGE_PAIRS=""
ARG RAG_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

WORKDIR /service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY ml_training ./ml_training
COPY scripts ./scripts
RUN python -m ml_training.train_model

# Ship the default embedding model with the image. This prevents the first
# document request after deployment from depending on Hugging Face availability.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${RAG_EMBEDDING_MODEL}')"

ENV ARGOS_DATA_DIRECTORY=/service/argos_data \
    ARGOS_LANGUAGE_PAIRS=${ARGOS_LANGUAGE_PAIRS}
RUN python scripts/install_argos_packages.py

RUN useradd --create-home --uid 10001 chatbot && chown -R chatbot:chatbot /service
USER chatbot

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["sh", "-c", "WORKERS=${WEB_CONCURRENCY:-$((2 * $(nproc) + 1))}; exec gunicorn -k app.core.worker.BoundedUvicornWorker -w \"$WORKERS\" --bind \"0.0.0.0:${PORT}\" --timeout \"${GUNICORN_TIMEOUT}\" --graceful-timeout 30 --access-logfile - app.main:app"]
