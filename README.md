# SAR Narrative Generator

AI-assisted compliance system for generating **Suspicious Activity Report (SAR)** narratives with full, immutable audit trail capabilities. The platform analyzes customer transaction activity, detects money-laundering typologies, retrieves relevant regulatory context, and drafts a FinCEN-aligned narrative that a compliance analyst reviews, edits, approves, and exports.

## Features

- **Automated Pattern Detection** — rule-based detection engine covering six AML typologies:
  - Structuring (transactions below the CTR threshold)
  - Funnel Activity (multiple sources concentrated to a single destination)
  - Rapid Movement (funds passing through the account within hours)
  - Cross-Border Anomalies (high-risk jurisdictions)
  - Round-Amount Patterns
  - Velocity Spikes
- **Feature Engineering** — comprehensive transaction analytics (inflow/outflow, velocity, counterparty concentration, cross-border ratio, near-threshold clustering).
- **RAG-Grounded Narratives** — retrieval-augmented generation grounds every narrative in a curated regulatory knowledge base (AML typologies, FinCEN phrasing, SAR templates) via ChromaDB semantic search.
- **LLM Generation (Ollama / Mistral)** — narratives are produced by a local Mistral 7B model, orchestrated through LangChain and traced end-to-end.
- **Human-in-the-Loop Review** — analysts review detected patterns, edit the draft, and formally approve before filing.
- **Full Audit Trail** — every event (audit start, feature extraction, pattern detection, prompt/response, edit, approval, export) is captured for complete traceability and compliance review.
- **PDF Export** — one-click generation of a formatted, filing-ready SAR document.
- **Pre-Loaded Data** — realistic sample customers and transactions are seeded into PostgreSQL for immediate use.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                        │
│        (Dashboard, Customer View, Review, Approve, Export)    │
└──────────────────────────────────────────────────────────────┘
                              │  REST (HTTP)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                         │
├───────────────┬───────────────┬───────────────┬──────────────┤
│  Ingestion &  │  Processing   │  Intelligence │  Governance  │
│  Validation   │  (Features +  │  (RAG +       │  (Audit &    │
│               │   Patterns)   │  LangChain +  │  Compliance) │
│               │               │  LLM)         │              │
└───────────────┴───────────────┴───────────────┴──────────────┘
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
         PostgreSQL       ChromaDB          Ollama
        (Cases & Data)   (Vector Store)   (Mistral 7B)
```

The backend is organized into four cooperating subsystems:

| Subsystem | Responsibility | Modules |
|-----------|----------------|---------|
| **Ingestion & Validation** | Validate and normalize transaction/KYC data entering the system | `processing/validators.py`, `processing/normalizer.py` |
| **Processing** | Derive analytical features and detect suspicious patterns | `processing/features.py`, `patterns/` |
| **Intelligence** | Retrieve regulatory context and generate the narrative | `rag/`, `llm/` |
| **Governance** | Capture the audit trail and produce compliance summaries | `audit/` |

## End-to-End Flow

A complete SAR is produced through a nine-stage pipeline. The single entry point is the **Start Audit** action, which orchestrates every downstream stage.

```
 Seed DB ─▶ Start Audit ─▶ Features ─▶ Patterns ─▶ RAG Context ─▶ LLM Narrative ─▶ Review/Edit ─▶ Approve ─▶ Export PDF
 (stage 1)   (stage 2)     (stage 3)   (stage 4)    (stage 5)      (stage 6)        (stage 8)      (stage 8)   (stage 9)
                                        └──────────── every step written to the audit trail (stage 7) ───────────┘
