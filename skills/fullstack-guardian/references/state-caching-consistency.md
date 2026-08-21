# State & Caching Consistency

## The Stale Shape Problem

Changing an API response shape while an old cached response is still being served produces objects that don't match either the old or new frontend code's expectations — a partially-migrated read is often worse than a fully-old one.

## Versioned Cache Keys

Include a version segment in any cache key for data whose shape can change (`order:v2:123` instead of `order:123`), and bump it whenever the cached shape changes, so a deploy naturally invalidates old entries instead of requiring a manual cache flush that's easy to forget.

## Client-Side State

The same problem exists in frontend state managers (Redux/Zustand/React Query caches) — a user with a tab open across a deploy can hold state shaped like the old API. Prefer short cache TTLs plus revalidation-on-focus for data whose shape might change, over long-lived client caches with no invalidation path.

## CDN and Edge Caches

An API response cached at a CDN layer is invisible to both the backend and frontend test suite. If the endpoint is cached there, changing its shape needs an explicit cache purge as part of the deploy, not just a code change.
