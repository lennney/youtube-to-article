"""Tests for support layer."""
import tempfile
from pathlib import Path
import pytest
from ytarticle.support.cookies import CookieManager
from ytarticle.support.proxy import ProxyManager


class TestCookieManager:
    def test_no_path_returns_empty_args(self):
        mgr = CookieManager()
        assert mgr.yt_dlp_args() == []

    def test_with_valid_cookie_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write(".youtube.com\tTRUE\t/\tTRUE\t0\tTEST\tvalue\n")
            p = f.name
        mgr = CookieManager(p)
        assert mgr.exists
        assert mgr.is_valid
        assert "--cookies" in mgr.yt_dlp_args()
        Path(p).unlink()

    def test_is_valid_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("# just a comment\n")
            p = f.name
        mgr = CookieManager(p)
        assert mgr.exists
        assert not mgr.is_valid
        Path(p).unlink()


class TestProxyManager:
    def test_disabled_by_default(self):
        mgr = ProxyManager()
        assert not mgr.enabled
        assert mgr.yt_dlp_args() == []

    def test_with_http_proxy(self):
        mgr = ProxyManager(http="http://127.0.0.1:8080")
        assert mgr.enabled
        assert "--proxy" in mgr.yt_dlp_args()
