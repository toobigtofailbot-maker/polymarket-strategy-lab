import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
}

ALLOWLIST_MARKERS = {
    "DO_NOT_COMMIT",
    "PLACEHOLDER_ONLY",
    "EXAMPLE_ONLY",
    "REDACTED",
    "N/A",
}

FORBIDDEN_REGEXES = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bmnemonic(?:_phrase)?\b\s*[:=]\s*['\"][^'\"]{20,}['\"]", re.IGNORECASE),
    re.compile(r"\bseed(?:_phrase)?\b\s*[:=]\s*['\"][^'\"]{20,}['\"]", re.IGNORECASE),
    re.compile(r"\b(?:POLY_API_KEY|POLY_PASSPHRASE|KALSHI_API_KEY)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}['\"]?", re.IGNORECASE),
]


def iter_project_text_files():
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def is_allowlisted(line: str) -> bool:
    return any(marker in line for marker in ALLOWLIST_MARKERS)


def test_no_env_files_committed():
    env_files = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob(".env*")
        if ".git" not in path.parts and path.is_file() and path.name != ".env.example"
    ]
    assert env_files == []


def test_no_realistic_secret_values_in_text_files():
    findings = []
    for path in iter_project_text_files():
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if is_allowlisted(line):
                continue
            for pattern in FORBIDDEN_REGEXES:
                if pattern.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}")
    assert findings == []

