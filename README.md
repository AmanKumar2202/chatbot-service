# Chatbot Service

A production-oriented, locally operated AI chatbot API built with FastAPI,
scikit-learn, sentence transformers, Redis, and Chroma.

The service performs intent classification, deterministic response generation,
tool-call argument extraction, document retrieval, and extractive document
summarization without sending prompts or document content to an external LLM API.

## Highlights

- Twelve trained intents using TF-IDF features and a probability-producing classifier
- Specialized general-QA, coding-help, formal-writing, and small-talk agents
- Structured tool calls for meetings, web searches, reminders, citations, and schedule matching
- User-isolated retrieval-augmented responses backed by a shared Chroma server
- TextRank-style extractive summarization using local embeddings and PageRank
- Cloze flashcards, batch message analysis, symbolic math help, and essay scaffolds
- Confidence-scored OCR receipt parsing and offline Argos text translation
- Stateless conversation handling for safe horizontal scaling
- Redis-backed, per-user HTTP and WebSocket rate limiting
- REST, Server-Sent Events, and WebSocket interfaces
- Service-key authentication, request-size limits, timeouts, and quotas
- Prometheus metrics, structured JSON logs, health checks, and RAG readiness
- Docker, Docker Compose, Kubernetes HPA, and distributed k6 load-test assets

## Important document-support boundary

The service summarizes and indexes **extracted text**. It does not currently accept
or parse a binary PDF file directly.

For a PDF workflow, the calling application must:

1. Receive and validate the PDF.
2. Extract its text with a PDF parser or OCR service.
3. Send that text to `POST /api/chatbot/summarize`.
4. Optionally send the same text to `POST /api/chatbot/documents` for retrieval.

Therefore, document summarization is implemented, including PDF-derived text
summarization, but native PDF upload/parsing is outside this service.

## Architecture

```text
Client or full-stack application
        |
        | X-Service-Key + user_id + caller-maintained history
        v
FastAPI request controls
        |
        +-- General service
        |     TF-IDF classifier -> confidence gate -> specialized agent/tool router
        |
        +-- RAG service
              local sentence embeddings -> shared Chroma -> grounded excerpts
              local sentence embeddings -> PageRank -> extractive summary

Shared infrastructure:
  Redis  -> distributed per-user rate limits
  Chroma -> user-isolated document vectors
```

Conversation history is supplied by the caller with every request. The service
does not store conversation state in SQLite or another local database, so any
replica can process the next request.

### Deployment roles

Set `SERVICE_ROLE` to control workload placement:

| Role | Purpose |
|---|---|
| `general` | Lightweight classification, agents, tool routing, streaming, and WebSockets |
| `rag` | Document indexing, retrieval, embeddings, summarization, and offline translation |
| `all` | Runs both workloads; suitable for local development |

In production, route ordinary chat traffic to the general deployment and
document-related traffic to the RAG deployment.

## Implementation status and boundaries

All features below are implemented and covered by automated tests. Several are
deliberately scoped so the service does not imply capabilities it does not have.

| Feature | Status | Implemented behavior | Deliberate boundary |
|---|---|---|---|
| Intent classification | Implemented | Twelve local TF-IDF intents with confidence gating | Not an open-ended generative model |
| Specialized agents | Implemented | General, coding, formal-writing, and small-talk routing | Responses are knowledge/rule/template based |
| Meeting tool | Implemented | Extracts topic and raw time phrase | Caller creates the calendar event |
| Web-search tool | Implemented | Extracts a search query | Caller performs the search |
| Reminder tool | Implemented | Extracts reminder content and raw time | Caller resolves, schedules, and delivers it |
| Citation finder | Implemented | Extracts an academic topic into `find_citations` | Caller queries Semantic Scholar |
| Schedule matcher | Implemented | Extracts raw availability phrases | Caller resolves timezones and intersects intervals |
| RAG | Implemented | User-isolated embeddings and grounded excerpts | Answers remain extractive rather than generative |
| Document summary | Implemented | Local embedding similarity and PageRank | Accepts extracted text, not binary files |
| Flashcards | Implemented | Definitions plus TF-IDF cloze deletion | Works best on explanatory text |
| Action items | Implemented | Rule-based assignment and owner extraction | Subtle or implicit assignments may be missed |
| Deadlines | Implemented | Deadline-context and raw time extraction | Caller converts phrases to concrete timestamps |
| Meeting minutes | Implemented | Summary, attendees, actions, and deadlines from chat | No live audio capture or transcription |
| Context catch-up | Implemented | Three extractive bullet points | Requires enough source sentences for three points |
| Math homework help | Implemented | SymPy equations, arithmetic, derivatives, and integrals | Accepts symbolic expressions, not unrestricted word problems |
| Essay homework help | Implemented | Type-aware structure and Socratic questions | Always labeled as a generic template |
| Formal email output | Implemented | Internal agent email mode returns subject and body | No dedicated email endpoint or delivery integration |
| Receipt parser | Implemented | OCR-text items, totals, and confidence score | OCR and bill-splitting remain with the caller |
| Translation | Implemented | Offline Argos inference | Only pre-installed directional language pairs work |
| Focus/catch-up support | Implemented | Reuses catch-up analysis | Focus timers and notifications belong to the caller |

