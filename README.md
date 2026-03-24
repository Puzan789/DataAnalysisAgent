# Data Analysis Agent

An AI-powered data analysis agent that lets you interact with your PostgreSQL databases through natural language. Ask questions in plain English, and the agent generates SQL, executes it, and returns human-readable results -- all through a modern chat interface.

## Features

### Multi-Agent Chat System
- **Intelligent Query Routing** -- A router agent analyzes your question and decides whether to use the SQL agent (for data queries) or the general agent (for analysis and conversation)
- **Agentic SQL Generation** -- Retrieves relevant database schema via vector search, then generates safe, read-only SQL queries
- **SQL Execution Pipeline** -- Executes generated queries on PostgreSQL and returns structured results
- **Streaming Responses** -- Real-time Server-Sent Events (SSE) for token-by-token response streaming

### Vector Store Integration (Qdrant)
- Automatically indexes your database schema (tables, columns, relationships, example queries) into Qdrant
- Semantic search retrieves only the relevant schema context when generating SQL, keeping prompts efficient
- Three collections: `table_descriptions`, `db_schema`, `companies`

### Database Exploration Dashboard
- Browse database tables, view schemas, and inspect data with pagination
- See foreign key relationships between tables
- View vector store statistics (points, vectors, collection info)
- Full database overview with table counts, row counts, and data sizes

### Chat History & Sessions
- MongoDB-backed conversation persistence
- Multiple chat threads per user
- LangGraph state checkpoints for reliable agent execution

### Authentication
- JWT-based authentication with Bearer tokens
- User registration and login
- Session management

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | Web framework & API |
| **LangGraph + LangChain** | Multi-agent orchestration |
| **OpenAI** | LLM (GPT-4o) & embeddings |
| **PostgreSQL** | Target database for analysis |
| **MongoDB** | Chat history, sessions, checkpoints |
| **Qdrant** | Vector store for schema retrieval |
| **SQLAlchemy** | Async PostgreSQL driver |
| **Pydantic** | Data validation |

### Frontend
| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool |
| **Tailwind CSS** | Styling |
| **react-markdown** | Markdown rendering in chat |
| **Lucide React** | Icons |

### Note: I vibecoded the frontend

## Project Structure

```
.
├── main.py                        # FastAPI entry point
├── pyproject.toml                 # Python dependencies (managed with uv)
├── Dockerfile                     # Container configuration
├── docker-compose.yml             # Services: backend, mongodb, qdrant
├── .env.sample                    # Environment template
├── start.sh                       # Dev startup script
│
├── src/
│   ├── agents/                    # Multi-agent routing
│   │   ├── router_agent.py        # Routes queries to SQL or general agent
│   │   ├── sql_agent.py           # SQL generation & execution agent
│   │   ├── general_agent.py       # General Q&A agent
│   │   ├── history.py             # Message history trimming
│   │   └── types.py               # Agent state definitions
│   │
│   ├── api/v1/                    # API endpoints
│   │   ├── chat.py                # Chat streaming endpoint
│   │   ├── auth.py                # Signup / login
│   │   ├── databaseinfo.py        # Database exploration endpoints
│   │   ├── vectordb.py            # Vector store management
│   │   └── message.py             # Chat history endpoints
│   │
│   ├── sqlagent/                  # SQL query generation pipeline
│   │   ├── embeddings/
│   │   │   ├── vectorstore.py     # Qdrant wrapper
│   │   │   └── embedder.py        # Embedding generation
│   │   ├── indexer/
│   │   │   └── schema_indexer.py  # Index DB schema into vector store
│   │   ├── ingestion/
│   │   │   ├── schema_extractor.py # Extract schema from PostgreSQL
│   │   │   └── chunk_generator.py  # Create chunks for indexing
│   │   ├── nodes/
│   │   │   ├── sql_generation.py  # Generate SQL from natural language
│   │   │   └── sql_execution.py   # Execute SQL on PostgreSQL
│   │   └── retrieval/
│   │       └── retriever.py       # Vector search for relevant schema
│   │
│   ├── graph/
│   │   └── builder.py            # LangGraph workflow compilation
│   │
│   ├── database/                  # Database connections
│   │   ├── state.py               # DatabaseState container
│   │   ├── models.py              # User, Session, Message models
│   │   ├── postgres.py            # PostgreSQL connection
│   │   ├── mongo.py               # MongoDB connection
│   │   └── dependencies.py        # FastAPI dependencies
│   │
│   ├── services/                  # Business logic
│   │   ├── auth_service.py        # User registration / login
│   │   ├── message_service.py     # Chat session management
│   │   └── database_service.py    # DB exploration queries
│   │
│   ├── core/                      # Core utilities
│   │   ├── container.py           # ServiceContainer (dependency injection)
│   │   ├── utils.py               # get_llm(), get_embeddings()
│   │   ├── auth.py                # JWT token handling
│   │   ├── exception.py           # Custom exceptions
│   │   └── responses.py           # API response wrapper
│   │
│   ├── prompts/
│   │   └── _prompts.py            # LLM prompt templates
│   │
│   ├── schemas/                   # Pydantic request/response models
│   │   ├── llm_response_schemas.py
│   │   └── tool_input_schemas.py
│   │
│   └── config.py                  # Application settings
│
└── frontend/
    ├── package.json
    └── src/
        ├── App.tsx                # Main app component
        ├── components/
        │   ├── ChatInput.tsx      # Chat input box
        │   ├── ChatMessage.tsx    # Message display with markdown
        │   ├── Dashboard.tsx      # Database explorer & vector stats
        │   ├── AuthForm.tsx       # Login / signup form
        │   ├── Sidebar.tsx        # Navigation & chat threads
        │   └── EmptyState.tsx     # Initial state with prompts
        ├── hooks/
        │   ├── useChat.ts         # Chat state management
        │   └── useAuth.ts         # Auth state management
        ├── lib/
        │   ├── api.ts             # API client
        │   └── constants.ts       # Config constants
        └── types/
            └── index.ts           # TypeScript interfaces
```

