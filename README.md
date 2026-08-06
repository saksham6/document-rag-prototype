# Document RAG Prototype

A database-backed Retrieval-Augmented Generation system for uploading documents, extracting and chunking their content, storing embeddings in PostgreSQL with pgvector, retrieving relevant chunks, and generating answers with source references.

The project was built as a practical Applied AI and ML engineering project. It combines document processing, semantic retrieval, database design, API development, Docker, and large language model integration in one end-to-end workflow.

## Current status

The repository has been restructured into separate API, database, service, schema, and configuration layers.

The active application uses:

- FastAPI for the API
- PostgreSQL for persistent storage
- pgvector for vector similarity search
- SQLAlchemy and asyncpg for asynchronous database access
- Alembic for database migrations
- OpenAI embeddings for document chunks and user queries
- OpenAI generation for answers based on retrieved context
- Docker Compose for the local API and database environment
- A browser-based user interface mounted at `/ui`

The older local in-memory RAG pipeline has been removed. The active workflow is now based on PostgreSQL and pgvector.

The refactored application imports successfully. A complete Docker workflow test is the next verification step.

## What the system does

The application supports the following workflow:

1. Create a knowledge base.
2. Upload a PDF or TXT document.
3. Store document metadata in PostgreSQL.
4. Extract text from the uploaded document.
5. Split the extracted text into overlapping chunks.
6. Store the chunks and their metadata in PostgreSQL.
7. Generate embeddings for the chunks.
8. Store the embedding vectors using pgvector.
9. Embed a user question.
10. Retrieve the most relevant chunks using vector similarity.
11. Send the retrieved context and question to the language model.
12. Return an answer together with document and chunk source information.

## Architecture

```text
Browser UI
    |
    v
FastAPI application
    |
    +-- Knowledge-base routes
    +-- Document routes
    +-- Ingestion routes
    +-- RAG search route
    +-- Health routes
    |
    v
Service layer
    |
    +-- Document extraction and chunking
    +-- Embedding generation
    +-- Vector retrieval
    +-- Answer generation
    |
    v
SQLAlchemy and asyncpg
    |
    v
PostgreSQL with pgvector
```

## Repository structure

```text
document-rag-prototype/
├── app/
│   └── api/
│       └── main.py
│
├── src/
│   └── document_rag_prototype/
│       ├── api/
│       │   ├── routes/
│       │   │   ├── health.py
│       │   │   ├── knowledge_bases.py
│       │   │   ├── documents.py
│       │   │   ├── ingestion.py
│       │   │   └── rag.py
│       │   └── schemas/
│       │       └── models.py
│       │
│       ├── core/
│       │   └── config.py
│       │
│       ├── db/
│       │   ├── models.py
│       │   └── session.py
│       │
│       └── services/
│           ├── ingestion_service.py
│           ├── embedding_service.py
│           ├── retrieval_service.py
│           └── generation_service.py
│
├── alembic/
├── notebooks/
├── tests/
├── static/
│   └── index.html
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

## Main components

### FastAPI entry point

`app/api/main.py` creates the FastAPI application, registers the routers, and mounts the browser interface.

The file contains application startup configuration only. Route logic is kept in separate route modules.

### API routes

`api/routes/health.py`

Contains basic application and database health endpoints.

`api/routes/knowledge_bases.py`

Handles knowledge-base creation and listing.

`api/routes/documents.py`

Handles document upload, manual document creation, document listing, and chunk-management endpoints.

`api/routes/ingestion.py`

Handles document extraction, chunk creation, and embedding generation.

`api/routes/rag.py`

Handles database-backed semantic retrieval and answer generation.

### Schemas

`api/schemas/models.py` contains the Pydantic request and response models used by the API.

These schemas validate incoming requests and define the structure of returned responses.

### Database layer

`db/models.py` defines the SQLAlchemy database models:

- `KnowledgeBase`
- `Document`
- `Chunk`

`db/session.py` creates the asynchronous SQLAlchemy engine and database sessions.

### Service layer

`services/ingestion_service.py`

Extracts text from PDF and TXT files and splits the extracted text into chunks.

`services/embedding_service.py`

Creates OpenAI embeddings for document chunks and user queries.

`services/retrieval_service.py`

Runs metadata-filtered pgvector similarity search and returns the nearest document chunks.

`services/generation_service.py`

Builds the prompt from the retrieved chunks and generates an answer grounded in that context.

## Database model

The main database relationship is:

```text
KnowledgeBase
    |
    | one-to-many
    v
Document
    |
    | one-to-many
    v
