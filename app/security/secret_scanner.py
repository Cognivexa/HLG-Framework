"""Offline secret detection: API keys, generic secrets, passwords, private keys.

Fully local — regex signatures for well-known key formats plus a Shannon-entropy
heuristic for opaque high-entropy strings assigned to credential-shaped names.
Never calls out to a network CVE feed (unlike dependency_scanner), so this step
always runs, even with no internet access.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

CATEGORY_API_KEY = "api_key"
CATEGORY_SECRET = "secret"
CATEGORY_PASSWORD = "password"
CATEGORY_PRIVATE_KEY = "private_key"

_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    (CATEGORY_API_KEY, "AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        CATEGORY_API_KEY,
        "AWS Secret Access Key",
        re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*['\"][A-Za-z0-9/+=]{40}['\"]"),
    ),
    (CATEGORY_API_KEY, "Google API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    (CATEGORY_API_KEY, "OpenAI-style API Key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    (CATEGORY_API_KEY, "Anthropic API Key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    (CATEGORY_API_KEY, "Slack Token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (CATEGORY_API_KEY, "GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    (
        CATEGORY_PRIVATE_KEY,
        "PEM Private Key Block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    (
        CATEGORY_PASSWORD,
        "Hardcoded password assignment",
        # No leading \b: real-world names are commonly prefixed, e.g.
        # DB_PASSWORD — the "_" before "PASSWORD" is a word character, so a
        # leading \b would never match there.
        re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"\s]{4,}['\"]"),
    ),
    (
        CATEGORY_SECRET,
        "Generic secret assignment",
        re.compile(r"(?i)(secret|token|api_key|apikey|access_key)\s*[=:]\s*['\"][^'\"\s]{8,}['\"]"),
    ),
]

_ENTROPY_ASSIGNMENT = re.compile(
    r"(?i)(secret|token|key|password|credential)\w*\s*[=:]\s*['\"]([A-Za-z0-9+/_\-]{20,})['\"]"
)


@dataclass
class SecretFinding:
    category: str
    rule_name: str
    file: str
    line: int
    snippet: str


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _redact(snippet: str) -> str:
    return snippet[:60] + ("…" if len(snippet) > 60 else "")


def scan_text(text: str, file_label: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for category, rule_name, pattern in _PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(category, rule_name, file_label, lineno, _redact(line.strip())))
        match = _ENTROPY_ASSIGNMENT.search(line)
        if match and _shannon_entropy(match.group(2)) >= 4.0:
            findings.append(
                SecretFinding(
                    CATEGORY_SECRET,
                    "High-entropy credential-like value",
                    file_label,
                    lineno,
                    _redact(line.strip()),
                )
            )
    return findings


def scan_files(paths: list[Path]) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings.extend(scan_text(text, str(path)))
    return findings


def filter_by_category(findings: list[SecretFinding], category: str) -> list[SecretFinding]:
    return [f for f in findings if f.category == category]
