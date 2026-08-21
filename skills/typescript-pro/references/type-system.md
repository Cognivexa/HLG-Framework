# Type System Fundamentals

## Discriminated Unions

Model a value that can be one of several distinct shapes as a union tagged by a literal field, not as one object with a pile of optional fields:

```ts
type LoadState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }
```

Switching on `status` lets TypeScript narrow the type in each branch — `state.data` is only accessible where `status === 'success'`, so a bug that reads `data` before it exists is a compile error, not a runtime `undefined`.

## Conditional & Mapped Types

```ts
type NonNullableFields<T> = { [K in keyof T]: NonNullable<T[K]> }
```

Reach for a mapped or conditional type when a transformation needs to apply uniformly across every property of an existing type — deriving it once avoids the two types drifting apart as fields are added.

## Generics With Real Constraints

A generic that accepts literally anything (`<T>`) is rarely the goal — constrain it to what the function actually needs (`<T extends { id: string }>`), so the compiler catches a caller passing something structurally incompatible.

## Utility Types

Prefer built-in utility types (`Partial`, `Pick`, `Omit`, `ReturnType`) derived from an existing type over hand-writing a near-duplicate interface — the derived version stays in sync automatically when the source type changes.
