# Regression Policy

Add an NLQ regression test when:

- a user-facing bug was fixed
- orchestration logic changed
- result enrichment changed
- answer formatting depends on specific result keys

Prefer structural assertions over brittle full-text assertions.

Examples:

- response executes successfully
- result count is non-zero
- result rows contain expected keys such as `model_name`, `test_datasets`, or `pipelines`
- the request no longer falls back to an error path that previously failed

