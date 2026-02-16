# Owkin Agentic PoC – Cancer Gene Assistant

A proof-of-concept agentic product that lets non-technical stakeholders ask questions in natural language about cancer-related genes and their median expression values. The solution orchestrates two data functions (`get_targets`, `get_expressions`) via a retrieval-augmented pipeline backed by a local LLM (Llama 3.2 3B via Ollama).

---

## How to set up and run

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Ollama** | Installed on the host machine — [ollama.com/download](https://ollama.com/download) |
| **Docker & Docker Compose** | For building and running the web application |
| **Hardware** | Mac (Apple Silicon or Intel) or Windows 11, ≤ 16 GB RAM, no GPU required |

### Step 1 — Install Ollama and pull the model

**macOS (Homebrew):**

```bash
brew install ollama
```

**Or download the installer** from <https://ollama.com/download> (macOS / Windows / Linux).

Once installed, start the Ollama server and pull the model:

```bash
# Start Ollama (runs in the background on port 11434)
ollama serve
```

In a **separate terminal**, pull the model (~2 GB download, only needed once):

```bash
ollama pull llama3.2:3b
```

> **Verify** Ollama is reachable: `curl http://localhost:11434/api/tags` should return a JSON list containing the pulled model.

### Step 2 — Build and start the application

```bash
docker compose up --build
```

The app container runs a wait script (`scripts/wait_ollama.sh`) that polls Ollama on the host (`host.docker.internal:11434`) before starting the Chainlit UI. You will see `Ollama is ready.` in the logs once the connection is established.

### Step 3 — Open the UI

Open **<http://localhost:8000>** in your browser. The Chainlit chat interface will appear.

### Step 4 — Try the expected queries

- *"How can you help me?"*
- *"What are the main genes involved in lung cancer?"*
- *"What is the median value expression of genes involved in breast cancer?"*
- *"What is the median value expression of genes involved in esophageal cancer?"*

### Stopping

```bash
docker compose down
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API endpoint (host machine) |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model name; change in `docker-compose.yml` or pass as env |
| `LOG_DIR` | `/app/logs` | Log directory inside the container (mapped to `./logs` on host) |

To try a different model (e.g. the smaller 1B variant):

```bash
ollama pull llama3.2:1b
OLLAMA_MODEL=llama3.2:1b docker compose up --build
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Waiting for Ollama...` loops forever | Ollama is not running on the host. Run `ollama serve` in a separate terminal. |
| `Cannot reach the language model` in the chat | Same as above, or the model has not been pulled yet. Run `ollama pull llama3.2:3b`. |
| Port 8000 already in use | Stop the conflicting process or change the port in `docker-compose.yml`. |

---

## Design overview

### Architecture

The system uses a **retrieval-augmented generation (RAG)** approach:

1. **Query analysis** — The user's message is scanned for known cancer types and gene names present in the CSV dataset.
2. **Context retrieval** — Matching data is retrieved using `get_targets(cancer_name)` and `get_expressions(genes)`, producing a structured data block.
3. **Prompt construction** — The retrieved data is injected into a system prompt that instructs the LLM to answer **only** from the provided data.
4. **LLM generation** — The LLM (Llama 3.2 3B via Ollama) produces a natural-language answer grounded in the retrieved context.
5. **Response & logging** — The answer is streamed to the Chainlit UI and logged (JSONL) with model name, latency, and request ID.

This deterministic retrieval step ensures the LLM always receives the relevant CSV data, avoiding tool-call failures that can occur with smaller models.

### Key components

| Component | Technology | Role |
|-----------|-----------|------|
| **LLM** | Llama 3.2 3B (instruct) via Ollama | Natural-language understanding and answer generation |
| **Data layer** | pandas + CSV | Loads `owkin_take_home_data.csv`; provides `get_targets` and `get_expressions` |
| **Orchestration** | Python (context-injection pipeline) | Scans query, retrieves data, builds prompt, calls LLM |
| **UI** | Chainlit (`ui/`) | Chat interface with streaming responses |
| **Logging** | JSONL (`logs/query_answers.jsonl`) | Every query/answer logged with `request_id`, `timestamp`, `model`, `latency_ms` |
| **Config** | Environment variables (`config/settings.py`) | Model name, Ollama URL, log directory — single point of configuration |

### Folder structure

```text
project/
├── docker-compose.yml          # App service (connects to host Ollama)
├── Dockerfile                  # Python 3.11, LangChain, pandas, Chainlit
├── requirements.txt
├── owkin_take_home_data.csv    # Dataset
├── README.md                   # This file
├── docs/
│   └── AI_COMPONENTS_AND_TRADEOFFS.md
├── config/
│   └── settings.py             # OLLAMA_BASE_URL, OLLAMA_MODEL, LOG_DIR
├── app/
│   ├── agent.py                # Context retrieval + LLM pipeline
│   ├── data.py                 # CSV loading, get_targets, get_expressions
│   └── logging_utils.py        # JSONL query/answer logging
├── ui/
│   ├── app.py                  # Chainlit entry point
│   └── .chainlit/              # Chainlit config
├── logs/                       # query_answers.jsonl (gitignored, Docker volume)
└── scripts/
    ├── wait_ollama.sh          # Waits for Ollama before app starts
    ├── pull_model.sh           # Optional: pull model via script
    └── check_ollama.sh         # Diagnostic: verify Ollama + model
```

---

## AI components: architecture, use and trade-offs

### What is used

- **LLM:** Llama 3.2 3B (instruct) via Ollama. Used for understanding the user's intent and generating the final natural-language answer from retrieved data.
- **Orchestration:** A retrieval-augmented pipeline that deterministically fetches relevant data from the CSV and injects it into the LLM prompt.

### How they are used

1. User sends a message in the chat.
2. The pipeline scans the query for known cancer types and gene names.
3. Matching data is retrieved via `get_targets(cancer_name)` and `get_expressions(genes)`.
4. Retrieved data is injected into the **system prompt**, which instructs the LLM to answer only from the provided context and never fabricate data.
5. The LLM produces a final answer, which is streamed to the UI and logged.

### Trade-offs

| Decision | Benefit | Trade-off |
|----------|---------|-----------|
| Small local model (3B) | Runs on CPU, ≤ 16 GB RAM, no GPU needed | Weaker reasoning than 7B+ models |
| Deterministic retrieval (not LLM-driven tool calls) | Reliable data retrieval regardless of model capability; no tool-call parsing failures | Less flexible than LLM-driven tool selection for complex multi-step queries |
| Single provider (Ollama) | Simple setup, one command to start | No built-in A/B across providers; would need extra abstraction |
| Anti-hallucination system prompt | Keeps answers grounded in the CSV; handles missing cancer types correctly | Depends on the model following instructions; not a hard guardrail |
| Ollama on host (not in Docker) | Simpler Docker setup; Ollama manages its own model cache | Requires Ollama installed on the host machine |

---

## UI: purpose, why Chainlit, replaceability

- **Purpose:** The UI is an interactive demonstration layer for the PoC, not a production frontend.
- **Why Chainlit:** Chosen for rapid prototyping of the chat interaction under time constraints, while keeping focus on core agent behaviour.
- **Replaceability:** All UI code lives under `ui/`. The agent and data layer live in `app/`. The UI can be swapped (e.g. custom HTML, Streamlit, another framework) without changing the agent or data logic.

---

## Logging and model comparison

Every query/answer pair is appended to `logs/query_answers.jsonl` with:

- `request_id` (UUID)
- `timestamp` (ISO 8601)
- `model` (the model used, e.g. `llama3.2:3b`)
- `query`, `answer`
- `latency_ms`

To compare outputs across models, run the same queries with different `OLLAMA_MODEL` values. Each record includes the model name, making it easy to filter and compare with `jq`:

```bash
jq 'select(.query | test("lung"))' logs/query_answers.jsonl
```

---

## AI-assisted coding: pros and cons in this project

### Pros

- **Faster scaffolding:** Boilerplate for LangChain, Docker, Chainlit, and the retrieval pipeline was generated and adapted quickly.
- **Focus on delivery:** Under a 4-hour constraint, AI assistance helped produce a runnable, coherent prototype instead of writing everything from scratch.
- **Consistency:** Project structure (config, data, agent, logging) and conventions (env-based config, JSONL logging) were applied consistently across files.

### Cons

- **Architectural ownership:** Core system design decisions (agent-tool separation, deterministic prompting, minimal dependency strategy, and local LLM deployment) were defined independently. AI assistance was used strictly for implementation acceleration.
- **Hidden complexity:** AI-generated suggestions sometimes introduced abstractions that were unnecessary for a first PoC. Simplification was required to avoid technical debt.
- **Verification required:** All generated code was reviewed and tested; dependencies and security (e.g. no secrets in repo) were checked by hand.
- **Design ownership:** Architecture and key decisions (retrieval pipeline, anti-hallucination prompt, log format, Ollama-on-host setup) were made by the author; AI was used as a coding assistant, not as the design authority.


## How I spent the 4 hours

To deliver a functional product within the time constraint, I followed a structured sprint with three phases:

### Phase 1 — Research & architecture (~1 hour)

I had a rough idea of the end state, so I used Cursor's Plan mode to break the task into pieces and produced the planning document. During this phase I researched component choices — for example, I initially considered a custom HTML frontend but discovered Chainlit, which let me prototype the chat UI in minutes instead of hours.

### Phase 2 — Implementation & first test (~1 hour)

Using the architecture document as a blueprint, I scaffolded the full project (Docker, config, data layer, agent, UI) with Cursor and tested end-to-end. The priority at this stage was a **working system** — once queries returned answers, I could shift focus to answer quality.

### Phase 3 — Iteration & improvement (~2 hours)

The initial version had several issues that required architectural pivots:

1. **Docker performance:** I originally ran Ollama, the LLM, and Chainlit all inside Docker. Inference took 4–5 minutes per query. Moving Ollama to the host machine brought latency down to an acceptable range.
2. **LLM tool-calling reliability:** The first approach used a ReAct-style agent where the 3B model decided which tools to call. Results were inconsistent — the model frequently produced malformed tool calls or hallucinated data. A 3B parameter model simply isn't reliable enough for autonomous tool selection.
3. **Switch to RAG:** I replaced the ReAct agent with a deterministic retrieval pipeline: the system scans the query for known cancer types and gene names, fetches the matching data from the CSV, and injects it into the prompt. This guarantees the LLM always receives the right context, producing accurate and grounded answers. The trade-off is less flexibility for novel query patterns, but for this dataset and scope it is the more pragmatic choice.
