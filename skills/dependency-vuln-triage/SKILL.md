---
name: dependency-vuln-triage
description: Scans package manifests and lockfiles across npm, pip, and Maven for known CVEs, then ranks each finding by exploitability, reachability in your code, and available patch path.
argument-hint: [lockfile-or-manifest-path]
---

# Dependency Vulnerability Triage

Cuts through hundreds of CVE alerts to the handful that are actually exploitable in your codebase.

## Input

$ARGUMENTS

## How It Works

1. Parse manifests and lockfiles to build a full transitive dependency tree
2. Cross-reference every package version against known vulnerability advisories
3. Statically trace import graphs to check whether vulnerable code paths are actually reachable
4. Score each finding using exploitability, reachability, and patch-availability weights
5. Produce a ranked remediation list with exact upgrade targets and breaking-change warnings