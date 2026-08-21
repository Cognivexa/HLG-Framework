# Performance

## Memoization Is Not Free

`useMemo`/`useCallback`/`memo` each have their own overhead (comparing dependencies) — applying them everywhere "just in case" can make things slower, not faster. Reach for them when a profiler shows a component actually re-rendering expensively and unnecessarily, not by default on every component.

## Virtualization

For a list that can grow large (hundreds+ of rows), render only the visible window with a virtualization library instead of every row — a full DOM tree for a huge list degrades scroll performance and initial render time regardless of how well individual rows are optimized.

## Code Splitting

Split rarely-visited routes or heavy, optional features (a rich text editor, a charting library) into a separate chunk loaded with `React.lazy` and `Suspense`, so the initial bundle only pays for what most users need immediately.

```tsx
const ReportBuilder = lazy(() => import('./ReportBuilder'))
```

## Profiling Before Optimizing

Use the React DevTools Profiler to find which components actually re-render and why, before reaching for memoization — the component that "feels" slow is often not the one that's actually re-rendering excessively.
