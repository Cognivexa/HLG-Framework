# Testing

## Vitest / Jest

Keep tests close to the code they cover and assert on observable behavior (return values, thrown errors, calls to injected collaborators), not on internal implementation details that are free to change.

```ts
it('rejects a negative quantity', () => {
  expect(() => new OrderItem('sku', -1)).toThrow('quantity must be positive')
})
```

## Mocking

Prefer passing a fake/stub implementation of a dependency through its constructor or parameter over mocking a module import — it keeps the test's setup honest about what the function actually depends on.

## Type-Level Tests

For a library exporting complex generic types, add type-level tests that assert on the *type* the compiler infers, not just runtime values:

```ts
import { expectTypeOf } from 'vitest'

expectTypeOf(pluck([{ id: 1, name: 'a' }], 'name')).toEqualTypeOf<string[]>()
```

This catches a change that breaks type inference for consumers even when every runtime test still passes.

## Coverage as a Signal

Treat coverage as a map of what's untested, not a score to maximize — a test that only calls a function without asserting anything meaningful inflates coverage while catching nothing.
