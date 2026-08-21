# API Contract Drift

## What It Looks Like

The backend renames a field, changes a type (string to number), makes a field optional that was required, or reorders array items the frontend assumed were sorted — and nothing fails until a specific user hits the specific path that depended on the old shape.

## Detecting It

Diff the actual response shape before and after the change, not just the code diff — read the serializer/resource/DTO, not the controller, since that's where the wire shape is actually defined. Grep the frontend for every place that destructures or accesses the field being changed; a TypeScript-only search misses stringly-typed access in untyped JS or dynamic property access.

## The Fix

Add or update a shared type/schema (OpenAPI, JSON Schema, or a hand-shared TS interface) as part of the same change, and require the frontend PR that consumes it to be reviewed alongside the backend PR — never merge the backend half first and "fix the frontend later."

## When Drift Is Intentional

A genuinely breaking API change still needs a plan: version the endpoint, ship both shapes for one deploy cycle, or coordinate a synchronized deploy of both sides. Document which of these applies in the PR description so the reviewer isn't left guessing whether the drift is a bug or a plan.
