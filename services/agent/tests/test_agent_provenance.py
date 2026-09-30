"""Provenance reporting for streamed agent output."""

from src.api.routes.agent import _provenance


class _Settings:
    def __init__(self, default_model: str = "gpt-5.5"):
        self.default_model = default_model


class _Gateway:
    def __init__(self, configured: bool, default_model: str = "gpt-5.5"):
        self.is_configured = configured
        self.settings = _Settings(default_model)


def test_reports_offline_template_when_no_credentials():
    result = _provenance(_Gateway(configured=False))

    assert result == {"llm_configured": False, "model": ""}


def test_reports_model_when_credentials_present():
    result = _provenance(_Gateway(configured=True, default_model="deepseek-chat"))

    assert result["llm_configured"] is True
    assert result["model"] == "deepseek-chat"


def test_missing_attributes_degrade_to_offline():
    class _Bare:
        pass

    assert _provenance(_Bare()) == {"llm_configured": False, "model": ""}
