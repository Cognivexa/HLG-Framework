---
name: react-best-practices
description: Expert React developer specializing in component architecture, hooks, and performance: eliminates prop drilling, unnecessary re-renders, and unsafe effects.
when_to_use: Use when building or reviewing React components, extracting custom hooks, choosing a state-management approach, optimizing re-renders, writing React Testing Library tests, or auditing components for accessibility and XSS risk.
metadata:
  domain: React
  platform: JavaScript/TypeScript
  role: expert
  scope: implementation
  output: code
  relatedSkills: TypeScript Pro, Fullstack Guardian, Security Reviewer
---

# React Best Practices

Expert React developer specializing in component architecture, hooks, and performance: eliminates prop drilling, unnecessary re-renders, and unsafe effects.

## Core Workflow

1. **Analyze requirements** — Understand the app's React version, state management approach, and existing component conventions.
2. **Design component architecture** — Decide component boundaries, prop contracts, and where state should live.
3. **Implement** — Build with hooks, proper memoization, and accessible markup.
4. **Validate** — Run the linter (eslint-plugin-react-hooks) and type-check props/state.
5. **Test** — Write React Testing Library tests focused on behavior, not implementation details.
6. **Optimize & secure** — Profile re-renders with React DevTools, and audit for XSS via dangerouslySetInnerHTML and unsafe prop passthrough.

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|---|---|---|
| Component Architecture | references/component-architecture.md | Composition, prop drilling, container/presentational split |
| Hooks & State Management | references/hooks-state-management.md | useState/useReducer, context, external stores |
| Performance | references/performance.md | Memoization, virtualization, code splitting |
| Testing with React Testing Library | references/testing-rtl.md | Querying by role, user-event, avoiding implementation details |
| Accessibility & Security | references/accessibility-security.md | ARIA, focus management, dangerouslySetInnerHTML risks |

## Key Implementation Patterns

### Custom Hook Extraction
```tsx
function useOrderTotal(items: OrderItem[]): number {
  return useMemo(
    () => items.reduce((sum, item) => sum + item.priceCents * item.quantity, 0),
    [items]
  )
}
```

### Avoiding Unnecessary Re-Renders
```tsx
const ExpensiveRow = memo(function ExpensiveRow({ item }: { item: OrderItem }) {
  return (
    <tr>
      <td>{item.name}</td>
      <td>{item.priceCents}</td>
    </tr>
  )
})
```

### Context for Cross-Cutting State Only
```tsx
const ThemeContext = createContext<Theme>('light')

// Reach for context for truly cross-cutting state (theme, auth, locale) —
// not as a shortcut past prop drilling for a couple of levels.
```

### Testing Library — Query by Role, Not by Class
```tsx
test('submits the order form', async () => {
  render(<OrderForm onSubmit={onSubmit} />)
  await userEvent.click(screen.getByRole('button', { name: /place order/i }))
  expect(onSubmit).toHaveBeenCalled()
})
```

### Safe HTML Rendering
```tsx
// Never: dangerouslySetInnerHTML={{ __html: userInput }}
// Sanitize first if raw HTML is genuinely required:
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(markdownHtml) }} />
```

## Constraints

**MUST DO**
- Keep components small and focused on one responsibility
- Use useMemo/useCallback only where a measured re-render cost justifies it
- Extract reusable stateful logic into custom hooks
- Query in tests by role/label text, not by class name or test-id when an accessible query exists
- Manage server state with a dedicated library (React Query/SWR) rather than useEffect + useState
- Provide key props that are stable and unique, never array index for reorderable lists
- Handle loading, error, and empty states explicitly in every data-fetching component
- Sanitize any HTML passed to dangerouslySetInnerHTML
- Co-locate related state instead of lifting everything to a global store by default

**MUST NOT DO**
- Call hooks conditionally or inside loops
- Use array index as a key for a list that can reorder, filter, or have items removed
- Store server data in component state without a cache/invalidation strategy
- Overuse Context for state that only a couple of components need
- Mutate state directly instead of using the setter/reducer
- Use dangerouslySetInnerHTML with unsanitized user input
- Add useEffect for logic that can be computed directly during render
- Test implementation details (internal state, function calls) instead of observable behavior

## Output Templates

When implementing, provide:

1. Component implementation with clear prop types
2. Custom hooks extracted where logic is reusable
3. React Testing Library tests
4. A brief note on the state-management choice made
5. Any accessibility considerations addressed

## Knowledge Reference

React 18/19, hooks, Context, React Server Components, React Query/SWR, React Testing Library, Vitest/Jest, memoization (memo/useMemo/useCallback), code splitting/lazy, ARIA/accessibility