## Installation

### Prerequisites

- Python 3.13+
- Node.js 16+
- Docker & Docker Compose
- An OpenAI API key
- A PostgreSQL database you want to analyze

### 1. Clone the repository

```bash
git clone https://github.com/Puzan789/DataAnalysisAgent.git
cd DataAnalysisAgent
```

### 2. Configure environment variables

```bash
cp .env.sample .env
```

Edit `.env` and fill in the required values:

```env
# Required
OPENAI_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small

# PostgreSQL (the database you want to analyze)
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=host.docker.internal   # use your DB host
POSTGRES_PORT=5432
POSTGRES_DB=your-database

# Auth
AUTH_SECRET=your-secret-key

# These have sensible defaults in .env.sample
# QDRANT_URL, MONGO_DB_URI, MONGO_DB_NAME, CORS_ORIGINS, etc.
```

### 3a. Run with Docker Compose (recommended)

```bash
docker-compose up -d
```

This starts three services:
| Service | Port |
|---|---|
| Backend (FastAPI) | `7000` |
| MongoDB | `27017` |
| Qdrant | `6333` |

### 3b. Run manually (development)

**Backend:**

```bash


# Install dependencies
uv sync

# Start the backend
uvicorn main:app --reload --host 0.0.0.0 --port 7000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server starts at `http://localhost:5173`.

> **Note:** You'll also need MongoDB and Qdrant running locally. You can start just those with:
> ```bash
> docker-compose up -d mongodb qdrant
> ```

### 4. Initialize the vector store

After the backend is running, index your database schema into Qdrant:

```bash
curl -X POST http://localhost:7000/api/v1/vector/initialize_schema
```

This extracts your PostgreSQL schema and creates vector embeddings for semantic search during SQL generation.

### 5. Verify

```bash
# Health check
curl http://localhost:7000/health

# Database connectivity
curl http://localhost:7000/health/db
```

## Usage

1. Open the app in your browser (`http://localhost:5173` in dev, or `http://localhost:7000` with Docker)
2. **Sign up** for an account using the auth form
3. **Ask questions** about your data in natural language:
   - *"How many users signed up last month?"*
   - *"Show me the top 10 products by revenue"*
   - *"What's the average order value by country?"*
   - *"List all tables in the database"*
4. The agent automatically:
   - Routes your query to the right agent (SQL or general)
   - Retrieves relevant schema context from the vector store
   - Generates and executes a safe, read-only SQL query
   - Returns results with a natural language explanation
5. Use the **Dashboard** tab to browse tables, view schemas, inspect data, and see vector store stats

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/signup` | Register a new user |
| `POST` | `/api/v1/auth/login` | Login |
| `GET` | `/api/v1/auth/me` | Get current user |
| `POST` | `/api/v1/graph/stream/graph` | Stream chat response (SSE) |
| `GET` | `/api/v1/threads/{user_id}` | List chat threads |
| `GET` | `/api/v1/messages/{thread_id}` | Get messages in a thread |
| `DELETE` | `/api/v1/delete_thread/{thread_id}` | Delete a thread |
| `PUT` | `/api/v1/{thread_id}/deactivate` | Deactivate a session |
| `GET` | `/api/v1/db/overview` | Database overview stats |
| `GET` | `/api/v1/db/tables` | List all tables |
| `GET` | `/api/v1/db/tables/{table}/schema` | Get table schema |
| `GET` | `/api/v1/db/tables/{table}/data` | Get paginated table data |
| `GET` | `/api/v1/db/relationships` | Get foreign key relationships |
| `POST` | `/api/v1/vector/initialize_schema` | Index schema into vector store |
| `GET` | `/api/v1/vector/stats` | Vector store statistics |
| `GET` | `/health` | Health check |
| `GET` | `/health/db` | Database health check |

## How It Works

```
User Query
    │
    ▼
┌──────────────┐
│ Router Agent │ ── Analyzes intent using LLM
└──────┬───────┘
       │
  ┌────┴────┐
  ▼         ▼
┌─────┐  ┌─────────┐
│ SQL │  │ General │
│Agent│  │  Agent  │
└──┬──┘  └────┬────┘
   │          │
   ▼          │
┌────────────┐│
│ 1. Retrieve││
│    schema  ││
│    (Qdrant)││
│ 2. Generate││
│    SQL     ││
│ 3. Execute ││
│    query   ││
│    (PG)    ││
└─────┬──────┘│
      │       │
      ▼       ▼
   ┌────────────┐
   │  Response  │
   │  (Streamed │
   │   via SSE) │
   └────────────┘
```

## TODO

- [ ] **Interactive Data Visualizations** -- Agent-generated charts rendered in the chat UI
- [ ] **Smart Chart Selection** -- Agent automatically picks the best chart type based on the SQL results and query intent
- [ ] **Chart Interactivity** -- Hover tooltips, click to drill down, zoom, and export (PNG/SVG)
- [ ] **Dashboard Pinning** -- Save generated charts to a personal dashboard for quick reference