Chunk
```

### Knowledge base

A knowledge base groups related documents.

Example:

```text
Medical and Thesis Documents
```

### Document

A document stores metadata about an uploaded file, including:

- knowledge-base ID
- filename
- source type
- processing status
- creation time

### Chunk

A chunk stores:

- document ID
- chunk index
- extracted text
- page number
- embedding vector
- creation time

Embedding vectors are stored directly in PostgreSQL using pgvector.

## Document processing flow

### Upload

The upload endpoint:

- validates the knowledge base
- validates the filename and file extension
- saves the uploaded file
- creates a document record
- assigns the initial document status

Uploading does not automatically extract or embed the document.

### Ingestion

The ingestion endpoint:

- locates the uploaded file
- extracts text from the PDF or TXT document
- divides the text into chunks
- removes previously stored chunks for the document
- stores the new chunks
- updates the document status

### Embedding

The embedding endpoint:

- loads the stored chunks
- sends their text to the embedding model
- receives one vector for each chunk
- stores the vectors in PostgreSQL

### Retrieval and answer generation

The search endpoint:

- validates the question
- creates a query embedding
- optionally filters by knowledge base or document
- compares the query vector with stored chunk vectors
- retrieves the closest chunks
- sends the retrieved context to the language model
- returns the generated answer and source metadata

## API endpoints

### System endpoints

```text
GET /
GET /health
GET /db-check
```

### Knowledge-base endpoints

```text
POST /knowledge-bases
GET  /knowledge-bases
```

### Document endpoints

```text
POST /knowledge-bases/{knowledge_base_id}/documents/upload
POST /documents
GET  /documents
```

### Chunk endpoints

```text
POST /chunks
GET  /chunks
```

### Processing endpoints

```text
POST /documents/{document_id}/ingest
POST /documents/{document_id}/embed
```

### RAG endpoint

```text
POST /search
```

The `/search` endpoint performs both retrieval and answer generation.

Example request:

```json
{
  "query": "What is the conclusion of the report?",
  "knowledge_base_id": 1,
  "document_id": null,
  "top_k": 5
}
```

Example response structure:

```json
{
  "query": "What is the conclusion of the report?",
  "answer": "The report concludes that...",
  "sources": [
    {
      "chunk_id": 72,
      "document_id": 42,
      "filename": "Conclusion.pdf",
      "chunk_index": 2,
      "page_number": 2,
      "distance": 0.6914
    }
  ]
}
```

## Technology stack

### Application

- Python
- FastAPI
- Pydantic

### Database

- PostgreSQL
- pgvector
- SQLAlchemy
- asyncpg
- Alembic

### Document processing

- PyMuPDF
- TXT file processing
- overlapping text chunking

### AI integration

- OpenAI `text-embedding-3-small`
- OpenAI language model integration
- vector similarity retrieval
- grounded answer generation

### Development and delivery

- Docker
- Docker Compose
- Git
- uv
- pytest planned for automated tests

## Running the project with Docker

### Requirements

Install:

- Docker Desktop
- Git

An OpenAI API key is also required for embedding and answer generation.

### Clone the repository

```bash
git clone https://github.com/saksham6/document-rag-prototype.git
cd document-rag-prototype
```

### Environment variables

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
```

Database settings are defined through the Docker Compose configuration.

Do not commit the `.env` file.

### Start the containers

```bash
docker compose up --build
```

The API should be available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

Browser interface:

```text
http://localhost:8000/ui
```

Database access from the host machine uses the PostgreSQL port configured in `docker-compose.yml`.

### Stop the containers

```bash
docker compose down
```

To stop the containers without deleting their persistent data:

```bash
docker compose stop
```

## Database migrations

Alembic is used to manage database schema changes.

Apply all migrations:

```bash
alembic upgrade head
```

Create a new migration after changing the database models:

```bash
alembic revision --autogenerate -m "describe the schema change"
```

The project currently includes migrations for the knowledge-base, document, and chunk tables and the pgvector embedding column.

## Current limitations

The project is functional but still under active development.

Current limitations include:

- the complete refactored Docker workflow still needs final verification
- upload, ingestion, and embedding are separate operations
- document lifecycle states need further improvement
- duplicate upload handling is limited
- ingestion and embedding failure recovery needs improvement
- automated tests are not yet complete
- retrieval quality has not yet been measured on a fixed evaluation dataset
- answer groundedness and citation correctness are not yet evaluated systematically
- hybrid search and reranking are not part of the current database-backed workflow
- cloud deployment and CI/CD are not yet completed


## Planned work

The next project stages are:

1. Verify the complete Docker and browser workflow.
2. Document the final ingestion and query execution paths.
3. Create a representative RAG evaluation dataset.
4. Measure retrieval quality using Hit Rate at K and Mean Reciprocal Rank.
5. Record latency, token usage, and approximate cost.
6. Analyse retrieval and generation failures.
7. Run controlled chunk-size, overlap, and top-k experiments.
8. Add unit, integration, and end-to-end tests.
9. Add GitHub Actions for linting, tests, and Docker builds.
10. Improve lifecycle states, validation, rollback, and logging.
11. Evaluate groundedness, citation support, completeness, and refusal behaviour.
12. Deploy a controlled portfolio version using Azure services.

Advanced retrieval methods will be added only when evaluation results show a clear need.



