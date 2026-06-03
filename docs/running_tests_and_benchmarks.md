# Running Tests and Benchmarks by claude

## Running Tests

Tests live in [`tests/nlq/test_regressions.py`](../tests/nlq/test_regressions.py) and use Python's `unittest` framework.

### Basic run

```bash
# From the project root
uv run python -m pytest tests/

# Or with unittest directly
uv run python -m unittest discover tests/
```

### Run a specific file

```bash
uv run python -m pytest tests/nlq/test_regressions.py -v
```

### Run a single test method

```bash
uv run python -m pytest tests/nlq/test_regressions.py::NLQRegressionTests::test_downstream_artifacts_query_returns_lineage_shape -v
```

### Override LLM provider via env vars

The tests accept these environment variables to swap in a different LLM without changing code:

| Variable | Default | Purpose |
|---|---|---|
| `MLLO_NLQ_TEST_REPO` | `mllo4` | GraphDB repo to query |
| `MLLO_NLQ_TEST_PROVIDER` | *(from settings)* | LLM provider (e.g. `lm_studio`, `openai`) |
| `MLLO_NLQ_TEST_BASE_URL` | *(from settings)* | Base URL (e.g. `http://localhost:1234/v1`) |
| `MLLO_NLQ_TEST_MODEL` | *(from settings)* | Model name |
| `MLLO_NLQ_TEST_API_KEY` | *(from settings)* | API key |

```bash
MLLO_NLQ_TEST_PROVIDER=lm_studio \
MLLO_NLQ_TEST_BASE_URL=http://localhost:1234/v1 \
MLLO_NLQ_TEST_MODEL=gemma4:e4b \
uv run python -m pytest tests/ -v
```

---

## Running the Benchmark

The benchmark lives at [`benchmarks/nlq/scripts/benchmark_llm_candidates.py`](../benchmarks/nlq/scripts/benchmark_llm_candidates.py). It runs all prompt cases across multiple LLM candidates and measures **pass rate** and **latency**.

### Step 1 — Set up your config

Copy the example config and edit it:

```bash
cp benchmarks/nlq/configs/llm_candidates.example.json benchmarks/nlq/configs/my_candidates.json
```

Edit `my_candidates.json` with your actual models:

```json
{
  "repo": "mllo4",
  "answer_mode": "auto",
  "candidates": [
    {
      "name": "gemma4-e4b",
      "provider": "lm_studio",
      "base_url": "http://localhost:1234/v1",
      "model": "gemma4:e4b"
    }
  ]
}
```

### Step 2 — Run it

```bash
# Uses default prompts + example config
uv run python benchmarks/nlq/scripts/benchmark_llm_candidates.py

# Specify your own config
uv run python benchmarks/nlq/scripts/benchmark_llm_candidates.py \
  --config benchmarks/nlq/configs/my_candidates.json

# Specify a different prompt set
uv run python benchmarks/nlq/scripts/benchmark_llm_candidates.py \
  --prompts benchmarks/nlq/prompts/model_selection_cases.json \
  --config benchmarks/nlq/configs/my_candidates.json

# Save to a specific output file
uv run python benchmarks/nlq/scripts/benchmark_llm_candidates.py \
  --config benchmarks/nlq/configs/my_candidates.json \
  --output benchmarks/nlq/results/my_run.json
```

### Output

Two files are saved side by side in `benchmarks/nlq/results/`:

| File | Content |
|---|---|
| `llm_benchmark_<timestamp>.json` | Full machine-readable results |
| `llm_benchmark_<timestamp>.md` | Human-readable report with scoreboard, per-candidate summary table, per-case pass/fail, and failed-case SPARQL detail |

A scoreboard is also printed to stdout, sorted by pass rate then median latency.

---

## Tracing a Single Chat Question

[`scripts/trace_nlq.py`](../scripts/trace_nlq.py) runs **one question** and produces a step-by-step Markdown trace showing every LLM call, the SPARQL generated, GraphDB results, and the final answer — with timestamps, model name, provider, and per-call latency.

### Run it

```bash
# Default question
uv run python scripts/trace_nlq.py

# Your own question
uv run python scripts/trace_nlq.py "What downstream artifacts use MnistG16?"

# Choose repo and answer mode
uv run python scripts/trace_nlq.py "Show me models with performance > 0.9" \
  --repo mllo4 \
  --answer-mode auto

# Save to a specific file
uv run python scripts/trace_nlq.py "..." --output tmp/my_trace.md

# Print to stdout only, no file written
uv run python scripts/trace_nlq.py "..." --no-md
```

### What the Markdown trace contains

1. **Metadata** — question, repo, provider, model, timestamps, total duration, request ID
2. **LLM Calls** (one section per call, in order):
   - Purpose (`intent_classification`, `sparql_generation`, `sparql_repair_validation`, `sparql_repair_execution`, `answer_generation`)
   - Provider, model, base URL, latency, prompt char count
   - Full system prompt and user prompt
   - Raw LLM response
3. **Execution Plan** — tool chosen, params, reasoning
4. **Execution Steps** — tool, params, SPARQL, inference flag, result count, results preview
5. **Final Response** — intent, final SPARQL, results preview (5 rows), natural language answer

The trace file is written to `tmp/trace_<timestamp>.md` by default.

---

## Key Difference

| | Tests (`tests/`) | Benchmark (`benchmarks/`) | Trace (`scripts/trace_nlq.py`) |
|---|---|---|---|
| Purpose | Correctness regression checks | Quality + latency across LLM candidates | Step-by-step explainability for one question |
| Speed | Fast, targeted | Slower, runs all prompt cases | Single query |
| Output | Pass/fail per assertion | JSON + MD report with scoreboard | MD trace with full prompts + SPARQL |
| When to use | Before merging, CI | When evaluating a new model | Debugging, understanding what the system did |
