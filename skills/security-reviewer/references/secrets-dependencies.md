# Secrets & Dependency Hygiene

## Secrets

Never commit API keys, database credentials, or signing keys to source control — including in test fixtures, comments, or commit history from before it was removed (a deleted secret in git history is still exposed; rotate it, don't just delete the line). Load secrets from environment variables or a dedicated secrets manager, and fail fast at startup if a required secret is missing rather than silently running with an empty value.

## Secret Scanning

Run a secret-scanning tool (gitleaks, truffleHog, or the equivalent built into most CI platforms) on every push, not just at audit time — catching a committed secret in the same PR is far cheaper than rotating it after it's been live in history for months.

## Software Composition Analysis (SCA)

Run dependency vulnerability scanning (`npm audit`, `composer audit`, Dependabot, Snyk) on a schedule and on every dependency bump. A vulnerable transitive dependency is exploitable exactly the same as vulnerable code you wrote yourself.

## Supply Chain Risk

Pin dependency versions and review new dependencies before adding them, especially small packages with a single maintainer — a compromised maintainer account or a typosquatted package name are both real, recurring attack vectors. Prefer well-maintained, widely-used packages over marginally more convenient ones with a tiny user base.
