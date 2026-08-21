# Hooks & State Management

## useState vs. useReducer

Reach for `useReducer` when a component has several pieces of state that change together in response to the same actions (a form with validation state, submission state, and field values) — it makes the valid transitions explicit instead of scattered across several `useState` calls that can drift out of sync with each other.

## Context

Context re-renders every consumer when the value changes, regardless of which part of the value a given consumer actually reads. Split a large context into smaller, more focused ones, or pair it with a selector-based store (Zustand, Jotai) when a value changes frequently and many components read only part of it.

## Server State vs. Client State

Data that lives on a server (fetched via an API) has different needs than truly client-only state (a modal's open/closed flag): it needs caching, revalidation, and de-duplication of in-flight requests. Use React Query, SWR, or RTK Query for server state, and reserve `useState`/Context/a lightweight store for genuinely client-local state.

## Derived State

If a value can be computed from existing props/state, compute it during render (optionally wrapped in `useMemo` if the computation is expensive) rather than storing it in its own `useState` and syncing it with a `useEffect` — the synced-copy pattern is a common source of stale-state bugs.
