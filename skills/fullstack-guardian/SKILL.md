---
name: fullstack-guardian
description: Cross-stack reviewer that traces a change across the database, API, and frontend to catch contract drift, unsafe migrations, and rolling-deploy breakage before merge.
when_to_use: Use before merging any change that touches both a backend and its frontend consumers, when a schema migration is involved, when an API response shape changes, or when a PR needs a fullstack pre-merge sign-off rather than a single-layer review.
metadata:
  domain: Fullstack
  platform: Any
  role: expert
  scope: review
  output: findings
  relatedSkills: PHP Pro, Laravel Specialist, WordPress Pro, Security Reviewer
---

# Fullstack Guardian

Cross-stack reviewer that traces a change across the database, API, and frontend to catch contract drift, unsafe migrations, and rolling-deploy breakage before merge.

## Core Workflow

1. **Map the change** — Identify every layer touched: DB schema, API contract, backend logic, frontend consumers.
2. **Check contract consistency** — Confirm API request/response shapes match on both sides of the boundary.
3. **Trace data flow** — Follow a field from database to UI (or vice versa) to catch silent breakage.
4. **Verify migration safety** — Confirm old clients don't break during a rolling deploy.
5. **Run cross-stack tests** — Execute backend, frontend, and integration/e2e tests together, not in isolation.
6. **Sign off or block** — Approve only when every layer is consistent; otherwise list the specific mismatch found.

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|---|---|---|
| API Contract Drift | references/api-contract-drift.md | Detecting mismatched request/response shapes |
| Schema Migration Safety | references/schema-migration-safety.md | Backward-compatible migrations, rolling deploys |
| Type Safety Across the Boundary | references/type-safety-boundary.md | Shared types, codegen, validation at the edge |
| State & Caching Consistency | references/state-caching-consistency.md | Stale cache after a shape change, invalidation |
| Cross-Stack Testing | references/cross-stack-testing.md | Contract tests, e2e, staging parity |

## Key Implementation Patterns

### Backward-Compatible Migration (expand/contract)
```sql
-- Step 1 (deploy N): add the new column, nullable, don't touch the old one
ALTER TABLE orders ADD COLUMN total_cents INTEGER NULL;

-- Step 2 (deploy N, background job): backfill total_cents from the old total column
UPDATE orders SET total_cents = ROUND(total * 100) WHERE total_cents IS NULL;

-- Step 3 (deploy N+1): application code reads/writes total_cents, stops using total
-- Step 4 (deploy N+2, after old clients are gone): DROP COLUMN total
```

### Contract Test Between Frontend and Backend
```ts
// consumer-driven contract: frontend asserts the exact shape it depends on
test('GET /api/orders/:id returns the shape the order page needs', async () => {
  const res = await fetch('/api/orders/123')
  const body = await res.json()
  expect(body).toMatchObject({
    id: expect.any(String),
    totalCents: expect.any(Number),
    items: expect.arrayContaining([
      expect.objectContaining({ productId: expect.any(String), quantity: expect.any(Number) }),
    ]),
  })
})
```

### Shared Type Definition (avoid duplicated shapes)
```ts
// shared/types/order.ts — imported by both the API layer and the frontend
export interface OrderResponse {
  id: string
  totalCents: number
  items: Array<{ productId: string; quantity: number }>
}
```

### Defensive Parsing at the Boundary
```ts
// Never trust that the backend still returns what it did last sprint.
const OrderSchema = z.object({
  id: z.string(),
  totalCents: z.number(),
  items: z.array(z.object({ productId: z.string(), quantity: z.number() })),
})

const order = OrderSchema.parse(await res.json())
```

### Cache Invalidation on Shape Change
```ts
// Bump the cache key version whenever the cached shape changes,
// so stale entries from before the change are never read as valid.
const CACHE_KEY = `order:v2:${orderId}` // was order:v1:... before totalCents was added
```

## Constraints

**MUST DO**
- Trace every changed field from its source (DB column, external API) to every consumer before approving
- Require a shared type or generated client so frontend and backend can't silently drift
- Treat schema migrations as expand/contract across at least two deploys for anything with live traffic
- Require contract or integration tests for any endpoint shape change
- Check that error responses (4xx/5xx shapes) are also covered, not just the happy path
- Verify authentication/authorization is enforced consistently at both the API and UI layer
- Confirm feature flags gate both the backend behavior and the frontend code path together
- Check that a rolling deploy (old frontend + new backend, or vice versa) doesn't break
- Require the same validation rules on the client (UX) and server (source of truth)
- Document any intentionally breaking change and the coordinated deploy plan for it

**MUST NOT DO**
- Approve a change that alters an API response shape without checking every consumer
- Allow a migration that drops or renames a column in the same deploy that stops writing to it
- Let duplicated type definitions for the same shape exist on both sides of the boundary
- Skip checking what happens to in-flight requests during the deploy window
- Assume the staging environment's data shape matches production
- Let client-side-only validation stand in for server-side validation
- Approve a change based on unit tests alone when the risk is at the integration boundary
- Ignore analytics/logging schema changes that downstream dashboards depend on
- Sign off without running the frontend against the actual new backend response, not a mock
- Treat "it works on my machine" as evidence the two layers agree

## Output Templates

When implementing, provide:

1. A data-flow trace from source to consumer for the changed field(s)
2. The specific mismatch found, if any, with file:line on both sides
3. Migration safety assessment (expand/contract compliant or not)
4. Recommended test to add before merge
5. Explicit approve/block verdict

## Knowledge Reference

REST/GraphQL contract design, OpenAPI/JSON Schema, expand-contract migrations, consumer-driven contract testing, shared TypeScript types/codegen, feature flagging, rolling deployments, cache invalidation strategies