## Repository structure

```text
app/
  core/             Configuration, authentication, limits, logging, metrics
  data/             Structured local knowledge base
  ml/               Preprocessing, model validation, and intent prediction
  models/           Pydantic API contracts
  routes/           REST, SSE, document, and WebSocket endpoints
  services/
    agents/         Specialized deterministic agents
    rag/            Embeddings, Chroma storage, retrieval, summarization
    tools/          Tool registry and argument extraction
  static/           Minimal browser client
k8s/                Autoscaled production and distributed-test manifests
load_tests/         k6 response, stream, document, quota, and 50k-user workloads
ml_training/        Training data and reproducible training pipeline
saved_models/       Verified classifier artifacts and metadata
tests/              Unit and API integration tests
```

## Technology stack

- Python 3.11+
- FastAPI and Uvicorn
- Gunicorn for production process management
- scikit-learn for intent classification and cosine similarity
- sentence-transformers for local document embeddings
- NetworkX PageRank for extractive summarization
- Chroma in HTTP server mode for shared vector storage
- Redis and SlowAPI for distributed rate limiting
- Prometheus FastAPI Instrumentator
- pytest and k6

## Quick start

For a complete first-time setup, every `.env` variable, Docker instructions,
tests, translation packages, and troubleshooting, see
[RUN_PROJECT.md](RUN_PROJECT.md).

### 1. Create the environment

PowerShell:

```powershell
py -3.11 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a random `SERVICE_API_KEY` of at least 16 characters in `.env`. For a
dependency-free local infrastructure setup, also select the in-memory rate-limit,
embedding, and vector backends as described in [RUN_PROJECT.md](RUN_PROJECT.md).

### 2. Choose how to run

The default configuration expects:

- Redis at `localhost:6379`, logical database `1`
- Chroma at `localhost:8001`

The provided Compose topology starts two application roles plus Redis and Chroma.
Train the classifier artifacts before the first image build:

```powershell
python -m ml_training.train_model
docker compose -f docker-compose.scaled.yml up --build
```

For isolated development without external services, set:

```dotenv
RATE_LIMIT_STORAGE_URI=memory://
RAG_EMBEDDING_BACKEND=hashing
RAG_VECTOR_BACKEND=memory
```

The memory backends are process-local and must not be used for multi-replica
production deployments.

To run a single development process instead, configure the in-memory backends,
then run:

```powershell
python -m ml_training.train_model
uvicorn app.main:app --reload
```

Development URLs:

- Web client: `http://localhost:8000/`
- OpenAPI UI: `http://localhost:8000/docs`
- Metrics: `http://localhost:8000/metrics`

`--reload` is for development only. The production image starts Gunicorn with
bounded Uvicorn workers and explicit thread settings.

## API

All `/api/chatbot` HTTP endpoints require:

```http
X-Service-Key: your-service-key
```

Send `X-User-Id` when an endpoint does not include `user_id` in its body. This
allows the distributed limiter to maintain an independent bucket for that user.

### Endpoint reference

