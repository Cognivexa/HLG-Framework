# XSS & Output Encoding

## The Three Kinds

**Reflected** — untrusted input from the current request (a query param) is echoed back into the page without encoding. **Stored** — untrusted input is saved (a comment, a profile field) and rendered for other users later, making it more dangerous since it doesn't require tricking a victim into clicking a crafted link. **DOM-based** — client-side JavaScript writes untrusted data into the DOM (`innerHTML`, `document.write`) without the server ever seeing the payload.

## Context-Aware Encoding

The correct encoding depends on where the value lands:

```js
el.textContent = userInput                                   // HTML body
element.setAttribute('title', userInput)                     // HTML attribute — browser encodes via setAttribute
const url = `/search?q=${encodeURIComponent(userInput)}`      // URL
const json = JSON.stringify({ name: userInput })              // embedding in a <script> block
```

Using HTML-body encoding for a value placed inside a URL (or vice versa) still leaves an exploitable gap — encoding must match the sink, not just "be encoded somehow."

## Never Use innerHTML With Untrusted Data

`el.innerHTML = userInput` executes any `<script>` or event-handler attribute in the input. Use `textContent` for plain text, or a sanitizing library (DOMPurify) when the input must support a safe subset of HTML.

## Content Security Policy

A strict CSP (`script-src 'self'`, no `unsafe-inline`) is a second layer of defense that blocks injected scripts from executing even if an encoding gap slips through — treat it as defense in depth, not a substitute for correct encoding.
