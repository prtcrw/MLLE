# MLLE

MLLE is a web application for exploring [MLLO](https://github.com/iofoundry/ontology/tree/mllo-dev) data through a Python/FastAPI backend and a Vite/React frontend.

Use this guide if you want to run MLLE locally.

## What You Need

Required:

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) for Python environment and dependency management
- Node.js and npm
- A SPARQL backend with MLLO data loaded

Choose one SPARQL backend:

- MOBI Server 3.0.0. See the [MOBI install guide](https://inovexcorp.github.io/mobi-docs/latest/index.html#installing_the_docker_image).
- ([GraphDB](https://graphdb.ontotext.com/)).

Optional:

- An LLM endpoint. This is only needed for natural-language query and chat workflows. You can run the rest of the app without it.

## Run MLLE Locally

### 1. Clone the repository

If you already have this repository, start from the repository root.

### 2. Create your environment file

```bash
cp .env.example .env
```

Open `.env` and choose the backend you want to use.

If you do not create a `.env` file, or if `.env` does not set the SPARQL backend, MLLE uses GraphDB by default:

```env
SPARQL_BACKEND=graphdb
GRAPHDB_URL=http://localhost:7200
GRAPHDB_DEFAULT_REPO=mllo5
GRAPHDB_AUTH_TYPE=none
```

The default GraphDB repository is `mllo5`. Create or import an `mllo5` repository in GraphDB and load the MLLO ontology/data there, or change `GRAPHDB_DEFAULT_REPO` to match your local MLLO repository name.

For MOBI:

```env
SPARQL_BACKEND=mobi
MOBI_ENDPOINT=https://localhost:8443/mobirest/sparql
MOBI_AUTH_TYPE=basic
MOBI_AUTH_USERNAME=admin
MOBI_AUTH_PASSWORD=admin
```

For GraphDB:

```env
SPARQL_BACKEND=graphdb
GRAPHDB_URL=http://localhost:7200
GRAPHDB_DEFAULT_REPO=mllo5
GRAPHDB_AUTH_TYPE=none
```

The repository query endpoint is always derived from `GRAPHDB_URL` and `GRAPHDB_DEFAULT_REPO`, so those values cannot drift apart.

The default app server settings are:

```env
HOST=127.0.0.1
PORT=5252
DEV=true
```

The frontend expects the API at `http://localhost:5252/api/v1` unless you set `VITE_API_BASE_URL`.

### 3. Install backend dependencies with uv

```bash
uv sync --python 3.11
```

This creates or updates the project `.venv` from `pyproject.toml` and `uv.lock`.

### 4. Install frontend dependencies

```bash
cd mllo_web/frontend/web
npm install
cd ../../..
```

### 5. Start your SPARQL backend

Start MOBI or GraphDB before starting MLLE.

For GraphDB, make sure the repository named in `GRAPHDB_DEFAULT_REPO` exists and contains the MLLO data. For MOBI, make sure `MOBI_ENDPOINT` is reachable with the credentials from `.env`.

### 6. Start the backend

From the repository root:

```bash
uv run python -m mllo_web.app.api_app
```

The backend listens on `http://localhost:5252` by default.

### 7. Start the frontend

Open a second terminal:

```bash
cd mllo_web/frontend/web
npm run dev
```

Vite prints the local frontend URL, usually `http://localhost:5173`.

### 8. Open MLLE

Open the Vite URL in your browser. Keep both terminals running while using the app in development mode.

## Optional LLM Setup

LLM setup is optional. Without an LLM endpoint, avoid the natural-language query and chat pages. SPARQL-backed browsing, search, and other non-LLM workflows can still run as long as your SPARQL backend is configured.

The repository-root `.env` is the single runtime configuration source for the server, GraphDB, LLM, and natural-language workflow. The Settings pages are read-only diagnostics and never store credentials or override `.env`. Restart the backend after changing `.env`.

### LM Studio

1. Start the LM Studio local server.
2. Load a chat or instruct model.
3. Add or update these values in `.env`:

```env
LLM_CLIENT_TYPE=openai_compatible
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_MODEL=local-model
LLM_API_KEY=lm-studio
```

Then open `/settings/llm` to verify the effective non-secret values and use **Test connection**.

### Ollama

1. Start Ollama.
2. Pull a model:

```bash
ollama pull YOUR-MODEL
```

3. Add or update these values in `.env`:

```env
LLM_CLIENT_TYPE=openai_compatible
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=YOUR-MODEL
```

Then open `/settings/llm` and use **Test connection**.

### OpenAI-Compatible API

For services that expose `/v1/chat/completions`, add or update:

```env
LLM_CLIENT_TYPE=openai_compatible
LLM_BASE_URL=https://YOUR-ENDPOINT/v1
LLM_CHAT_COMPLETIONS_PATH=/chat/completions
LLM_MODEL=YOUR-MODEL
LLM_API_KEY=YOUR_API_KEY
LLM_API_KEY_HEADER=Authorization
LLM_API_KEY_PREFIX=Bearer
```

### Azure OpenAI or Azure Foundry

Use the full chat-completions URL override and the `api-key` header:

```env
LLM_CLIENT_TYPE=azure_foundry
LLM_CHAT_COMPLETIONS_URL=https://YOUR-RESOURCE-NAME.openai.azure.com/openai/deployments/YOUR-DEPLOYMENT-NAME/chat/completions
LLM_SEND_MODEL=false
LLM_API_KEY=YOUR_AZURE_API_KEY
LLM_API_KEY_HEADER=api-key
LLM_API_KEY_PREFIX=
LLM_API_VERSION=2024-10-21
LLM_API_VERSION_PARAM=api-version
LLM_MAX_COMPLETION_TOKENS=1024
LLM_AZURE_SEND_TEMPERATURE=false
```

## Build for Deployment

Build the frontend:

```bash
cd mllo_web/frontend/web
npm run build
cd ../../..
```

Then start the backend:

```bash
uv run python -m mllo_web.app.api_app
```

After the frontend build exists, the backend serves the compiled UI from `mllo_web/frontend/web/dist`.

## Checks

Run backend NLQ regression tests:

```bash
uv run python -m unittest tests.nlq.test_regressions
```

Point the NLQ tests at a specific GraphDB repository:

```bash
MLLO_NLQ_TEST_REPO=mllo5 uv run python -m unittest tests.nlq.test_regressions
```

Run frontend checks:

```bash
cd mllo_web/frontend/web
npm run lint
npm run build
```
