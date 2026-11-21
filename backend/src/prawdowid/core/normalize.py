"""Step 1: turns text / URL / image input into analysable text, or a non-verdict status."""

import base64
import binascii
import re
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from prawdowid.core.extract import extract_article
from prawdowid.core.fetch import FetchError, FetchErrorKind, SafeFetcher
from prawdowid.providers.ocr import OCRError, OCRProvider, OCRUnavailableError
from prawdowid.schemas import MAX_IMAGE_BYTES, CheckInput, InputType

URL_ONLY_PATTERN = re.compile(r"^\s*(https?://\S+)\s*$", re.IGNORECASE)
MAX_FETCHED_CHARS = 8000
IMAGE_SIGNATURES = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"RIFF", b"BM", b"II*\x00", b"MM\x00*")
CLIENT_FETCH_ERRORS = frozenset(
    {
        FetchErrorKind.BLOCKED_ADDRESS,
        FetchErrorKind.UNSUPPORTED_URL,
        FetchErrorKind.ROBOTS_DISALLOWED,
        FetchErrorKind.UNSUPPORTED_CONTENT,
        FetchErrorKind.TOO_LARGE,
        FetchErrorKind.HTTP_ERROR,
    }
)


class NormalizationOutcome(StrEnum):
    OK = "ok"
    NEEDS_CLARIFICATION = "needs_clarification"
    TECHNICAL_ERROR = "technical_error"


@dataclass
class NormalizedInput:
    outcome: NormalizationOutcome
    input_type: InputType
    user_text: str = ""
    url: str | None = None
    fetched_title: str | None = None
    fetched_text: str | None = None
    fetched_published_at: date | None = None
    ocr_text: str | None = None
    message_pl: str | None = None
    error_kind: str | None = None
    limitations_pl: list[str] = field(default_factory=list)

    @property
    def analysable_text(self) -> str:
        return "\n\n".join(
            part for part in (self.user_text, self.fetched_text, self.ocr_text) if part
        )


def get_effective_input(check_input: CheckInput) -> tuple[InputType, str, str | None]:
    """A text message that is only a link is treated as a URL check (share menus send links as
    plain text)."""
    if check_input.type is InputType.TEXT and check_input.text:
        url_match = URL_ONLY_PATTERN.match(check_input.text)
        if url_match:
            return InputType.URL, "", url_match.group(1)
        return InputType.TEXT, check_input.text.strip(), None
    if check_input.type is InputType.URL:
        return InputType.URL, (check_input.text or "").strip(), str(check_input.url)
    return InputType.IMAGE, (check_input.text or "").strip(), None


def get_image_bytes(image_b64: str) -> bytes | None:
    payload = image_b64.split(",", 1)[1] if image_b64.startswith("data:") else image_b64
    try:
        image = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(image) > MAX_IMAGE_BYTES or not image.startswith(IMAGE_SIGNATURES):
        return None
    return image


@dataclass
class InputNormalizer:
    fetcher: SafeFetcher
    ocr: OCRProvider

    async def normalize(self, check_input: CheckInput) -> NormalizedInput:
        input_type, user_text, url = get_effective_input(check_input)
        if input_type is InputType.URL and url:
            return await self._normalize_url(user_text, url)
        if input_type is InputType.IMAGE and check_input.image_b64:
            return await self._normalize_image(user_text, check_input.image_b64)
        return NormalizedInput(NormalizationOutcome.OK, InputType.TEXT, user_text=user_text)

    async def _normalize_url(self, user_text: str, url: str) -> NormalizedInput:
        result = NormalizedInput(
            NormalizationOutcome.OK, InputType.URL, user_text=user_text, url=url
        )
        try:
            page = await self.fetcher.fetch(url)
        except FetchError as error:
            result.error_kind = error.kind.value
            if error.kind in CLIENT_FETCH_ERRORS:
                result.outcome = NormalizationOutcome.NEEDS_CLARIFICATION
                result.message_pl = (
                    "Nie możemy pobrać treści spod tego linku (strona blokuje pobieranie, "
                    "wymaga logowania albo adres jest niedozwolony). Wklej tekst, który chcesz "
                    "sprawdzić."
                )
            else:
                result.outcome = NormalizationOutcome.TECHNICAL_ERROR
            return result
        article = extract_article(page.text, page.url)
        if article is None:
            result.outcome = NormalizationOutcome.NEEDS_CLARIFICATION
            result.message_pl = (
                "Nie udało się odczytać głównej treści strony. Wklej fragment, który chcesz "
                "sprawdzić."
            )
            return result
        result.fetched_title = article.title
        result.fetched_text = f"{article.title}\n{article.text[:MAX_FETCHED_CHARS]}"
        result.fetched_published_at = article.published_at
        if len(article.text) > MAX_FETCHED_CHARS:
            result.limitations_pl.append(
                "Strona jest długa: przeanalizowaliśmy tylko jej początek."
            )
        return result

    async def _normalize_image(self, user_text: str, image_b64: str) -> NormalizedInput:
        result = NormalizedInput(NormalizationOutcome.OK, InputType.IMAGE, user_text=user_text)
        image = get_image_bytes(image_b64)
        if image is None:
            result.outcome = NormalizationOutcome.NEEDS_CLARIFICATION
            result.message_pl = (
                "Nie rozpoznaliśmy pliku jako obrazu (PNG, JPG, GIF, WEBP, do 5 MB)."
            )
            return result
        try:
            text = await self.ocr.read_text(image)
        except OCRUnavailableError:
            result.outcome = NormalizationOutcome.TECHNICAL_ERROR
            result.error_kind = "ocr_unavailable"
            result.message_pl = (
                "Odczyt tekstu z obrazów jest teraz niedostępny. Przepisz lub wklej tekst ze "
                "zrzutu ekranu. To nie jest ocena prawdziwości."
            )
            return result
        except OCRError:
            result.outcome = NormalizationOutcome.TECHNICAL_ERROR
            result.error_kind = "ocr_failed"
            return result
        if len(text.split()) < 3:
            result.outcome = NormalizationOutcome.NEEDS_CLARIFICATION
            result.message_pl = "Na obrazie nie odczytaliśmy tekstu do sprawdzenia."
            return result
        result.ocr_text = text
        result.limitations_pl.append(
            "Tekst odczytaliśmy z obrazu automatycznie (OCR). Odczyt może zawierać błędy. "
            "Nie analizujemy, czy sam obraz został przerobiony."
        )
        return result
