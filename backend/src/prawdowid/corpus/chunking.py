"""Splits documents into ~800–1,200 character chunks on paragraph/sentence boundaries, with
overlap."""

from prawdowid.core.text import normalize_whitespace, split_sentences

TARGET_CHARS = 1000
MAX_CHARS = 1200
OVERLAP_SENTENCES = 1


def get_units(text: str) -> list[str]:
    units: list[str] = []
    for paragraph in text.split("\n"):
        paragraph = normalize_whitespace(paragraph)
        if not paragraph:
            continue
        if len(paragraph) <= MAX_CHARS:
            units.append(paragraph)
            continue
        units.extend(get_sentence_units(paragraph))
    return units


def get_sentence_units(paragraph: str) -> list[str]:
    units: list[str] = []
    for sentence in split_sentences(paragraph):
        while len(sentence) > MAX_CHARS:
            cut = sentence.rfind(" ", 0, MAX_CHARS)
            cut = cut if cut > 0 else MAX_CHARS
            units.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            units.append(sentence)
    return units


def get_chunks(text: str, title: str | None = None) -> list[str]:
    units = get_units(text)
    chunks: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and len(" ".join([*current, unit])) > MAX_CHARS:
            chunks.append(" ".join(current))
            tail = split_sentences(current[-1])[-OVERLAP_SENTENCES:]
            current = tail if len(" ".join(tail)) < TARGET_CHARS // 2 else []
        current.append(unit)
        if len(" ".join(current)) >= TARGET_CHARS:
            chunks.append(" ".join(current))
            tail = split_sentences(current[-1])[-OVERLAP_SENTENCES:]
            current = tail if len(" ".join(tail)) < TARGET_CHARS // 2 else []
    if current and (not chunks or " ".join(current) not in chunks[-1]):
        chunks.append(" ".join(current))
    if title and chunks and title not in chunks[0]:
        chunks[0] = (
            f"{title}. {chunks[0]}" if len(chunks[0]) + len(title) < MAX_CHARS else chunks[0]
        )
    return chunks