```

**1. Data foundation.**
Customers and their transaction histories are loaded into PostgreSQL by `data_samples/seed_data.py`. As data enters the system it is schema-validated by `processing/validators.py` (required fields, valid dates/amounts, transaction-type normalization) and normalized into a consistent analytical shape by `processing/normalizer.py` (date parsing, weekend/off-hours flags, cross-border and round-amount detection, counterparty aggregation).

**2. Start Audit.**
An analyst selects a customer and triggers `POST /api/customers/{id}/audit` (`backend/api/routes.py`). This handler is the orchestrator: it creates an `audit` record, pulls the customer's transactions, and drives the remaining stages in sequence, committing an audit-log entry at each step.

**3. Feature extraction.**
`processing/features.py` computes the analytical feature set: total inflow/outflow, net flow, transaction counts, unique counterparties, cross-border count and percentage, amount statistics, velocity (transactions/day), weekend/off-hours activity, round-amount frequency, near-threshold clusters, rapid-movement pairs, and the top counterparties by volume.

**4. Pattern detection.**
`patterns/detector.py` runs the six detection rules against the features and normalized transactions. Thresholds and the high-risk jurisdiction list live in `patterns/rules.py`; each hit returns a `PatternMatch` (`patterns/models.py`) carrying a confidence score, severity, human-readable description, supporting evidence, and a recommendation. `patterns/models.py` also computes an overall weighted risk score.

**5. RAG retrieval.**
`rag/retriever.py` builds a case context and issues a semantic query against the ChromaDB vector store (`rag/vectorstore.py`), which was populated at startup from the regulatory knowledge base in `prompts/`. Embeddings are produced by `rag/embeddings.py` (sentence-transformers, `all-MiniLM-L6-v2`). The retrieved regulatory language and matching typologies are formatted into the prompt context.

**6. Narrative generation.**
`llm/prompts.py` assembles the system and user prompts from the KYC data, features, detected patterns, and retrieved regulatory context. `llm/chains.py` runs the SAR generation chain (LangChain `LLMChain`) over the Ollama client (`llm/client.py`, streaming Mistral 7B), while `llm/langchain_callbacks.py` traces the call — capturing prompts, responses, timing, and retrieved documents. `llm/generator.py` coordinates generation and persists the result. If the LLM is unavailable, the request fails gracefully with a clear "LLM unavailable" response rather than producing an unverified narrative.

**7. Governance & audit.**
Every stage is recorded. The governance subsystem (`audit/logger.py`, `audit/callbacks.py`, `audit/models.py`) defines the audit event taxonomy (`AuditEventType`), writes structured events (including full prompt/response capture with integrity hashes), and can roll the events up into a per-case compliance summary. This produces an unbroken chain of custody from raw data to filed narrative.

**8. Human review.**
The analyst reviews the detected patterns and the generated draft in the UI (`frontend/components/audit_view.py`, with inline editing via `frontend/components/narrative_editor.py`), makes any edits, and formally approves. Edits and approvals are themselves logged.

**9. Export.**
On approval, `processing/pdf_generator.py` (via `backend/api/export.py`) renders a filing-ready SAR PDF — subject information, transaction summary, detected patterns, the narrative, a regulatory disclaimer, and a signature block — and the audit status transitions to `exported`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Uvicorn |
| ORM / DB | SQLAlchemy, PostgreSQL |
| Data processing | pandas, numpy |
| LLM orchestration | LangChain, langchain-community |
| Vector store | ChromaDB |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| LLM runtime | Ollama (Mistral 7B) |
| Frontend | Streamlit |
| PDF | fpdf2 |
| Testing | pytest, pytest-asyncio |

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Ollama with the Mistral model
- 8GB+ RAM (recommended for local LLM inference)

### 1. Install dependencies

```bash
cd SAR

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Set up PostgreSQL

Create a database and user matching the default connection string in `backend/config.py`:

```sql
CREATE USER saruser WITH PASSWORD 'sarpass';
CREATE DATABASE sar_db OWNER saruser;
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env if your database or Ollama settings differ from the defaults
```

### 4. Set up Ollama

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the Mistral model
ollama pull mistral

# Verify it is available
ollama list
```

### 5. Seed the database

```bash
python data_samples/seed_data.py
```

This populates PostgreSQL with sample customers and realistic transaction histories exhibiting a range of suspicious patterns.

### 6. Run the application

**Terminal 1 — Backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
streamlit run frontend/app.py
```

**Access:**
- Frontend: http://localhost:8501
- API docs (Swagger): http://localhost:8000/docs

## Usage Guide

### 1. Dashboard

The dashboard lists all pre-loaded customers with portfolio metrics and a risk-rating filter. The sidebar shows backend and LLM health at a glance.

### 2. Review a customer

Select a customer to view their KYC profile (account type, occupation, country, risk rating, PEP / sanctions flags) and full transaction history.

### 3. Start an audit

Click **Start Audit**. The system extracts features, detects suspicious patterns, retrieves regulatory context, and generates a SAR narrative — all in one orchestrated step. (The local LLM must be running; if it is unavailable the app surfaces a clear "LLM unavailable" message.)

### 4. Review patterns & narrative

Inspect the detected patterns (with confidence and severity), the extracted features, and the generated narrative.

### 5. Edit & approve

Refine the narrative inline, save drafts as needed, then **Approve** to finalize it for filing.

### 6. Export

Export the approved SAR as a formatted PDF.

### 7. Audit trail

Open the audit trail for any case to see every event — timestamps, feature/pattern summaries, and the complete LLM prompt/response — for compliance review.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service metadata |
| `/health` | GET | Backend + Ollama availability |
| `/api/customers` | GET | List customers (optional `risk_rating` filter) |
| `/api/customers/{id}` | GET | Customer profile with transactions |
| `/api/customers/{id}/audit` | POST | Start an audit — runs the full analysis + generation pipeline |
| `/api/audits` | GET | List audits (optional `status` filter) |
| `/api/audits/{id}` | GET | Audit details (features, patterns, narrative) |
| `/api/audits/{id}/edit` | POST | Save an edited narrative |
| `/api/audits/{id}/approve` | POST | Approve and finalize the narrative |
| `/api/audits/{id}/export/pdf` | GET | Export the audit as a PDF |
| `/api/audits/{id}/logs` | GET | Retrieve the full audit trail for a case |

