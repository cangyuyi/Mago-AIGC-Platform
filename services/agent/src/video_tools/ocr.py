"""
OCR module for detecting on-screen text in video frames.
Uses PaddleOCR for Chinese text recognition (best accuracy).
Falls back gracefully if PaddleOCR is not installed.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.common.logger import get_logger

logger = get_logger(__name__)


class OCREngine:
    """On-screen text detection using PaddleOCR."""

    def __init__(self, lang: str = "ch"):
        self.lang = lang
        self._ocr: Any | None = None

    async def _load(self):
        if self._ocr is not None:
            return
        try:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang, show_log=False)
            logger.info("[OCR] PaddleOCR loaded")
        except ImportError:
            logger.warning("PaddleOCR not available; OCR will be skipped")
            self._ocr = False  # Mark as unavailable (not None = attempted)

    async def extract_text(self, image_path: str) -> str:
        """Extract text from a single image."""
        await self._load()
        ocr_engine = self._ocr
        if not ocr_engine:
            return ""

        def _ocr() -> str:
            result = ocr_engine.ocr(image_path, cls=True)
            texts = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2:
                        texts.append(line[1][0])
            return "\n".join(texts)

        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(None, _ocr)
            return str(text)
        except Exception as e:
            logger.warning(f"[OCR] Failed on {image_path}: {e}")
            return ""

    async def extract_text_batch(self, image_paths: list[str]) -> dict[str, str]:
        """Extract text from multiple images."""
        results = {}
        for path in image_paths:
            results[path] = await self.extract_text(path)
        return results
