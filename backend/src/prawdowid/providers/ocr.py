"""Local OCR (Tesseract). Images never leave the host and are not stored after processing."""

import asyncio
import shutil
from dataclasses import dataclass
from typing import Protocol

OCR_TIMEOUT_S = 20.0


class OCRError(Exception):
    pass


class OCRUnavailableError(OCRError):
    pass


class OCRProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def read_text(self, image_bytes: bytes) -> str: ...


@dataclass(frozen=True)
class DisabledOCRProvider:
    @property
    def name(self) -> str:
        return "none"

    async def read_text(self, image_bytes: bytes) -> str:
        raise OCRUnavailableError("OCR is disabled")


@dataclass(frozen=True)
class TesseractOCRProvider:
    languages: str = "pol+eng"
    binary: str = "tesseract"

    @property
    def name(self) -> str:
        return f"tesseract/{self.languages}"

    async def read_text(self, image_bytes: bytes) -> str:
        executable = shutil.which(self.binary)
        if executable is None:
            raise OCRUnavailableError("tesseract binary not found")
        process = await asyncio.create_subprocess_exec(
            executable,
            "stdin",
            "stdout",
            "-l",
            self.languages,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(image_bytes), timeout=OCR_TIMEOUT_S
            )
        except TimeoutError as error:
            process.kill()
            raise OCRError("OCR timed out") from error
        if process.returncode != 0:
            raise OCRError(stderr.decode(errors="replace")[:300])
        return stdout.decode(errors="replace").strip()


@dataclass(frozen=True)
class StaticOCRProvider:
    """Test double that returns a fixed transcript."""

    text: str

    @property
    def name(self) -> str:
        return "static/test"

    async def read_text(self, image_bytes: bytes) -> str:
        return self.text