## Data Model

The system is backed by four PostgreSQL tables (`backend/models.py`):

| Table | Purpose |
|-------|---------|
| `customers` | Pre-loaded customer / KYC records (name, account, country, occupation, risk rating, PEP & sanctions flags) |
| `transactions` | Transaction history per customer (date, amount, type, counterparty, country) |
| `audits` | One record per audit run — extracted features, detected patterns, and the generated / edited / final narrative |
| `audit_logs` | Immutable audit trail — event type, timestamp, details, and full LLM prompt/response capture for compliance |

## RAG Knowledge Base

The `prompts/` directory holds the regulatory knowledge base that grounds narrative generation. At startup its documents are chunked, embedded, and loaded into ChromaDB; relevant passages are retrieved during generation.

| File | Contents |
|------|----------|
| `prompts/aml_typologies/common_patterns.txt` | Money-laundering typologies with red flags and suggested narrative language |
| `prompts/regulatory_phrases/fincen_language.txt` | FinCEN-aligned regulatory phrasing |
| `prompts/sar_templates/standard_sar.txt` | Standard SAR narrative structure and writing guidelines |

## Configuration

Environment variables (or `.env` file), read by `backend/config.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://saruser:sarpass@localhost:5432/sar_db` | PostgreSQL connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `mistral` | LLM model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer embedding model |

Detection thresholds are also configurable in `backend/config.py`, including the CTR structuring threshold (`$10,000`), the velocity-spike multiplier (`3.0×`), the round-amount threshold, and the rapid-movement window (`24h`).

## Running Tests

```bash
# Run the full suite
pytest tests/ -v

# Run a specific test file
pytest tests/test_patterns.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

The suite covers the API (`tests/test_api.py`), feature extraction (`tests/test_features.py`), pattern detection (`tests/test_patterns.py`), and the RAG subsystem (`tests/test_rag.py`).

## Project Structure

```
SAR/
├── backend/
│   ├── main.py                 # FastAPI entry point (startup, CORS, health)
│   ├── config.py               # Settings & thresholds (env-driven)
│   ├── database.py             # PostgreSQL engine & session management
│   ├── models.py               # ORM tables & Pydantic schemas
│   ├── api/
│   │   ├── routes.py           # API endpoints & audit orchestration
│   │   └── export.py           # PDF / JSON export handlers
│   ├── processing/
│   │   ├── validators.py       # Ingestion schema validation
│   │   ├── normalizer.py       # Data normalization
│   │   ├── features.py         # Feature extraction engine
│   │   └── pdf_generator.py    # SAR PDF generation
│   ├── patterns/
│   │   ├── detector.py         # Pattern detection rules
│   │   ├── rules.py            # Thresholds, jurisdictions, typologies
│   │   └── models.py           # Pattern models & risk scoring
│   ├── rag/
│   │   ├── embeddings.py       # Embedding generation & chunking
│   │   ├── vectorstore.py      # ChromaDB operations
│   │   └── retriever.py        # Regulatory context retrieval
│   ├── llm/
│   │   ├── client.py           # Ollama client (streaming)
│   │   ├── chains.py           # LangChain SAR generation chain
│   │   ├── prompts.py          # Prompt assembly
│   │   ├── generator.py        # Narrative generation orchestrator
│   │   └── langchain_callbacks.py  # LLM tracing callbacks
│   └── audit/
│       ├── logger.py           # Audit event logging
│       ├── models.py           # Audit taxonomy & compliance schemas
│       └── callbacks.py        # LangChain audit callbacks
├── frontend/
│   ├── app.py                  # Streamlit main app
│   ├── components/
│   │   ├── customer_list.py    # Dashboard customer list & metrics
│   │   ├── customer_view.py    # Customer profile & transactions
│   │   ├── case_view.py        # Case detail view
│   │   ├── audit_view.py       # Audit review, edit & export
│   │   ├── audit_viewer.py     # Audit-trail & compliance views
│   │   └── narrative_editor.py # Inline narrative editor
│   └── utils/
│       └── api_client.py       # Backend API client
├── prompts/                    # RAG regulatory knowledge base
├── data_samples/
│   ├── seed_data.py            # Seed PostgreSQL with sample data
│   ├── sample_transactions.csv # Example transactions
│   └── sample_kyc.json         # Example KYC record
├── tests/                      # Test suite
├── vector_store/               # ChromaDB persistence (generated at runtime)
├── requirements.txt
├── .env.example
└── README.md
```

## Disclaimer

This tool is designed to assist compliance professionals. All generated narratives should be reviewed by qualified personnel before submission. The system does not make determinations about criminal activity. Provided for educational and demonstration purposes.
