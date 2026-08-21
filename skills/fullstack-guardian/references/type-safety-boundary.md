# Type Safety Across the Boundary

## The Core Problem

A backend type and a frontend type that describe the same API response are, by default, two independent pieces of code with no compiler check that they agree. They drift silently the moment one side changes without the other.

## Shared Types

Where both sides are the same language (TypeScript monorepo), put the wire-format type in a shared package both sides import — there is then exactly one place to update, and a change to it shows type errors on both sides immediately.

## Codegen From a Schema

Where the backend isn't TypeScript, generate the frontend's types from an OpenAPI spec, GraphQL schema, or protobuf definition rather than hand-writing them. A generated client fails to compile the moment the backend's contract changes, instead of failing silently at runtime.

## Validation at the Edge

Even with shared or generated types, validate the actual response at runtime (with a schema library such as Zod or io-ts) at the one place data crosses the network boundary. Compile-time types describe what the backend is *supposed* to send; runtime validation catches what it *actually* sent — including bugs, an unmigrated old server, or a network proxy that mangled the payload.
