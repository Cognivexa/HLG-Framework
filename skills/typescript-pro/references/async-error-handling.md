# Async & Error Handling

## Typed Promises

An `async` function's return type is inferred as `Promise<T>` — annotate it explicitly on public APIs so a change to what the function resolves to is caught at every call site, not just where the change was made.

## Result Types Over Throwing

For expected failure cases (validation, a not-found lookup), consider returning a discriminated `Result<T, E>` instead of throwing — it forces the caller to handle the failure case at the type level, rather than relying on them remembering to wrap the call in `try/catch`:

```ts
type Result<T, E = string> = { ok: true; value: T } | { ok: false; error: E }
```

Reserve actual `throw` for genuinely exceptional, programmer-error conditions (an invariant violation), not for expected business outcomes like "user not found."

## Typed Catch Blocks

`catch` binds its parameter as `unknown` under strict mode (correctly — anything can be thrown). Narrow it before use:

```ts
try {
  await risky()
} catch (err) {
  if (err instanceof PaymentError) return { ok: false, error: err.code }
  throw err
}
```

## Avoiding Floating Promises

Enable the `no-floating-promises` ESLint rule (from `typescript-eslint`) — an un-awaited promise whose rejection is never handled is a common source of silently swallowed errors and unhandled rejection crashes.
