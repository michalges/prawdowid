"""Polish-aware text normalization shared by ingest, retrieval and citation checks."""

import re
import unicodedata

POLISH_FOLD = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
TOKEN_PATTERN = re.compile(r"[0-9]+(?:[.,][0-9]+)*|[^\W\d_]+", re.UNICODE)
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?…])\s+(?=[\"„«(]?[A-ZĄĆĘŁŃÓŚŹŻ0-9])")
STEM_LENGTH = 5

STOPWORDS = frozenset(
    """a aby ale albo ani az bardzo bez bo by byc byl byla byli bylo co czy dla do gdy gdzie go
    i ich ile im inne ja jak jaki jako je jego jej jest jestem jeszcze jesli juz ktora ktore
    ktory ma mi mnie moze na nad nam nas nie niej nim no o od oraz po pod przez przy sa sie
    sobie tak tam te tego tej ten to tu tylko tym u w we wiec wszystko z za ze zostal zostala
    the of and or in on to is are was were be by for with that this it as at from""".split()
)


def fold_diacritics(text: str) -> str:
    folded = text.translate(POLISH_FOLD)
    decomposed = unicodedata.normalize("NFKD", folded)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_match(text: str) -> str:
    """Lowercased, diacritics-folded, punctuation-light form used to compare quotes with chunks."""
    unified_quotes = re.sub(r"[„”“\"«»‚‘’']", '"', text)
    unified_dashes = re.sub(r"[–—−]", "-", unified_quotes)
    return normalize_whitespace(fold_diacritics(unified_dashes).lower())


def get_tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(fold_diacritics(text).lower())


def get_stem(token: str) -> str:
    return token if token.isdigit() else token[:STEM_LENGTH]


def get_content_stems(text: str) -> list[str]:
    """Prefix stems of non-stopword tokens: a crude but robust answer to Polish inflection."""
    return [
        get_stem(token) for token in get_tokens(text) if token not in STOPWORDS and len(token) > 1
    ]


def get_index_text(text: str) -> str:
    return " ".join(get_content_stems(text))


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_SPLIT_PATTERN.split(text) if sentence.strip()]


def get_lexical_overlap(query: str, document: str) -> float:
    """Share of the query's distinct content stems that occur in the document (0..1)."""
    query_stems = set(get_content_stems(query))
    if not query_stems:
        return 0.0
    document_stems = set(get_content_stems(document))
    return len(query_stems & document_stems) / len(query_stems)
