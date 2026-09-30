import ipaddress

import pytest

from src.video_tools.downloader import VideoDownloader


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/video",
        "https://localhost.localdomain/video",
        "http://127.0.0.1/video",
        "http://10.0.0.8/video",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/video",
        "https://user:password@example.com/video",
        "ftp://example.com/video",
    ],
)
def test_validate_url_rejects_non_public_or_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        VideoDownloader._validate_url(url)


def test_validate_url_accepts_public_hostname_with_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        VideoDownloader,
        "_resolve_host_addresses",
        staticmethod(lambda _hostname: [ipaddress.ip_address("93.184.216.34")]),
    )

    assert VideoDownloader._validate_url("https://example.com/video?id=123") == "example.com"


def test_safe_url_host_does_not_log_credentials_or_port() -> None:
    assert VideoDownloader._safe_url_host("https://user:password@example.com:8443/video?token=secret") == "example.com"


@pytest.mark.asyncio
async def test_download_returns_safe_error_for_rejected_url() -> None:
    downloader = object.__new__(VideoDownloader)

    result = await downloader.download("http://127.0.0.1/video")

    assert result.success is False
    assert result.error == "video URL is not allowed"
