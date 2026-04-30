# MLLO Web
MLLO Web is a web application for [MLLO](https://github.com/hakjuoh/MLLOS).

This guide is intended for developers working on the MLLO Web project.

### Prerequisites

- Node.js and npm: required for the Vite/React frontend.
- Python 3.11+ with a virtual environment: recommended for isolating backend dependencies.
- A SPARQL backend:
  - MOBI Server version 3.0.0. [MOBI install guide](https://inovexcorp.github.io/mobi-docs/latest/index.html#installing_the_docker_image)
  - GraphDB, if you prefer the GraphDB backend.
- An LLM endpoint for natural-language query features. Local OpenAI-compatible servers such as LM Studio and Ollama are supported, along with OpenAI-compatible and Azure OpenAI/Foundry endpoints.

### Setting up the project

#### Create local environment configuration:
```
cp .env.example .env
```

Edit `.env` for your local services. The most common values to check are:

- `HOST` / `PORT`: backend bind address. The frontend expects the backend at `http://localhost:5252`.
- `SPARQL_BACKEND`: use `mobi` or `graphdb`.
- `MOBI_ENDPOINT`, `MOBI_AUTH_*`: MOBI connection settings.
- `GRAPHDB_URL`, `GRAPHDB_DEFAULT_REPO`, or `GRAPHDB_ENDPOINT`: GraphDB connection settings.
- `LLM_*`: backend LLM request settings.

#### Install frontend dependencies:
```
cd mllo_web/frontend/web
npm install
cd ../../..
```

#### Install/Activate virtualenv:
```
python -m venv .venv
source .venv/bin/activate
```

#### Install backend dependencies:
```
pip install -r requirements.txt
```

### LLM setup

Natural-language query features need an LLM provider. There are two related configuration surfaces:

- `.env` controls backend defaults and low-level chat-completions requests.
- The app Settings page (`/settings/llm`) controls the saved provider used by the NLQ workflow. Saved settings are stored in the user data directory as `MLLE/mlle_settings.json` and override defaults loaded from environment variables.

#### LM Studio

1. Start the LM Studio local server.
2. Load a chat/instruct model.
3. Use an OpenAI-compatible base URL:

```
LLM_PROVIDER=lm_studio
LLM_CLIENT_TYPE=openai_compatible
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=local-model
LLM_API_KEY=lm-studio
```

Then open the web app Settings page, choose `lm_studio`, set the same base URL/model if needed, and use **Test connection**.

#### Ollama

Start Ollama and pull a model, for example:

```
ollama pull YOUR-MODEL
```

Then configure:

```
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL= YOUR-MODEL
```

#### OpenAI-compatible API

For services that expose `/v1/chat/completions`:

```
LLM_CLIENT_TYPE=openai_compatible
LLM_BASE_URL=https://YOUR-ENDPOINT/v1
LLM_CHAT_COMPLETIONS_PATH=/chat/completions
LLM_MODEL=YOUR-MODEL
LLM_API_KEY=YOUR_API_KEY
LLM_API_KEY_HEADER=Authorization
LLM_API_KEY_PREFIX=Bearer
```

For the Settings page `openai` provider, set:

```
OPENAI_API_KEY=YOUR_API_KEY
OPENAI_MODEL=YOUR_MODEL
```

### Running the Application

#### Run the backend server:
```
python -m mllo_web.app.api_app
```

The backend listens on `http://localhost:5252` by default and serves API routes under `/api`.

#### Run the frontend server for development:
```
cd mllo_web/frontend/web
npm run dev
```

Vite will print the frontend URL, usually `http://localhost:5173`.

#### Build the frontend UI for deployment:
```
cd mllo_web/frontend/web
npm run build
cd ../../..
```

After building, `python -m mllo_web.app.api_app` can serve the compiled frontend from `mllo_web/frontend/web/dist`.

### Testing and checks

Run the focused NLQ regression tests:

```
python -m unittest tests.nlq.test_regressions
```

Point the NLQ tests at a specific GraphDB repository:

```
MLLO_NLQ_TEST_REPO=mllo4 python -m unittest tests.nlq.test_regressions
```

Run frontend checks:

```
cd mllo_web/frontend/web
npm run lint
npm run build
```
