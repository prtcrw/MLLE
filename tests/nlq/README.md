# NLQ Regression Tests

This folder is for focused regression tests that protect known NLQ behavior.

Good candidates:

- lineage questions such as `What downstream artifacts use MnistG16?`
- hybrid lineage questions such as `What models use downstream artifacts of MnistG16?`
- performance-enrichment questions that should return model, dataset, and pipeline context

These tests should check stable structural expectations, for example:

- the request does not crash
- the response contains rows
- specific keys are present in result rows
- known regressions do not reappear

Current starter regression file:

- [test_regressions.py](/Users/pnc12/Documents/GitHub/MLLO-Web-2/tests/nlq/test_regressions.py)

Run with:

```bash
uv run python -m unittest tests.nlq.test_regressions
```

If needed, override the GraphDB repo with:

```bash
MLLO_NLQ_TEST_REPO=mllo4 uv run python -m unittest tests.nlq.test_regressions
```

If you want to force the tests to use an LM Studio model instead of the saved app settings:

```bash
MLLO_NLQ_TEST_PROVIDER=lm_studio \
MLLO_NLQ_TEST_BASE_URL=http://localhost:1234/v1 \
MLLO_NLQ_TEST_MODEL=your-model-name \
uv run python -m unittest tests.nlq.test_regressions
```
