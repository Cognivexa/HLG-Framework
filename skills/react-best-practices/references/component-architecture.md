# Component Architecture

## Composition Over Configuration

Prefer composing small components via `children` or slots over one large component with many boolean/variant props controlling its internal branches:

```tsx
<Card>
  <Card.Header>Order #123</Card.Header>
  <Card.Body>...</Card.Body>
</Card>
```

This scales better than `<Card showHeader variant="order" headerContent="...">` as requirements grow, and each piece can be tested and reused independently.

## Prop Drilling

Passing a prop through three or more intermediate components that don't use it themselves is a sign the data belongs in Context, a colocated state manager, or that the component tree should be restructured (e.g. by moving the consuming component up and passing it down as `children` instead).

## Container/Presentational Split

Separate "how to fetch/compute the data" from "how to render it" — a presentational component that only receives props and renders is trivial to test and reuse, while the data-fetching logic can be swapped (mocked, cached, moved to a server component) independently.

## Component Size

If a component's render function needs scrolling to read in one pass, or it manages more than two or three pieces of unrelated state, it's usually a sign to extract a child component or a custom hook.
