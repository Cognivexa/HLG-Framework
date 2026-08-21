# Access Control

## Insecure Direct Object Reference (IDOR)

The most common real-world access-control bug: an endpoint takes an ID and returns/modifies the corresponding record without checking that the current user actually owns or may access it.

```js
// Vulnerable — any authenticated user can read any invoice by guessing IDs
app.get('/invoices/:id', (req, res) => res.json(db.invoices.findById(req.params.id)))

// Safe — ownership checked on every access
app.get('/invoices/:id', (req, res) => {
  const invoice = db.invoices.findById(req.params.id)
  if (!invoice || invoice.ownerId !== req.user.id) return res.sendStatus(403)
  res.json(invoice)
})
```

## Privilege Escalation

Check for both vertical escalation (a regular user reaching admin-only functionality) and horizontal escalation (a user reaching another user's data at the same privilege level, which is IDOR by another name). Test both directions explicitly — a review that only checks "can a logged-out user do this" misses most access-control bugs.

## Missing Function-Level Access Control

An admin action hidden from the UI for non-admins is not access control — if the underlying endpoint doesn't independently check the caller's role, anyone who discovers the URL can call it directly. Every sensitive endpoint must check authorization server-side regardless of what the UI shows.

## Default Deny

Design authorization so a missing or misconfigured rule denies access by default, rather than one that fails open — a bug in an allow-list is far safer than a bug in a deny-list.
