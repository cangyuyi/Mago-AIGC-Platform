"""
Keyframe extraction from video shots using FFmpeg and OpenCV.
Extracts the middle frame of each detected shot for visual analysis.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import cv2

from src.common.logger import get_logger
from src.video_tools.scene_detect import Shot

logger = get_logger(__name__)


class KeyframeExtractor:
    """Extracts representative keyframes from each shot in a video."""

    def __init__(self, output_dir: str | None = None, ffmpeg_path: str = "ffmpeg"):
        self.output_dir = Path(output_dir or "/tmp/mago_keyframes")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = ffmpeg_path

    async def extract_keyframes(
        self,
        video_path: str,
        shots: list[Shot],
        video_id: str = "video",
        max_width: int = 640,
    ) -> list[dict]:
        """
        Extract keyframes for each shot. Returns list of {shot_index, path, timestamp}.
        Uses OpenCV for frame extraction (no ffmpeg subprocess needed for basic extraction).
        """
        keyframes = []

        def _extract():
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Cannot open video: {video_path}")
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            results = []

            for shot in shots:
                # Extract middle frame of the shot
                mid_time = (shot.start_time + shot.end_time) / 2
                frame_num = int(mid_time * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                if not ret:
                    # Try start frame
                    cap.set(cv2.CAP_PROP_POS_FRAMES, int(shot.start_time * fps) + 1)
                    ret, frame = cap.read()
                if not ret:
                    continue

                # Resize if needed
                h, w = frame.shape[:2]
                if w > max_width:
                    scale = max_width / w
                    frame = cv2.resize(frame, (max_width, int(h * scale)))

                # Save keyframe
                filename = f"{video_id}_shot_{shot.index:04d}.jpg"
                path = str(self.output_dir / filename)
                cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

                results.append(
                    {
                        "shot_index": shot.index,
                        "path": path,
                        "timestamp": mid_time,
                        "width": frame.shape[1],
                        "height": frame.shape[0],
                    }
                )

            cap.release()
            return results

        loop = asyncio.get_event_loop()
        keyframes = await loop.run_in_executor(None, _extract)
        logger.info(f"[keyframe] Extracted {len(keyframes)} keyframes")
        return keyframes

    def estimate_blur(self, image_path: str) -> float:
        """Estimate image blur using Laplacian variance (higher = sharper)."""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0.0
        return float(cv2.Laplacian(img, cv2.CV_64F).var())

    async def cleanup_keyframes(self, paths: list[str]) -> None:
        for path in paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
