# NLQ Benchmarks

This folder is for broader NLQ evaluation, not narrow regression protection.

Typical benchmark goals:

- compare model providers or prompts
- measure latency and failure rate
- compare routing behavior across revisions
- track answer quality on a larger prompt set

Recommended practice:

- store reusable benchmark prompt sets in `prompts/`
- store run settings in `configs/`
- write raw outputs to `results/`
- keep summarized charts or markdown reports in `reports/`
- keep benchmark runner scripts in `scripts/`

Starter assets added here:

- [prompts/model_selection_cases.json](/Users/pnc12/Documents/GitHub/MLLO-Web-2/benchmarks/nlq/prompts/model_selection_cases.json)
- [configs/llm_candidates.example.json](/Users/pnc12/Documents/GitHub/MLLO-Web-2/benchmarks/nlq/configs/llm_candidates.example.json)
- [scripts/benchmark_llm_candidates.py](/Users/pnc12/Documents/GitHub/MLLO-Web-2/benchmarks/nlq/scripts/benchmark_llm_candidates.py)

Run a model comparison with:

```bash
conda run --no-capture-output -n mlloweb python benchmarks/nlq/scripts/benchmark_llm_candidates.py
```

Or point to your own candidate config:

```bash
conda run --no-capture-output -n mlloweb python benchmarks/nlq/scripts/benchmark_llm_candidates.py \
  --config benchmarks/nlq/configs/llm_candidates.example.json
```

The example config is set up for `lm_studio` on `http://localhost:1234/v1`.
