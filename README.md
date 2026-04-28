# document-rag-prototype

A document retrieval and question-answering prototype evolving from a monolithic notebook-based pipeline into a service-oriented backend with FastAPI, Docker, Docker Compose, and PostgreSQL.

## Overview

This project started as a retrieval-first RAG prototype for TXT and PDF documents, with the main focus on practical document ingestion problems such as noisy PDF extraction, uneven structure, weak chunk boundaries, and imperfect retrieval quality.

The project has now moved beyond the earlier monolithic baseline and is being restructured into a more realistic backend architecture. The current direction includes:

- a FastAPI service layer
- Dockerized application runtime
- Docker Compose multi-service setup
- PostgreSQL as a separate service container
- environment-based database configuration
- the beginning of a lighter API vs heavier retrieval boundary

This repository therefore shows both:
- the original retrieval prototype work
- the ongoing architectural refactor toward a more production-style design

## Why this project exists

Document-based QA becomes much harder when the input is not a clean benchmark example but a real file with messy structure. Reports, theses, slide decks, and mixed-format PDFs often contain:

- repeated headers and footers
- fragmented lines
- front matter
- captions and navigation text
- broken reading order
- different text behavior across pages

This project was built to work through those practical issues step by step, rather than pretending retrieval quality depends only on model choice.

At the same time, the project also became a learning ground for backend engineering decisions such as:
- how to expose retrieval through an API
- how to containerize services
- how to separate application and database responsibilities
- how to evolve from a single-process prototype to a multi-service architecture

## Current architecture direction

The repository is currently in transition from a monolithic retrieval prototype toward a service-based design.

### Current service structure

- **API service**: FastAPI application
- **Database service**: PostgreSQL container
- **Orchestration**: Docker Compose

### Current proven endpoints

- `/` → basic API root
- `/health` → confirms API is running
- `/db-check` → confirms the Python app can connect to PostgreSQL and run a real SQL query

### Current architectural status

The infrastructure side is already working:

- API container starts successfully
- PostgreSQL container starts successfully
- Docker Compose networking works
- API receives `DATABASE_URL`
- Python connects to PostgreSQL successfully through `psycopg`
- container-to-container DB communication is proven

The heavier `/ask` retrieval path is still being separated from the ML-heavy stack. This is an intentional design step: the API is being made lighter, while heavier retrieval and embedding logic are being isolated more carefully.

## Project evolution

### Phase 1 — Monolithic retrieval prototype

The earlier version focused on:

- TXT and PDF ingestion
- PDF text extraction
- chunking
- embedding-based retrieval
- reranking
- grounded answer generation

That version was useful for proving the retrieval idea, but it mixed too many responsibilities into one flow.

### Phase 2 — API introduction

A FastAPI layer was introduced so the prototype could be exposed through endpoints rather than only notebook/manual flow.

### Phase 3 — Dockerized API

The API was packaged into a Docker image and run as a container. This proved that the service could run in a reproducible environment.

### Phase 4 — Compose + Postgres

The project moved to a two-service setup:

- API container
- PostgreSQL container

At this stage, the project successfully established a real app-to-database connection using:

- Docker Compose networking
- environment-based DB configuration
- `psycopg`
- a `/db-check` route with a real SQL query

### Current design lesson

A major lesson from the refactor was that the API image should not automatically carry the full heavy ML stack. The repository is therefore being reorganized so that:

- API/runtime dependencies stay lighter
- heavier ML dependencies are separated more clearly
- future worker-style processing can be introduced more cleanly

## Current repository structure

```text
document-rag-prototype/
│
├── app/
│   └── api/
│       └── main.py
│
├── src/
│   └── document_rag_prototype/
│       ├── __init__.py
│       ├── chunker.py
│       ├── config.py
│       ├── content_profiler.py
│       ├── embedder.py
│       ├── generator.py
│       ├── loader.py
│       ├── pipeline.py
│       ├── query_analyzer.py
│       ├── reranker.py
│       └── search.py
│
├── notebooks/
│   └── rag_prototype.ipynb
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
