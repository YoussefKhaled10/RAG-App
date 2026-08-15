<div align="center">

# NexMind AI
### Enterprise Multi-Tenant Hybrid RAG & Runtime Database Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_pgvector-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Celery](https://img.shields.io/badge/Celery-Distributed_Tasks-37814A?style=flat&logo=celery&logoColor=white)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*An enterprise-ready AI orchestration platform unifying unstructured document intelligence through Hybrid RAG and structured external database access with strict multi-tenancy, granular RBAC, dynamic schema discovery, and data masking.*

</div>

---

## 📖 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Key Features](#-key-features-phases-1--10)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation & Getting Started](#-installation--getting-started)
- [API Endpoints Summary](#-api-endpoints-summary)
- [Roadmap Status](#-roadmap-status)
- [License](#-license)

---

## 🏛 Architecture Overview

**NexMind AI** connects private enterprise documents with runtime enterprise databases. The platform provides a production-oriented backend built with **FastAPI**, an asynchronous **SQLAlchemy** engine, distributed worker queues through **Celery and RabbitMQ**, and an interactive **Streamlit** dashboard.

```text
                   ┌──────────────────────────────────────────────┐
                   │             Web Dashboard Layer              │
                   │           (Streamlit Application)            │
                   └──────────────────────┬───────────────────────┘
                                          │  REST API / JWT
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │             FastAPI Backend Layer            │
                   │      (Multi-Tenant Router & Security)        │
                   └──────┬──────────────────────┬────────────┬───┘
                          │                      │            │
            ┌─────────────┴────────┐   ┌─────────┴─────────┐  │
            │ Hybrid RAG Pipeline  │   │  DB Intelligence  │  │
            │ ──────────────────── │   │ ───────────────── │  │
            │ • Semantic (Vector)  │   │ • Schema Discovery│  │
            │ • Full-Text & Trigram│   │ • Metadata Cache  │  │
            │ • RRF & Deduplication│   │ • Column Masking  │  │
            │ • Cohere Reranking   │   │ • Row Policies    │  │
            └─────────────┬────────┘   └─────────┬─────────┘  │
                          │                      │            │
                          ▼                      ▼            ▼
                   ┌──────────────┐       ┌──────────────┐ ┌──────────────┐
                   │ PostgreSQL   │       │ External     │ │ Celery Queue │
                   │  + pgvector  │       │ Databases    │ │  + RabbitMQ  │
                   └──────────────┘       └──────────────┘ └──────────────┘
```

---

## 🚀 Key Features (Phases 1 — 10)

### 🏢 1. Strict Multi-Tenancy & Workspace Isolation

- Complete logical data isolation across tenants using `tenant_id`.
- Isolated workspaces, projects, assets, vector collections, and database connections.
- Cross-tenant access rejection at the database and dependency levels.

### 🔐 2. Enterprise Authentication & Role-Based Access Control

- Secure JWT authentication with access and refresh tokens.
- Tenant Admin auto-provisioning during workspace registration.
- Built-in system roles: `Tenant Admin`, `Document Manager`, and `Viewer`.
- Protected system roles with support for custom role creation and assignment.

### 📁 3. Scalable File & Document Ingestion

- Support for **PDF, TXT, DOCX, CSV, XLSX, and XLS**.
- Content-type validation, size limits, and filename sanitization.
- SHA-256 asset checksums to prevent redundant storage.

### ⚙️ 4. Distributed Processing & Idempotency

- Asynchronous file chunking and indexing through **Celery and RabbitMQ**.
- Task-level idempotency using hashed task arguments to eliminate duplicate workloads.
- Task monitoring and asset lifecycle tracking: `uploaded` → `processing` → `indexed` or `failed`.

### 🧠 5. Multi-Provider Embedding & Vector Storage

- Modular provider architecture supporting **OpenAI**, **Cohere**, and **Ollama**.
- Swappable vector backends: **PostgreSQL with pgvector** and **Qdrant**.
- Cosine similarity, HNSW indexing, and isolated vector collections.

### 🔍 6. Advanced Hybrid Document Search & RAG

- Tri-hybrid retrieval combining dense semantic search, PostgreSQL full-text search, and trigram similarity.
- Reciprocal Rank Fusion to merge semantic and keyword result rankings.
- Cohere reranking for improved contextual precision.
- LLM query rewriting for better retrieval.
- Grounded citations with source files, chunk order, page numbers, sheets, and row metadata.

### 🔌 7. Secure Runtime Database Connections

- Encrypted credential storage using Fernet symmetric encryption.
- Live database probing and connection health verification.
- Read-only transaction mode and SSL configuration support.
- Tenant-scoped CRUD operations for runtime PostgreSQL connections.

### 🗺️ 8. Live Schema Discovery & Metadata Caching

- Live schema introspection without reading or storing application rows.
- Discovery of schemas, tables, views, columns, data types, primary keys, foreign keys, and relationships.
- Canonical JSON metadata caching with SHA-256 change detection.
- Schema discovery, synchronization, and cached metadata endpoints.

### 🛡️ 9. Granular Database Security & Data Masking

- Per-table and per-column capabilities: `can_read`, `can_filter`, and `can_aggregate`.
- Dynamic masking modes:
  - `full`: complete anonymization.
  - `partial`: preserves edge characters.
  - `email`: masks the mailbox while preserving the domain.
  - `phone` and `last4`: retain the final four digits.
  - `hash`: returns an irreversible SHA-256 digest.
  - `unmasked`: requires explicit authorization.
- Row-level policies and context filters based on authenticated user and tenant values.

### 📊 10. Secure Query Engine & Dashboard

- Controller-enforced SQL construction with parameterized values.
- Permission-aware structured database queries.
- Interactive Streamlit dashboard with live metrics and action feedback.
- Administrative interfaces for projects, documents, users, roles, and database connections.

---

## 💻 Tech Stack

| Domain | Technology |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) with Python 3.10+ |
| **Data & ORM** | [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/) and [asyncpg](https://github.com/MagicStack/asyncpg) |
| **Primary Database** | [PostgreSQL 16](https://www.postgresql.org/) with `pgvector` and `pg_trgm` |
| **Vector Databases** | [pgvector](https://github.com/pgvector/pgvector) and [Qdrant](https://qdrant.tech/) |
| **Task Queue & Broker** | [Celery](https://docs.celeryq.dev/), [RabbitMQ](https://www.rabbitmq.com/), and [Redis](https://redis.io/) |
| **LLM & Embeddings** | [OpenAI](https://openai.com/), [Cohere](https://cohere.com/), and [Ollama](https://ollama.com/) |
| **Security & Auth** | [PyJWT](https://pyjwt.readthedocs.io/), password hashing, and [Cryptography](https://cryptography.io/) with Fernet |
| **Frontend** | [Streamlit](https://streamlit.io/) |
| **Containerization** | [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) |

---

## 📁 Project Structure

```text
├── alembic/                       # Database schema migrations
├── frontend/
│   ├── requirements.txt
│   └── streamlit_app.py           # Streamlit web dashboard
├── src/
│   ├── controllers/               # Business logic and orchestration
│   │   ├── AuthController.py
│   │   ├── DataController.py
│   │   ├── DatabaseConnectionController.py
│   │   ├── DatabasePermissionController.py
│   │   ├── NLPController.py
│   │   ├── ProcessController.py
│   │   └── ProjectController.py
│   ├── core/                      # Runtime encryption services
│   │   └── credentials_encryption.py
│   ├── dependencies/              # FastAPI auth and role dependencies
│   │   └── auth.py
│   ├── helpers/                   # Application settings
│   │   └── config.py
│   ├── models/                    # SQLAlchemy logic models and ORM exports
│   │   ├── AssetModel.py
│   │   ├── ChunkModel.py
│   │   ├── DatabaseConnectionModel.py
│   │   ├── DatabasePermissionModel.py
│   │   ├── DatabaseSchemaCacheModel.py
│   │   ├── ProjectModel.py
│   │   ├── RoleModel.py
│   │   ├── TenantModel.py
│   │   └── UserModel.py
│   ├── routes/                    # API route definitions
│   │   ├── auth.py
│   │   ├── database_connections.py
│   │   ├── files.py
│   │   ├── projects.py
│   │   ├── roles.py
│   │   ├── search.py
│   │   ├── tasks.py
│   │   └── users.py
│   ├── schemas/                   # Pydantic request and response models
│   ├── services/                  # Tenant onboarding and services
│   │   └── registration.py
│   ├── stores/                    # Pluggable provider implementations
│   │   ├── databases/             # Runtime database adapters
│   │   ├── llm/                   # LLM and embedding providers
│   │   └── vectordb/              # pgvector and Qdrant adapters
│   ├── tasks/                     # Celery background workers
│   │   ├── celery_app.py
│   │   └── file_processing.py
│   ├── utils/                     # Metrics, rerankers, and query utilities
│   │   ├── cohere_reranker.py
│   │   ├── idempotency_manager.py
│   │   ├── llm_error_middleware.py
│   │   ├── metrics.py
│   │   ├── query_rewriter.py
│   │   └── result_deduplicator.py
│   └── main.py                    # FastAPI application entry point
├── docker-compose.yaml            # Multi-service stack definition
├── Dockerfile                     # API container build
└── requirements.txt               # Project dependencies
```

---

## ⚡ Installation & Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/nexmind-ai.git
cd nexmind-ai
```

### 2. Configure the Environment

Copy the example environment files and replace placeholder values with local development secrets:

```bash
cp src/.env.example src/.env
cp docker/.env.example docker/.env
```

Never commit real `.env` files, encryption keys, passwords, or API keys.

### 3. Run with Docker Compose

Launch PostgreSQL, Redis, RabbitMQ, Celery, FastAPI, and Streamlit:

```bash
docker compose up pgvector redis rabbitmq celery_worker
```

### 4. Run Locally for Development

#### A. Create a Python Virtual Environment

```bash
python -m venv venv
```

On Windows:

```bash
venv\Scripts\activate
```

On Linux or macOS:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r src/requirements.txt
pip install -r frontend/requirements.txt
```

#### B. Run Database Migrations

```bash
alembic upgrade head
```

#### C. Start the Celery Worker

Run the worker from the directory expected by the project import paths:

```bash
celery -A tasks.celery_app.celery_app worker --loglevel=info --pool=solo
```

#### D. Start the FastAPI Backend

From the `src` directory:

```bash
uvicorn main:app --reload --port 8000
```

#### E. Start the Streamlit Dashboard

From the project root:

```bash
streamlit run frontend/streamlit_app.py --server.port 8501
```

---

## 🌐 API Endpoints Summary

| Method | Endpoint | Description | Required Access |
|---|---|---|---|
| `POST` | `/api/v1/auth/register-tenant` | Register a new tenant and administrator | Public |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT tokens | Public |
| `POST` | `/api/v1/auth/refresh` | Refresh an access token | Public |
| `GET` | `/api/v1/auth/me` | Fetch the current user profile | Authenticated |
| `POST` | `/api/v1/projects` | Create a knowledge project | Tenant Admin |
| `GET` | `/api/v1/projects` | List tenant projects | Authenticated |
| `PATCH` | `/api/v1/projects/{project_id}` | Update a project | Tenant Admin |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete a project | Tenant Admin |
| `POST` | `/api/v1/projects/{project_id}/files` | Upload and queue file indexing | Document Manager or Admin |
| `POST` | `/api/v1/projects/{project_id}/search` | Execute hybrid document search | Authenticated |
| `POST` | `/api/v1/projects/{project_id}/ask` | Generate a grounded RAG answer | Authenticated |
| `POST` | `/api/v1/database-connections` | Register an external PostgreSQL connection | Tenant Admin |
| `POST` | `/api/v1/database-connections/{connection_id}/test` | Test connectivity, SSL, and read-only mode | Tenant Admin |
| `POST` | `/api/v1/database-connections/{connection_id}/discover-schema` | Discover live database metadata | Tenant Admin |
| `POST` | `/api/v1/database-connections/{connection_id}/sync-schema` | Discover and cache database metadata | Tenant Admin |
| `GET` | `/api/v1/database-connections/{connection_id}/schema` | Read cached schema metadata | Authenticated |
| `PUT` | `/api/v1/database-connections/{connection_id}/permissions/roles/{role_id}` | Publish table, column, masking, and row policies | Tenant Admin |
| `POST` | `/api/v1/database-connections/{connection_id}/query` | Execute a permission-enforced structured query | Authenticated |

Interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## 🗺️ Roadmap Status

- [x] **Phase 1:** Multi-Tenancy Foundation
- [x] **Phase 2:** Authentication & JWT
- [x] **Phase 3:** Users, Roles & General RBAC Permissions
- [x] **Phase 4:** Projects & File Management
- [x] **Phase 5:** Document Processing & Celery Idempotency
- [x] **Phase 6:** Embeddings & Vector Database with pgvector or Qdrant
- [x] **Phase 7:** Document Search & Tri-Hybrid RAG Pipeline
- [x] **Phase 8:** Runtime Database Connections & Encryption
- [x] **Phase 9:** Live Schema Discovery & Metadata Caching
- [x] **Phase 10:** Table, Column & Row Permissions with Data Masking
- [ ] **Phase 11:** Text-to-SQL Security & Execution Guardrails *(In Progress)*
- [ ] **Phase 12:** SQL and Document Hybrid Agent Routing
- [ ] **Phase 13:** Persistent Conversations & Citation History
- [ ] **Phase 14:** Audit Logs & Compliance Traceability
- [ ] **Phase 15:** SSE Streaming Chat Endpoint
- [ ] **Phase 16:** Automated PyTest Suite for Unit, Security, and Isolation Testing
- [ ] **Phase 17:** Production Hardening & Complete Deployment

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
