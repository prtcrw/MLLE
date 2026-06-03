# Testing, Benchmarking, and Tracing Guide by gemma4:31b

This guide explains how to ensure the correctness of the MLLO Web system, evaluate LLM performance, and debug individual Natural Language Query (NLQ) flows.

## Overview: Which tool should I use?

| Tool | Purpose | Scope | Output | Speed |
| :--- | :--- | :--- | :--- | :--- |
| **Tests** | Correctness & Regression | Small set of deterministic cases | Pass/Fail (CLI) | Fast |
| **Benchmarks** | Quality & Performance | Large sets across multiple LLMs | JSON & Markdown Reports | Slow |
| **Tracing** | Deep-Dive Debugging | Single query execution flow | Detailed Markdown Trace | Medium |

---

## 1. Running Tests (Correctness)
Tests are designed to be fast and deterministic. They ensure that core logic doesn't break during refactors.

### Prerequisites
Install the project environment:

```bash
uv sync --python 3.11
```

### Execution Commands
The project uses `pytest`. You can run tests at various levels of granularity:

*   **Run all tests in the project**:
    ```bash
    uv run python -m pytest tests/
    ```
*   **Run only NLQ regression tests**:
    ```bash
    uv run python -m pytest tests/nlq/test_regressions.py
    ```
*   **Run a specific test function**:
    ```bash
    uv run python -m pytest tests/nlq/test_regressions.py::test_specific_case_name
    ```

---

## 2. Running Benchmarks (Evaluation)
Benchmarks are used to compare different LLM providers or models to determine which one provides the best balance of accuracy and speed for your specific dataset.

### Execution
Run the benchmark script by specifying a prompt manifest and a candidate configuration:

```bash
uv run python benchmarks/nlq/scripts/benchmark_llm_candidates.py \
  --prompts benchmarks/nlq/prompts/model_selection_cases.json \
  --config benchmarks/nlq/configs/llm_candidates.example.json \
  --output benchmarks/nlq/results/my_eval_run.json
```

### Arguments Detail
- `--prompts`: Path to a JSON file containing the questions and expected outcomes.
- `--config`: Path to a JSON file defining the LLM candidates (API keys, models, base URLs).
- `--output`: (Optional) Custom path for the result files. If omitted, it defaults to a timestamped file in `benchmarks/nlq/results/`.

### Analyzing Reports
The script generates two reports with the same filename but different extensions:

#### 1. The JSON Report (`.json`)
Contains raw data including every response and latency measurement. Ideal for programmatic analysis or importing into spreadsheets.

#### 2. The Markdown Report (`.md`)
A human-readable summary designed for quick decision-making:
- **Scoreboard**: A ranked list of candidates. Ranking is determined first by **Pass Rate** (descending) and then by **Median Latency** (ascending).
- **Candidate Summaries**: High-level stats (Passed, Failed, Errored) per model.
- **Case Grid**: A visual matrix showing which specific questions were passed (✅), failed (❌), or errored (💥).
- **Failure Analysis**: For every failed case, the report includes the generated SPARQL, allowing you to see exactly where the LLM's logic diverged from the expected result.

---

## 3. Tracing Single Queries (Debugging)
When a specific query fails in a benchmark or during manual use, use the Trace script to "open the hood" and see every internal step.

### Execution
```bash
uv run python scripts/trace_nlq.py "What downstream artifacts use MnistG16?"
```

### The Trace Report (`tmp/trace_<timestamp>.md`)
The trace captures the full lifecycle of a request:

1.  **Metadata**: Records the question, target repository, LLM provider/model used, and total wall-clock duration.
2.  **LLM Call Sequence**: Every single interaction with the LLM is logged in order:
    - **Purpose**: (e.g., `intent_classification` $\rightarrow$ `sparql_generation` $\rightarrow$ `sparql_repair` $\rightarrow$ `answer_generation`).
    - **Latency**: The exact time taken for that specific API call.
    - **Prompts**: The full system prompt and user prompt sent to the model.
    - **Raw Response**: Exactly what the LLM returned before any parsing.
3.  **Execution Plan**: Details on which tool was selected (e.g., `graph_native` vs `sparql`) and why.
4.  **Database Execution**: The final SPARQL query executed against the database, the inference flags used, and a preview of the raw rows returned.
5.  **Final Response**: The natural language answer delivered to the end-user.

---

## 4. Manually Creating New Benchmarks

### Step A: Define Test Cases (`prompts/*.json`)
Create a JSON file in `benchmarks/nlq/prompts/`. Each object in the list represents one test case:

```json
[
  {
    "question": "How many nodes are in the graph?",
    "category": "counting",
    "expected_tool": "graph_stats", 
    "expected_inference_used": true,
    "min_results": 1,
    "expected_keys": ["node_count"]
  }
]
```
- `question`: The NLQ input.
- `category`: Used for grouping results in reports.
- `expected_tool`: The tool the system *should* have picked.
- `expected_inference_used`: Whether the logic should have triggered an inference step.
- `min_results`: Minimum number of rows expected in the result set.
- `expected_keys`: Column names that must be present in the results for the case to be marked as "Passed".

### Step B: Define LLM Candidates (`configs/*.json`)
Create a JSON file in `benchmarks/nlq/configs/` to define who is being tested:

```json
{
  "repo": "default_repo",
  "answer_mode": "auto",
  "candidates": [
    {
      "name": "GPT-4o-Production",
      "provider": "openai",
      "model": "gpt-4o",
      "api_key": "sk-...",
      "base_url": "https://api.openai.com/v1"
    }
  ]
}
```

### Step C: The Workflow
1. **Identify a Gap**: Find a query that the system currently fails on.
2. **Add to Prompts**: Add that query and its expected keys to your prompt manifest.
3. **Run Benchmark**: Execute `benchmark_llm_candidates.py` with your new manifest.
4. **Iterate**: Use the Markdown report's "Failure Analysis" to adjust system prompts or tool definitions, then re-run the benchmark to verify improvement.
