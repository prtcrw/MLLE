# Gemma 4 e4b Regression Run

Date: 2026-04-13 16:38:11 EDT

## Model

- Provider: `lm_studio`
- Base URL: `http://127.0.0.1:1234/v1`
- Model: `google/gemma-4-e4b`

## Command

```bash
MLLO_NLQ_TEST_PROVIDER=lm_studio \
MLLO_NLQ_TEST_BASE_URL=http://127.0.0.1:1234/v1 \
MLLO_NLQ_TEST_MODEL=google/gemma-4-e4b \
uv run python -m unittest tests.nlq.test_regressions
```

## Result

```text
Ran 7 tests in 458.238s

OK
```

## Coverage

The current regression suite covers:

- conceptual inference prompts
- structured pipeline and model lookup
- lineage questions
- lineage plus model enrichment
- performance enrichment
- `custom_sparql` join-style prompts

## Takeaway

`google/gemma-4-e4b` passed the current NLQ regression suite.

The main concern is speed, not correctness. This run took about 7 minutes and 38 seconds for 7 tests, so this model is usable for quality validation but may be too slow to be the default if faster models achieve similar pass rates.

## Baseline For Comparison

- Pass rate: `7/7`
- Runtime: `458.238s`
