"""Heuristic prompt-injection detection (CONCEPT §7.5). Detection only logs and annotates; the real
defence is structural: delimiters, no tools, schema-validated output and code-checked citations."""

import re
from dataclasses import dataclass

from prawdowid.core.text import fold_diacritics

INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
        r"disregard (all |the )?(previous|prior|above|system) ",
        r"forget (all |your |the )?(previous |prior )?(instructions|rules)",
        r"you are now\b",
        r"new (system )?instructions?:",
        r"\b(system|developer|assistant)\s*(prompt|message)?\s*:",
        r"<\s*/?\s*(system|instructions?|im_start|im_end)\s*>",
        r"\[(system|inst)\]",
        r"(respond|answer|reply) (only )?with ['\"]?(potwierdzone|prawda|true|falszywe)",
        r"(mark|classify|label) (this|the claim) as (true|confirmed|verified)",
        r"zignoruj (wszystkie |wczesniejsze |poprzednie |powyzsze )*"
        r"(instrukcje|zasady|polecenia|reguly)",
        r"nie stosuj sie do (zasad|instrukcji|regul)",
        r"zapomnij (o )?(wszystkich |poprzednich )*(instrukcj|zasad|polecen)",
        r"(od teraz|teraz) jestes\b",
        r"nowe (instrukcje|polecenia|zasady)\s*:",
        r"(odpowiedz|odpowiadaj|zwroc) (tylko |wylacznie )?(ze|werdykt|slowem)? ?['\"]?"
        r"(potwierdzone|prawda|falszywe)",
        r"(uznaj|oznacz|ocen) (to|te|ten|twierdzenie)( twierdzenie)? (za|jako) (prawd|potwierdz)",
        r"(ujawnij|pokaz|wypisz) (swoj |swoje )?(prompt|instrukcje systemowe|klucz)",
    )
)
HIDDEN_TEXT_PATTERN = re.compile(r"[​-‏⁠-⁤﻿]|[\U000e0000-\U000e007f]")


@dataclass(frozen=True)
class InjectionFinding:
    location: str
    pattern: str
    excerpt: str


def get_injection_findings(text: str, location: str) -> list[InjectionFinding]:
    folded = fold_diacritics(text)
    findings = [
        InjectionFinding(
            location, pattern.pattern, folded[max(match.start() - 20, 0) : match.end() + 20]
        )
        for pattern in INJECTION_PATTERNS
        if (match := pattern.search(folded))
    ]
    if HIDDEN_TEXT_PATTERN.search(text):
        findings.append(InjectionFinding(location, "hidden_unicode", "zero-width / tag characters"))
    return findings


def get_stripped_hidden_text(text: str) -> str:
    return HIDDEN_TEXT_PATTERN.sub("", text)
