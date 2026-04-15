# Tests

This directory is for automated checks that should stay fast, deterministic, and useful during refactors.

Suggested layout:

- `nlq/`: regression tests for natural-language-query behavior
- `integration/`: multi-module tests that exercise app boundaries
- `smoke/`: very small end-to-end checks for critical flows

Rules of thumb:

- Put pass/fail correctness checks here.
- Keep these tests small enough to run regularly during development.
- Do not store large benchmark result files here.

