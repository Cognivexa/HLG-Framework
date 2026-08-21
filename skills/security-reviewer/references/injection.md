# Injection Vulnerabilities

## SQL Injection

Any query built by concatenating untrusted input into a SQL string is exploitable, regardless of how the input is "sanitized" with escaping alone. Use parameterized queries or an ORM's binding, always:

```js
// Vulnerable
db.query(`SELECT * FROM users WHERE email = '${email}'`)

// Safe
db.query('SELECT * FROM users WHERE email = $1', [email])
```

## NoSQL Injection

Document stores are not immune — passing a raw object from user input directly into a query operator lets an attacker inject operators:

```js
// Vulnerable: { email: { $ne: null } } bypasses the intended equality check
db.users.find({ email: req.body.email })

// Safe: coerce to the expected primitive type first
db.users.find({ email: String(req.body.email) })
```

## Command Injection

Never pass unsanitized input to a shell: `exec`, `system`, or a template-string-built shell command. Use the array-argument form of your language's process-spawning API, which doesn't go through a shell at all:

```js
// Vulnerable
exec(`convert ${filename} out.png`)

// Safe — arguments passed directly, no shell interpretation
execFile('convert', [filename, 'out.png'])
```

## LDAP Injection

The same principle applies to LDAP filter strings — escape or reject metacharacters (`* ( ) \ NUL`) in any value interpolated into an LDAP query filter, or use a library that parameterizes filters instead of building them as strings.
