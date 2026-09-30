"""
Video downloader using yt-dlp.
Downloads videos from public URLs for analysis.
Supports: douyin, kuaishou, bilibili, youtube, and many other platforms.
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from src.common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DownloadResult:
    success: bool
    video_path: str | None = None
    audio_path: str | None = None
    thumbnail_path: str | None = None
    title: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    platform: str | None = None
    video_id: str | None = None
    author: str | None = None
    description: str | None = None
    error: str | None = None
    file_size_mb: float = 0.0


class VideoDownloader:
    """Downloads videos using yt-dlp with configurable output directory."""

    def __init__(self, output_dir: str | None = None, ffmpeg_path: str | None = None):
        from src.config import get_settings

        _settings = get_settings()
        self.output_dir = Path(output_dir or _settings.video_temp_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = ffmpeg_path or _settings.ffmpeg_path

    async def download(
        self,
        url: str,
        extract_audio: bool = True,
        max_duration: int = 300,  # 5 minutes max for analysis
        quality: str = "best[height<=1080]",
    ) -> DownloadResult:
        """
        Download a video and optionally extract audio track.

        Args:
            url: Video URL
            extract_audio: Whether to extract audio as separate file
            max_duration: Maximum video duration in seconds
            quality: yt-dlp format selector

        Returns:
            DownloadResult with paths and metadata
        """
        try:
            self._validate_url(url)
        except (TypeError, ValueError):
            logger.warning("download_rejected host=%s", self._safe_url_host(url))
            return DownloadResult(success=False, error="video URL is not allowed")

        logger.info("downloading_video host=%s", self._safe_url_host(url))
        output_template = str(self.output_dir / "%(id)s.%(ext)s")

        ydl_opts = {
            "format": quality,
            "outtmpl": output_template,
            "ffmpeg_location": self._find_ffmpeg(),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
            # Download video metadata
            "writethumbnail": False,
            # Timeout settings
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
        }

        if extract_audio:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ]
            ydl_opts["postprocessor_args"] = ["-ar", "16000", "-ac", "1"]
            # Store audio path separately (will be computed after download)

        try:
            result = await self._run_ytdlp(url, ydl_opts, extract_audio, max_duration)
            return result
        except Exception as e:
            logger.error("download_failed host=%s error_type=%s", self._safe_url_host(url), type(e).__name__)
            return DownloadResult(success=False, error="video download failed")

    async def _run_ytdlp(self, url: str, opts: dict, extract_audio: bool, max_duration: int) -> DownloadResult:
        """Run yt-dlp in a thread pool (yt-dlp is synchronous)."""
        import yt_dlp

        def _download():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info

        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _download)

        if not info:
            return DownloadResult(success=False, error="No info extracted")

        video_id = info.get("id", "unknown")
        duration = info.get("duration")

        if duration and duration > max_duration:
            logger.warning(f"Video {video_id} duration {duration}s exceeds max {max_duration}s, truncating")
            # Don't reject, but note it for analysis

        video_ext = info.get("ext", "mp4")
        video_path = str(self.output_dir / f"{video_id}.{video_ext}")
        audio_path = str(self.output_dir / f"{video_id}_audio.wav") if extract_audio else None

        # Check file size
        file_size_mb = 0.0
        if os.path.exists(video_path):
            file_size_mb = os.path.getsize(video_path) / (1024 * 1024)

        # If audio was extracted, verify it exists
        if extract_audio and audio_path and not os.path.exists(audio_path):
            # Try common extensions
            for ext in ["wav", "mp3", "m4a", "opus"]:
                candidate = str(self.output_dir / f"{video_id}_audio.{ext}")
                if os.path.exists(candidate):
                    audio_path = candidate
                    break
            else:
                audio_path = None

        thumbnail = info.get("thumbnail")
        if thumbnail and not os.path.exists(str(thumbnail)):
            thumbnail = None

        logger.info(f"Downloaded: {info.get('title', video_id)} ({duration}s, {file_size_mb:.1f}MB)")

        return DownloadResult(
            success=True,
            video_path=video_path if os.path.exists(video_path) else None,
            audio_path=audio_path,
            title=info.get("title"),
            duration=duration,
            width=info.get("width"),
            height=info.get("height"),
            platform=info.get("extractor_key", "").lower(),
            video_id=video_id,
            author=info.get("uploader") or info.get("channel"),
            description=info.get("description"),
            file_size_mb=file_size_mb,
        )

    @classmethod
    def _validate_url(cls, url: str) -> str:
        """Reject local, private, and otherwise non-public URLs before yt-dlp runs."""
        if not isinstance(url, str):
            raise ValueError("URL must be a string")
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
        except ValueError as exc:
            raise ValueError("invalid URL") from exc

        if parsed.scheme.lower() not in {"http", "https"} or not hostname:
            raise ValueError("only public HTTP(S) URLs are allowed")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("URL credentials are not allowed")

        hostname = hostname.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
            raise ValueError("local hostnames are not allowed")

        try:
            addresses = [ipaddress.ip_address(hostname)]
        except ValueError:
            addresses = cls._resolve_host_addresses(hostname)

        if not addresses or any(cls._is_non_public_address(address) for address in addresses):
            raise ValueError("non-public address is not allowed")
        return hostname

    @staticmethod
    def _resolve_host_addresses(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            results = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise ValueError("host could not be resolved") from exc
        return list({ipaddress.ip_address(result[4][0]) for result in results})

    @staticmethod
    def _is_non_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        return (
            not address.is_global
            or address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
            or getattr(address, "is_site_local", False)
        )

    @staticmethod
    def _safe_url_host(url: str) -> str:
        """Return only the hostname for logs; never log credentials or query parameters."""
        try:
            return urlsplit(url).hostname or "unknown"
        except (TypeError, ValueError):
            return "invalid"

    def _find_ffmpeg(self) -> str:
        """Find ffmpeg binary."""
        # Check project tools directory first
        project_ffmpeg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".tools", "ffmpeg", "ffmpeg"
        )
        if os.path.exists(project_ffmpeg) and os.access(project_ffmpeg, os.X_OK):
            return project_ffmpeg
        return self.ffmpeg_path

    async def cleanup(self, *paths: str) -> None:
        """Remove downloaded files after analysis."""
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f"Cleaned up: {path}")
                except OSError as e:
                    logger.warning(f"Failed to clean {path}: {e}")