| Method | Path | Purpose | Recommended role |
|---|---|---|---|
| `POST` | `/api/chatbot/respond` | Non-streamed chat and tool routing | General, or RAG when `use_documents=true` |
| `POST` | `/api/chatbot/stream` | SSE chat response | General, or RAG when `use_documents=true` |
| `WS` | `/api/chatbot/ws/chat` | Authenticated WebSocket chat | General |
| `POST` | `/api/chatbot/documents` | Index extracted document text | RAG |
| `DELETE` | `/api/chatbot/documents/{doc_id}` | Delete a user's indexed document | RAG |
| `POST` | `/api/chatbot/summarize` | Extractive text summary | RAG |
| `POST` | `/api/chatbot/analyze` | Actions, deadlines, minutes, or catch-up | Mode dependent |
| `POST` | `/api/chatbot/flashcards` | Definition/cloze cards | General |
| `POST` | `/api/chatbot/homework-help` | Symbolic math or essay scaffold | General |
| `POST` | `/api/chatbot/translate` | Offline text translation | RAG |
| `POST` | `/api/chatbot/receipt/parse` | Parse OCR receipt text | General |
| `GET` | `/health` | Process liveness | Any |
| `GET` | `/ready` | Classifier and RAG readiness | Any |
| `GET` | `/metrics` | Prometheus metrics | Any |

### Chat response

```http
POST /api/chatbot/respond
Content-Type: application/json
X-Service-Key: your-service-key

{
  "message": "remind me tomorrow to call the bank",
  "user_id": "user-123",
  "history": [],
  "agent_override": null,
  "use_documents": false
}
```

Example:

```json
{
  "reply": "Got it — I'll remind you about that.",
  "intent": "set_reminder",
  "confidence": 0.87,
  "agent": "tool_router",
  "tool_call": {
    "name": "set_reminder",
    "arguments": {
      "message": "call the bank",
      "time": "tomorrow"
    },
    "missing_arguments": []
  },
  "sources": []
}
```

The service detects the action but does not schedule reminders, create calendar
events, or perform web searches. The trusted caller executes returned tool calls.

### Streaming

`POST /api/chatbot/stream` accepts the chat request contract and returns
`text/event-stream` events:

```text
data: {"delta": "partial response "}
data: {"done": true, "intent": "greeting", "delivery_time_ms": 4.21, ...}
```

Streams have a configurable maximum duration. If the cap is reached, remaining
generated content is flushed instead of holding the connection indefinitely.

### WebSocket

```text
ws://localhost:8000/api/chatbot/ws/chat?service_key=...&user_id=user-123
```

Each message uses the chat request JSON contract. WebSocket connections enforce
authentication, connection limits, per-user message limits, and idle timeouts.

### Index a document

```http
POST /api/chatbot/documents
Content-Type: application/json
X-Service-Key: your-service-key

{
  "doc_id": "manual-1",
  "filename": "manual.pdf",
  "text": "Text extracted from the document...",
  "user_id": "user-123"
}
```

Documents are chunked, embedded locally, and stored in a collection derived from
the user's hashed identity. Per-user document and chunk quotas bound storage growth.

Delete a document:

```http
DELETE /api/chatbot/documents/manual-1?user_id=user-123
X-Service-Key: your-service-key
```

Set `use_documents` to `true` on a chat request to retrieve relevant excerpts.
Responses include filenames and excerpts in `sources`; the service does not invent
information beyond retrieved content.

### Summarize extracted document text

```http
POST /api/chatbot/summarize
Content-Type: application/json
X-Service-Key: your-service-key
X-User-Id: user-123

{
  "text": "Long text extracted from a document or PDF...",
  "num_sentences": 5
}
```

Response:

```json
{
  "summary": "Selected representative sentences in original document order.",
  "key_points": [
    "First representative sentence.",
    "Another representative sentence."
  ]
}
```

Constraints:

- Text length: 1 to 2,000,000 characters
- Summary length: 1 to 20 sentences
- Method: local extractive PageRank summarization
- No external LLM calls

If the document contains fewer sentences than requested, its original text is
returned with the detected sentences as key points.

### Health and observability

| Endpoint | Purpose |
|---|---|
| `GET /health` | Process liveness |
| `GET /ready` | Classifier readiness and separate `rag_ready` status |
| `GET /metrics` | Prometheus metrics |

Custom metrics cover classifier latency, embedding latency, Chroma operations,
thread-pool utilization, and rate-limit rejections. Application logs are emitted
as structured JSON.

### Productivity and study endpoints

All endpoints use service-key authentication and distributed rate limiting:

