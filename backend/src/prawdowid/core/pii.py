"""Masks obvious personal data before any LLM call and before storage (brief §5 "Prywatność")."""

import re
from collections.abc import Callable
from dataclasses import dataclass

PESEL_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)


def is_valid_pesel(digits: str) -> bool:
    checksum = sum(
        int(digit) * weight for digit, weight in zip(digits, PESEL_WEIGHTS, strict=False)
    )
    return (10 - checksum % 10) % 10 == int(digits[10])


def is_valid_luhn(number: str) -> bool:
    digits = [int(char) for char in number if char.isdigit()]
    total = 0
    for i, digit in enumerate(reversed(digits)):
        doubled = digit * 2 if i % 2 else digit
        total += doubled - 9 if doubled > 9 else doubled
    return len(digits) >= 13 and total % 10 == 0


@dataclass(frozen=True)
class PIIRule:
    label: str
    pattern: re.Pattern[str]
    is_match: Callable[[str], bool] = lambda _value: True


PHONE_CONTEXT = r"(?:tel\.?|telefon\w*|komórk\w*|kom\.|nr|numer\w*|dzwo\w*|sms\w*)"

PII_RULES = (
    PIIRule("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    PIIRule("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?\d{4}){5,7}\b")),
    PIIRule("NR_KONTA", re.compile(r"\b\d{2}(?:[ ]?\d{4}){6}\b")),
    PIIRule("KARTA", re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), is_valid_luhn),
    PIIRule("PESEL", re.compile(r"\b\d{11}\b"), is_valid_pesel),
    PIIRule("TELEFON", re.compile(r"(?:\+|00)48[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}(?!\d)")),
    PIIRule("TELEFON", re.compile(r"\b\d{3}-\d{3}-\d{3}\b")),
    PIIRule("TELEFON", re.compile(r"\b[4-8]\d{8}\b")),
    PIIRule(
        "TELEFON",
        re.compile(
            rf"(?P<prefix>{PHONE_CONTEXT}\D{{0,15}}?)(?P<value>\d{{3}} \d{{3}} \d{{3}})\b",
            re.IGNORECASE,
        ),
    ),
    PIIRule("DOWOD", re.compile(r"\b[A-Z]{3}[ ]?\d{6}\b")),
)


@dataclass(frozen=True)
class MaskResult:
    text: str
    masked_counts: dict[str, int]


def get_masked_text(text: str) -> MaskResult:
    counts: dict[str, int] = {}
    masked = text
    for rule in PII_RULES:

        def replace(match: re.Match[str], rule: PIIRule = rule) -> str:
            groups = match.groupdict()
            value = groups.get("value") or match.group(0)
            if not rule.is_match(value):
                return match.group(0)
            counts[rule.label] = counts.get(rule.label, 0) + 1
            return f"{groups.get('prefix') or ''}[{rule.label}]"

        masked = rule.pattern.sub(replace, masked)
    return MaskResult(text=masked, masked_counts=counts)
