# Performance & Security

## Profiling Before Optimizing

Use `cProfile` (or `py-spy` for a running process) to find the actual bottleneck before rewriting anything — intuition about what's slow in Python is wrong more often than not, especially around string operations and attribute access.

## The GIL

The Global Interpreter Lock means only one thread executes Python bytecode at a time in a given process. Threads still help for I/O-bound work (they release the GIL during I/O waits); for CPU-bound work, use `multiprocessing` or a separate process pool to get real parallelism.

## Pickle Risks

`pickle.loads()` on attacker-controlled data can execute arbitrary code during deserialization — it is not a safe format for anything crossing a trust boundary. Use `json` for data exchanged with clients or external services, and reserve `pickle` for trusted, internal-only caches your own process wrote.

## Injection

Use parameterized queries with your DB driver/ORM, never string-formatted SQL. The same principle applies to `subprocess` calls — pass arguments as a list, not a shell string, and avoid `shell=True` with any untrusted input.

## Dependency Hygiene

Run `pip-audit` regularly and keep the lockfile current — an outdated transitive dependency with a known CVE is exploitable regardless of how careful your own code is.
