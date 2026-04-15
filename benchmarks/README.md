# Benchmarks

This directory is for broader evaluation runs that measure NLQ quality, coverage, and performance over time.

Use `benchmarks/` for:

- prompt sets
- benchmark configs
- run scripts
- dated result snapshots
- generated reports

Keep benchmark assets separate from `tests/` so heavy evaluation data does not clutter the fast correctness checks.

Suggested layout:

- `nlq/prompts/`
- `nlq/configs/`
- `nlq/results/`
- `nlq/reports/`
- `nlq/scripts/`