| Endpoint | Local behavior |
|---|---|
| `POST /api/chatbot/analyze` | Action items, deadlines, chat meeting minutes, or three-point catch-up |
| `POST /api/chatbot/flashcards` | Definition and TF-IDF cloze flashcards |
| `POST /api/chatbot/homework-help` | SymPy math computation or explicitly generic essay scaffolding |
| `POST /api/chatbot/translate` | Offline Argos translation using installed language packs |
| `POST /api/chatbot/receipt/parse` | Confidence-scored parsing of OCR-produced receipt text |

`find_citations` and `match_schedule` use the existing tool-call contract. The
trusted caller executes Semantic Scholar search and timezone-aware schedule
intersection. Essay help always sets `is_generic_template` to `true`; receipt
parsing accepts OCR text, and meeting minutes operate on chat messages, not audio.

No translation pairs are bundled by default. Install selected pairs locally:

```powershell
python scripts/install_argos_packages.py en-es en-fr
```

Or bake them into an image:

```powershell
docker build --build-arg ARGOS_LANGUAGE_PAIRS=en-es,en-fr -t chatbot-service .
```

Inference is offline after installation. Unsupported pairs return HTTP 422.

#### Batch analysis

```http
POST /api/chatbot/analyze
Content-Type: application/json
X-Service-Key: your-service-key
X-User-Id: user-123

{
  "mode": "meeting_minutes",
  "messages": [
    {
      "id": "m1",
      "sender": "Aman",
      "content": "I will submit the report by tomorrow."
    },
    {
      "id": "m2",
      "sender": "Maya",
      "content": "Maya, can you review the final draft by next Tuesday?"
    }
  ]
}
```

Supported modes are `action_items`, `deadlines`, `meeting_minutes`, and
`catch_up`. The response contains the selected `mode` and a mode-specific
`result` object. Meeting minutes and catch-up use the embedding summarizer and
must be routed to a RAG deployment. Action-item and deadline analysis can use the
general deployment.

#### Flashcards

```http
POST /api/chatbot/flashcards

{
  "text": "Photosynthesis is the process by which plants convert light.",
  "max_cards": 10
}
```

The response is `{ "flashcards": [{"question": "...", "answer": "..."}] }`.
`max_cards` must be between 1 and 50. Unsuitable source text can legitimately
produce an empty list.

#### Homework help

```http
POST /api/chatbot/homework-help

{
  "prompt": "solve 2x + 4 = 10",
  "type": "math"
}
```

Responses contain `steps`, `final_answer`, and `is_generic_template`. Math
results set the flag to `false`. Essay requests always set it to `true` and return
generic structural guidance rather than pretending to understand the topic like
an LLM.

#### Offline translation

```http
POST /api/chatbot/translate
X-User-Id: user-123

{
  "text": "Hello",
  "source_lang": "en",
  "target_lang": "es"
}
```

Language codes are lowercase Argos codes. Direction matters: installing `en-es`
does not install `es-en`. The endpoint runs on RAG deployments and returns
`translated_text`, or HTTP 422 when the requested pair is unavailable.

#### Receipt OCR parsing

```http
POST /api/chatbot/receipt/parse

{
  "ocr_text": "Coffee 3.50\nBagel 4.00\nSubtotal 7.50\nTax 0.60\nTotal 8.10"
}
```

The response contains parsed `items`, `subtotal`, `tax`, `tip`, `total`, and a
`parse_confidence` value between 0 and 1. Low confidence is intentional when
items and labeled totals disagree.

## Model training

The dataset is balanced to 600 examples across twelve intents. The training pipeline
compares:

- Class-weighted logistic regression
- Calibrated linear support-vector classification

Both use TF-IDF unigram and bigram features. The selected model is retrained on
the complete dataset and written atomically with its vectorizer and metadata:

```powershell
python -m ml_training.train_model
```

Startup verifies dataset, model, and vectorizer SHA-256 hashes and rejects stale,
corrupt, or scikit-learn-incompatible artifacts. The current selected logistic
regression model achieved 98.3% validation accuracy.

## Testing

Run the complete automated suite:

```powershell
python -m pytest -q
```

Current verified result:

```text
103 passed
```

The suite covers classification regression, agents, all five tool routes,
flashcards, action items, deadlines, availability, meeting minutes, context
catch-up, SymPy math, generic essay labeling, receipt confidence, offline
translation behavior, summarization, authentication, stateless history,
request-size enforcement, per-user rate isolation, WebSockets, document quotas,
Chroma client selection, retrieval, streaming, metrics, readiness, and
model-artifact integrity.

Additional validation:

