"""
Audio analysis module using librosa.
Performs BPM detection, onset strength analysis, emotion estimation,
and rhythm curve extraction.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import numpy as np

from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioAnalysisResult:
    bpm: float = 0.0
    bpm_category: str = "unknown"
    emotion: str = "neutral"
    emotion_confidence: float = 0.0
    onset_curve: list[float] = field(default_factory=list)
    onset_times: list[float] = field(default_factory=list)
    avg_onset_strength: float = 0.0
    speech_ratio: float = 0.0
    music_ratio: float = 0.0
    key_features: dict = field(default_factory=dict)


class AudioAnalyzer:
    """Audio analysis using librosa for BPM, onset, and emotion detection."""

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self._categories = {
            (0, 70): "calm",
            (70, 100): "medium",
            (100, 130): "active",
            (130, 160): "energetic",
            (160, 999): "tense",
        }
        self._emotion_map = {
            "calm": "calm/舒缓",
            "medium": "neutral/平稳",
            "active": "happy/活跃",
            "energetic": "energetic/激情",
            "tense": "tense/紧张",
        }

    async def analyze(self, audio_path: str) -> AudioAnalysisResult:
        """Analyze audio file: BPM, onset, rhythm, emotion."""

        def _analyze():
            import librosa

            result = AudioAnalysisResult()

            try:
                # Load audio
                y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)
                duration = librosa.get_duration(y=y, sr=sr)

                if duration < 0.5:
                    logger.warning("Audio too short for analysis")
                    return result

                # BPM detection
                tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
                result.bpm = (
                    float(tempo)
                    if isinstance(tempo, (int, float, np.floating))
                    else float(tempo[0])
                    if hasattr(tempo, "__len__")
                    else 0.0
                )
                result.bpm_category = self._get_bpm_category(result.bpm)
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                result.key_features["beat_count"] = len(beat_times)

                # Onset strength curve (rhythm analysis)
                onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                # Downsample to ~1 point per second for storage efficiency
                target_points = max(50, int(duration))
                if len(onset_env) > target_points:
                    indices = np.linspace(0, len(onset_env) - 1, target_points, dtype=int)
                    onset_sampled = onset_env[indices]
                else:
                    onset_sampled = onset_env

                # Normalize onset curve to 0-1
                onset_max = onset_sampled.max() if onset_sampled.max() > 0 else 1
                result.onset_curve = (onset_sampled / onset_max).tolist()
                result.onset_times = librosa.times_like(onset_env, sr=sr)[
                    :: max(1, len(onset_env) // target_points)
                ].tolist()
                result.avg_onset_strength = float(onset_sampled.mean() / onset_max)

                # Spectral features for emotion estimation
                spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
                spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
                zero_crossing_rate = librosa.feature.zero_crossing_rate(y=y)[0]

                result.key_features["spectral_centroid_mean"] = float(spectral_centroids.mean())
                result.key_features["spectral_rolloff_mean"] = float(spectral_rolloff.mean())
                result.key_features["zcr_mean"] = float(zero_crossing_rate.mean())

                # Simple emotion estimation based on BPM + spectral features
                result.emotion, result.emotion_confidence = self._estimate_emotion(
                    result.bpm,
                    float(spectral_centroids.mean()),
                    float(zero_crossing_rate.mean()),
                )

                # Simple speech vs music heuristic
                # Speech: high ZCR variability, lower spectral centroid
                # Music: more stable, often higher energy in low frequencies
                zcr_std = float(zero_crossing_rate.std())
                if zcr_std > 0.02:
                    result.speech_ratio = 0.7
                    result.music_ratio = 0.3
                else:
                    result.speech_ratio = 0.2
                    result.music_ratio = 0.8

                # RMS energy curve for dynamic range
                rms = librosa.feature.rms(y=y)[0]
                result.key_features["rms_mean"] = float(rms.mean())
                result.key_features["rms_std"] = float(rms.std())
                result.key_features["dynamic_range"] = float((rms.max() - rms.min()) / (rms.mean() + 1e-6))

                logger.info(
                    f"[audio] BPM={result.bpm:.0f}, category={result.bpm_category}, "
                    f"emotion={result.emotion}, onsets={len(result.onset_curve)}"
                )

            except Exception as e:
                logger.error(f"[audio] Analysis failed: {e}")

            return result

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _analyze)

    def _get_bpm_category(self, bpm: float) -> str:
        for (low, high), cat in self._categories.items():
            if low <= bpm < high:
                return cat
        return "unknown"

    def _estimate_emotion(self, bpm: float, spectral_centroid: float, zcr: float) -> tuple[str, float]:
        """Simple rule-based emotion estimation from audio features."""
        # Base emotion from BPM
        if bpm < 70:
            emotion, conf = "calm", 0.6
        elif bpm < 100:
            emotion, conf = "neutral", 0.5
        elif bpm < 130:
            emotion, conf = "happy", 0.6
        elif bpm < 160:
            emotion, conf = "energetic", 0.7
        else:
            emotion, conf = "tense", 0.6

        # Adjust based on spectral features
        # High spectral centroid = brighter sound = more energetic
        if spectral_centroid > 3000:
            if emotion in ("calm", "neutral"):
                emotion = "happy"
                conf = min(conf + 0.1, 0.9)
        elif spectral_centroid < 1000:
            if emotion in ("energetic", "tense"):
                emotion = "dramatic"
                conf = min(conf + 0.1, 0.9)

        return self._emotion_map.get(emotion, emotion), conf
