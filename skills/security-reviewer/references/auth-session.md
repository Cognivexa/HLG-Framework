# Authentication & Session Security

## Password Storage

Hash with a memory-hard, adaptive algorithm — argon2id or bcrypt — never a fast general-purpose hash (MD5, SHA-1, SHA-256 alone), which is exactly what makes offline brute-forcing of a leaked hash database cheap.

## Session Fixation

Regenerate the session identifier on login (and on any privilege change), rather than reusing whatever session ID existed before authentication — otherwise an attacker who can set a victim's session ID before login can hijack the now-authenticated session.

## Token Handling

Store bearer tokens/JWTs client-side in a way that isn't reachable by JavaScript when possible (an HttpOnly cookie) to limit XSS-driven token theft. If a JWT must be readable by client JS, keep its lifetime short and pair it with a separate, HttpOnly refresh token.

## Session/Cookie Flags

```
Set-Cookie: session=...; HttpOnly; Secure; SameSite=Lax
```

`HttpOnly` blocks JavaScript access (mitigates XSS token theft), `Secure` blocks transmission over plain HTTP, and `SameSite` reduces CSRF exposure. Use `SameSite=Strict` for the most sensitive cookies where the UX cost is acceptable.

## Multi-Factor & Rate Limiting

Rate-limit login and password-reset endpoints per account and per IP, and treat repeated failures as a signal to require MFA or lock the account temporarily — unlimited login attempts turn any password policy into a formality.
