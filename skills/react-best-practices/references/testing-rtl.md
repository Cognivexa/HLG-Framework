# Testing with React Testing Library

## Query Priority

Query in the order the library recommends: by accessible role and name first (`getByRole('button', { name: /submit/i })`), then by label text, then by text content — reach for `data-testid` only when no accessible query applies. This keeps tests aligned with what a real user (including one using assistive technology) actually perceives.

## user-event Over fireEvent

Use `@testing-library/user-event` instead of `fireEvent` for interactions — it simulates the full sequence of events a real user interaction produces (focus, keydown, input, etc.), catching bugs that a single synthetic `fireEvent.change` call would miss.

## Avoiding Implementation Details

Don't assert on component internal state, instance methods, or exactly which child function was called — assert on what the user would see or the effect on the outside world (a callback fired, text now visible on screen). This lets the component be refactored internally without breaking its tests.

## Async Assertions

Wrap assertions on data that arrives asynchronously in `findBy*` queries or `waitFor`, rather than asserting immediately after a state-changing action — a synchronous assertion right after a fetch-triggering click is a common source of flaky tests.
