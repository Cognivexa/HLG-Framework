# Accessibility & Security

## Semantic HTML First

Use a native `<button>`, `<a>`, or form element before reaching for a `<div>` with an `onClick` and ARIA attributes bolted on — native elements come with keyboard interaction, focus behavior, and screen-reader semantics for free that a div-based reimplementation has to hand-build and will likely miss edge cases on.

## Focus Management

When a modal opens, move focus into it and trap it there until closed; when it closes, return focus to the element that opened it. Losing focus management is one of the most common accessibility regressions in custom overlay components.

## ARIA as a Last Resort

ARIA attributes describe a custom widget to assistive technology, but they don't provide any behavior — adding `role="button"` to a div doesn't give it keyboard activation on Enter/Space; that still has to be implemented by hand. Prefer a native element wherever one exists for the job.

## dangerouslySetInnerHTML

Any use of `dangerouslySetInnerHTML` with content derived from user input is a stored/reflected XSS risk. If rendering rich text or Markdown-derived HTML is genuinely required, sanitize it with a library like DOMPurify immediately before rendering, not at some earlier point in the pipeline that a later refactor could bypass.
