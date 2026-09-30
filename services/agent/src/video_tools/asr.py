"""
Automatic Speech Recognition (ASR) module.
Supports two engines:
  - whisper: faster-whisper (CTranslate2 accelerated, good multilingual)
  - funasr: FunASR paraformer-zh (Chinese SOTA)
Default uses Whisper (faster-whisper) for broad compatibility.
Outputs word-level timestamps for shot alignment.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Word:
    word: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class TranscriptResult:
    text: str
    language: str
    words: list[Word] = field(default_factory=list)
    segments: list[dict] = field(default_factory=list)
    engine: str = "whisper"


class ASREngine:
    """
    Speech recognition engine.
    Defaults to faster-whisper with large-v3 model.
    Falls back to a mock engine if models are not available.
    """

    def __init__(self, engine: str = "whisper", model_size: str = "base"):
        self.engine = engine
        self.model_size = model_size
        self._model: Any | None = None

    async def _load_model(self):
        """Load ASR model lazily."""
        if self._model is not None:
            return

        if self.engine == "whisper":
            try:
                from faster_whisper import WhisperModel

                # Use base model for development; large-v3 for production
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info(f"[ASR] Loaded faster-whisper model: {self.model_size}")
            except ImportError:
                logger.warning("faster-whisper not available; ASR will be unavailable")
                self._model = None
        elif self.engine == "funasr":
            try:
                from funasr import AutoModel

                self._model = AutoModel(
                    model="paraformer-zh",
                    model_revision="v2.0.4",
                    vad_model="fsmn-vad",
                    vad_kwargs={"max_single_segment_time": 30000},
                    punc_model="ct-punc",
                )
                logger.info("[ASR] Loaded FunASR paraformer-zh model")
            except ImportError:
                logger.warning("FunASR not available; ASR will be unavailable")
                self._model = None

    async def transcribe(self, audio_path: str, language: str | None = None) -> TranscriptResult:
        """
        Transcribe audio file to text with word-level timestamps.

        Args:
            audio_path: Path to audio file (WAV, 16kHz recommended)
            language: Language code (zh, en, auto-detect if None)

        Returns:
            TranscriptResult with text, words, segments, language
        """
        await self._load_model()

        if self._model is None:
            logger.warning("[ASR] No model available, returning empty transcript")
            return TranscriptResult(text="", language=language or "zh", engine="none")

        if self.engine == "whisper":
            return await self._transcribe_whisper(audio_path, language)
        elif self.engine == "funasr":
            return await self._transcribe_funasr(audio_path)

        return TranscriptResult(text="", language="zh", engine="none")

    async def _transcribe_whisper(self, audio_path: str, language: str | None) -> TranscriptResult:
        """Transcribe using faster-whisper."""

        model = self._model
        if model is None:
            return TranscriptResult(text="", language=language or "zh", engine="none")

        def _transcribe():
            segments, info = model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                vad_filter=True,
                beam_size=5,
            )
            words = []
            seg_list = []
            full_text_parts = []

            for seg in segments:
                seg_dict = {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                }
                seg_list.append(seg_dict)
                full_text_parts.append(seg.text.strip())
                if seg.words:
                    for w in seg.words:
                        words.append(
                            Word(
                                word=w.word.strip(),
                                start=w.start,
                                end=w.end,
                                confidence=getattr(w, "probability", 1.0),
                            )
                        )

            return TranscriptResult(
                text=" ".join(full_text_parts),
                language=info.language,
                words=words,
                segments=seg_list,
                engine="whisper",
            )

        loop = asyncio.get_event_loop()
        result = cast(TranscriptResult, await loop.run_in_executor(None, _transcribe))
        logger.info(f"[ASR] Transcribed {len(result.words)} words, language={result.language}")
        return result

    async def _transcribe_funasr(self, audio_path: str) -> TranscriptResult:
        """Transcribe using FunASR (Chinese-optimized)."""

        model = self._model
        if model is None:
            return TranscriptResult(text="", language="zh", engine="none")

        def _transcribe():
            res = model.generate(input=audio_path, batch_size_s=300)
            text = ""
            words = []
            if res and len(res) > 0:
                text = res[0].get("text", "")
                # FunASR returns timestamp info in res[0]["timestamp"]
                timestamps = res[0].get("timestamp", [])
                if timestamps:
                    for ts in timestamps:
                        if len(ts) >= 3:
                            words.append(
                                Word(
                                    word=ts[0] if isinstance(ts[0], str) else "",
                                    start=ts[1] / 1000.0 if isinstance(ts[1], (int, float)) else 0,
                                    end=ts[2] / 1000.0 if isinstance(ts[2], (int, float)) else 0,
                                )
                            )
            return TranscriptResult(
                text=text,
                language="zh",
                words=words,
                engine="funasr",
            )

        loop = asyncio.get_event_loop()
        result = cast(TranscriptResult, await loop.run_in_executor(None, _transcribe))
        logger.info(f"[ASR] FunASR transcribed, text length={len(result.text)}")
        return result

    def get_words_for_time_range(self, words: list[Word], start: float, end: float) -> list[Word]:
        """Get words that fall within a time range (for shot alignment)."""
        return [w for w in words if w.start >= start and w.end <= end + 0.2]

    def get_text_for_time_range(self, words: list[Word], start: float, end: float) -> str:
        """Get text transcript for a time range."""
        range_words = self.get_words_for_time_range(words, start, end)
        return "".join(w.word for w in range_words)
