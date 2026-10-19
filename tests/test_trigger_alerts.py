"""Regression tests for the Core Service alert-trigger integration.

These guard the service-to-service seam that was silently broken: the call
had a doubled /api/v1 prefix and sent no X-Internal-Secret header, so the
Core Service rejected every price-driven alert match with 404/401 and no
alert ever fired.

Stdlib only (unittest + mock) so it runs with `python -m unittest` without
adding a test dependency. The third-party modules pulled in transitively by
the code under test (pydantic-settings, loguru, httpx) are used when they are
installed and otherwise replaced with minimal stubs, since the logic being
verified — URL building and request headers — does not depend on them.
"""
import sys
import types
import unittest
from unittest import mock


def _ensure_stub(name, build):
    """Register a stub module under `name` if the real one is not importable."""
    try:
        __import__(name)
    except ImportError:
        sys.modules[name] = build()


def _build_pydantic_settings():
    mod = types.ModuleType("pydantic_settings")

    class BaseSettings:  # noqa: D401 - minimal stand-in
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    mod.BaseSettings = BaseSettings
    return mod


def _build_loguru():
    mod = types.ModuleType("loguru")

    class _Logger:
        def __getattr__(self, _name):
            return lambda *a, **k: None

    mod.logger = _Logger()
    return mod


def _build_httpx():
    mod = types.ModuleType("httpx")

    class ConnectError(Exception):
        pass

    mod.ConnectError = ConnectError
    mod.post = lambda *a, **k: None  # patched per-test
    return mod


_ensure_stub("pydantic_settings", _build_pydantic_settings)
_ensure_stub("loguru", _build_loguru)
_ensure_stub("httpx", _build_httpx)

from src.infrastructure import config  # noqa: E402
from src.use_cases import trigger_alerts as trigger_alerts_module  # noqa: E402
from src.use_cases.trigger_alerts import trigger_alerts  # noqa: E402


class _FakeResponse:
    is_success = True
    status_code = 200
    text = "OK"

    @staticmethod
    def json():
        return {"data": {"triggered": 0}}


class TriggerAlertsTest(unittest.TestCase):
    def _capture_post(self, *, base_url, secret):
        """Invoke trigger_alerts() with patched settings and return the
        kwargs/args passed to httpx.post."""
        with mock.patch.object(config.settings, "core_service_url", base_url), \
             mock.patch.object(config.settings, "internal_secret", secret), \
             mock.patch.object(trigger_alerts_module.httpx, "post",
                               return_value=_FakeResponse()) as mock_post:
            trigger_alerts()
        self.assertEqual(mock_post.call_count, 1, "httpx.post should be called once")
        return mock_post.call_args

    def test_url_has_no_doubled_api_prefix(self):
        args, kwargs = self._capture_post(
            base_url="http://core.example/api/v1", secret="s3cret"
        )
        url = kwargs.get("url", args[0] if args else None)
        self.assertEqual(url, "http://core.example/api/v1/internal/trigger-alerts")
        self.assertNotIn("/api/v1/api/v1/", url)

    def test_internal_secret_header_is_sent(self):
        _, kwargs = self._capture_post(
            base_url="http://core.example/api/v1", secret="s3cret"
        )
        self.assertIn("headers", kwargs)
        self.assertEqual(kwargs["headers"].get("X-Internal-Secret"), "s3cret")


if __name__ == "__main__":
    unittest.main()
