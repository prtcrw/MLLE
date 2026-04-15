# NLQ Benchmarking

## Purpose

Use NLQ benchmarks to evaluate overall system quality across a broader set of prompts than the regression tests cover.

## Keep Separate From Regressions

Use `tests/nlq/` when the goal is:

- prevent a known bug from returning
- protect a stable response shape
- quickly validate refactors

Use `benchmarks/nlq/` when the goal is:

- compare models, prompts, or routing behavior
- measure trends over time
- inspect broader quality and latency

## Recommended Workflow

1. Add a focused regression test when a concrete bug is fixed.
2. Add representative prompts to the benchmark set when they help evaluate broader quality.
3. Run regression tests often.
4. Run benchmarks on meaningful changes, model swaps, or before release decisions.

## LLM Selection

For local-model selection, use:

- [benchmarks/nlq/prompts/model_selection_cases.json](/Users/pnc12/Documents/GitHub/MLLO-Web-2/benchmarks/nlq/prompts/model_selection_cases.json) for the prompt set
- [benchmarks/nlq/configs/llm_candidates.example.json](/Users/pnc12/Documents/GitHub/MLLO-Web-2/benchmarks/nlq/configs/llm_candidates.example.json) for candidate definitions
- [benchmarks/nlq/scripts/benchmark_llm_candidates.py](/Users/pnc12/Documents/GitHub/MLLO-Web-2/benchmarks/nlq/scripts/benchmark_llm_candidates.py) for the runner

The runner records, per candidate:

- pass or fail against structural expectations
- routing behavior
- inference usage
- result shape
- per-prompt latency
- overall pass rate and median latency

This is a good fit for deciding whether a model is "fast yet good" for MLLO NLQ, because it captures both correctness signals and response time across structured, lineage, inference, and `custom_sparql` prompts.

If you are using LM Studio locally, set candidate entries to:

- `provider`: `lm_studio`
- `base_url`: `http://localhost:1234/v1`
- `model`: the model name exposed by your LM Studio server
