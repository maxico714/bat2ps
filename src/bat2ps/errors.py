"""Structured errors carrying stable rule-ids (BPxxx)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bat2PsError(Exception):
    """Base error with rule id, location and profile version."""

    rule_id: str
    message: str
    lineno: int = 0
    profile: str = "v0.1"

    def __str__(self) -> str:
        loc = f"line {self.lineno}: " if self.lineno else ""
        return f"unsupported: {self.rule_id}: {loc}{self.message}"

    @property
    def args(self) -> tuple[str, ...]:  # type: ignore[override]
        return (str(self),)


class ParseError(Bat2PsError):
    """Raised for malformed batch that cannot be parsed."""


class ProfileError(Bat2PsError):
    """Raised for well-formed batch outside the constrained profile."""


class EmitError(Bat2PsError):
    """Raised when the emitter cannot represent a node."""


class HarnessError(Bat2PsError):
    """Raised for harness/environment failures (exit-code class 3)."""
