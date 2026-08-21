# Performance & Security

## Bundle Size

A type-only import (`import type { Foo } from './foo'`) is erased at compile time and costs nothing in the bundle — use it explicitly for imports that are only used as types, so a bundler doesn't need to guess whether the import has runtime side effects.

## Tree-Shaking

Prefer named exports over a default export that re-exports an object of everything — bundlers can tree-shake unused named exports far more reliably than they can eliminate unused properties of a single default-exported object.

## Prototype Pollution

Merging an untrusted object into another (a naive deep-merge of request body into config) can let an attacker set `__proto__` or `constructor.prototype` and affect every object in the process. Use a merge utility that explicitly guards against these keys, or validate/allowlist the incoming shape with a schema library before merging.

## Unsafe Casts

A type assertion (`as SomeType`) tells the compiler to trust you — it performs no runtime check. Reserve it for cases you've verified are genuinely safe (e.g. narrowing after a runtime check the compiler can't see), and prefer a type guard or schema-validated parse over `as` for anything derived from external input.