```powershell
python -m compileall app tests ml_training
python -m pip check
docker compose -f docker-compose.scaled.yml config --quiet
```

## Performance and scaling

Local in-process measurements on a 4-core/8-thread Intel Core i5-1155G7 with
7.8 GB RAM produced:

| Workload | Throughput | p95 latency | Errors |
|---|---:|---:|---:|
| 100 concurrent requests | 240.5 requests/s | 442 ms | 0 |
| 500-request burst | 240.6 requests/s | 1.76 s | 0 |
| 1,000-request burst | 272.1 requests/s | 3.08 s | 0 |
| 100 workers for 15 seconds | 233.2 requests/s | 609 ms | 0/3,527 |

These figures are development-machine measurements, not a claim that one instance
serves 50,000 concurrent users.

Production assets include:

- Stateless general and RAG deployments
- Redis-backed distributed limits
- Shared Chroma storage
- Kubernetes rolling updates and disruption budgets
- HPA ranges of 4–50 general replicas and 2–20 RAG replicas
- A 20-runner k6 workload that ramps to 50,000 virtual users

Passing the distributed workload in the target cluster is the release gate for
claiming verified 50,000-user concurrency. See [k8s/README.md](k8s/README.md).

## Configuration

Copy `.env.example` for the complete runtime baseline. The exhaustive reference,
including validation ranges and container-only variables, is in
[RUN_PROJECT.md](RUN_PROJECT.md#environment-variable-reference). Important
settings include:

| Variable | Default | Description |
|---|---|---|
| `SERVICE_API_KEY` | Required | Shared service authentication secret |
| `SERVICE_ROLE` | `all` | `general`, `rag`, or `all` |
| `RATE_LIMIT` | `60/minute` | Per-user HTTP request limit |
| `RATE_LIMIT_STORAGE_URI` | `redis://localhost:6379/1` | Distributed limiter storage |
| `WEBSOCKET_CONNECTION_RATE_LIMIT` | `10/minute` | Connection attempts per user |
| `WEBSOCKET_MESSAGE_RATE_LIMIT` | `60/minute` | Messages per user |
| `WEBSOCKET_IDLE_TIMEOUT_SECONDS` | `60` | Inactive connection timeout |
| `MAX_REQUEST_BODY_BYTES` | `2100000` | Hard ASGI request-body cap |
| `SERVER_LIMIT_CONCURRENCY` | `200` | Per-worker server concurrency cap |
| `RAG_EMBEDDING_BACKEND` | `sentence_transformers` | Embedding implementation |
| `RAG_VECTOR_BACKEND` | `chroma` | Vector-store implementation |
| `RAG_CHROMA_HOST` | `localhost` | Shared Chroma hostname |
| `RAG_CHROMA_PORT` | `8001` | Shared Chroma port |
| `RAG_MAX_DOCUMENTS_PER_USER` | `100` | Document quota |
| `RAG_MAX_CHUNKS_PER_USER` | `5000` | Chunk quota |
| `RAG_WARMUP_ON_STARTUP` | `false` | Eagerly load embeddings on RAG startup |
| `ARGOS_DATA_DIRECTORY` | `./argos_data` | Installed translation package location |
| `STREAM_MAX_DURATION_SECONDS` | `30` | Maximum server-side SSE duration |

## Production checklist

- Replace the example container image and Redis URI in `k8s/chatbot.yaml`.
- Store `SERVICE_API_KEY` in a secret manager; never commit it.
- Use TLS at the ingress or gateway.
- Route general and document workloads to their respective services.
- Use a managed highly available Redis deployment.
- Back Chroma with production persistent storage and backups.
- Install Metrics Server for HPA and scrape `/metrics` with Prometheus.
- Run the distributed k6 test before publishing a 50,000-user claim.
- Tune replicas and resource limits from measured production telemetry.

For the complete command-by-command setup, environment, Docker, Kubernetes,
autoscaling, monitoring, and 50,000-user testing procedure, see
[DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md).

## Security notes

- The service key protects service-to-service access; it is not end-user identity.
- The trusted caller supplies `user_id`, which scopes rate limits and documents.
- Validate PDF type, size, malware status, and ownership before extracting text.
- Avoid logging service keys, document contents, or WebSocket query strings.
- Rotate credentials and restrict network access to Redis and Chroma.

## License

No license file is currently included. Add an explicit license before distributing
or accepting external contributions.
