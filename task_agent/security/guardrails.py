import re
import os
from pathlib import Path
from typing import Optional

class SecurityViolationError(Exception):
    """Raised when an operation violates security policy."""
    pass

class SecurityGuardrail:
    """Security guardrail to block dangerous system commands and path traversal."""

    DANGEROUS_PATTERNS = [
        r"\brm\s+-[rf]*\s+/",
        r"\bformat\s+[a-zA-Z]:",
        r"\bdel\s+/[fFqQsS]",
        r"remove-item.*-force",
        r"remove-item.*-recurse.*-force",
        r"\bdrop\s+database\b",
        r"\bshutdown\b",
        r"\bmkfs\b",
        r">\s*/dev/sd[a-z]",
    ]

    def __init__(self, allowed_root: Optional[str] = None):
        self.allowed_root = Path(allowed_root).resolve() if allowed_root else None
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS
        ]

    def validate_command(self, command: str) -> bool:
        """Validate if a shell command is safe to execute."""
        trimmed = command.strip()
        for pattern in self._compiled_patterns:
            if pattern.search(trimmed):
                raise SecurityViolationError(f"Command blocked by security policy: {command}")
        return True

    def validate_path(self, target_path: str) -> Path:
        """Validate that target_path does not escape allowed root."""
        resolved = Path(target_path).resolve()
        if self.allowed_root:
            try:
                resolved.relative_to(self.allowed_root)
            except ValueError:
                raise SecurityViolationError(
                    f"Path traversal blocked: '{target_path}' is outside allowed root '{self.allowed_root}'"
                )
        return resolved
