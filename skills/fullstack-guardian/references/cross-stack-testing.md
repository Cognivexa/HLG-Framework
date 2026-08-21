# Cross-Stack Testing

## Why Layer-Isolated Tests Miss This

Backend unit tests confirm the backend does what the backend test expects. Frontend unit tests confirm the frontend does what the frontend test (usually backed by a mock) expects. Neither one confirms the two actually agree with each other — that gap is exactly where contract drift lives.

## Contract Tests

Write a test, owned by the consumer, that asserts the exact shape it depends on from the provider — run against the real provider (or a provider-verified mock), not a hand-maintained fixture that can drift from reality on its own.

## Staging Parity

Run the frontend against a staging backend that has gone through the same migration path as production will, not a fresh seed database with the final schema already applied — the fresh-seed version can hide expand/contract bugs that only show up mid-migration.

## End-to-End Tests

Reserve e2e tests for the handful of critical paths (checkout, sign-up, payment) where a cross-stack regression is expensive — e2e suites are slow and flaky at scale, so they complement contract tests rather than replacing them for everyday coverage.
