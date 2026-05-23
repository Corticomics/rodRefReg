"""Unit tests for ``utils.net`` — the central network policy module.

Phase 2 of the offline-resilience work. Pins the contract that the updater
and notifications modules now depend on:

* :func:`utils.net.get_json` is fail-soft (returns ``None`` on any failure);
* :func:`utils.net.require_digest` is fail-closed (raises ``NetworkError``);
* :func:`utils.net.stream_download` enforces both a byte cap and a
  wall-clock deadline, and cleans up the partial file on any failure.
"""

from __future__ import annotations

import pytest

requests = pytest.importorskip("requests")

from utils import net  # noqa: E402  (importorskip first)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Stand-in for a ``requests.Response`` from a non-streaming GET."""

    def __init__(self, *, status_ok=True, json_data=None, text="", raise_json=False):
        self._json_data = json_data
        self._raise_json = raise_json
        self._ok = status_ok
        self.text = text

    def raise_for_status(self):
        if not self._ok:
            raise requests.HTTPError("404")

    def json(self):
        if self._raise_json:
            raise ValueError("not JSON")
        return self._json_data


class _FakeStream:
    """Stand-in for a streaming ``requests`` response used as a CM."""

    def __init__(self, chunks, *, status_ok=True):
        self._chunks = chunks
        self._ok = status_ok

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        if not self._ok:
            raise requests.HTTPError("404")

    def iter_content(self, _chunk_size):
        yield from self._chunks


def _conn_error(*_a, **_k):
    raise requests.exceptions.ConnectionError("offline")


# ---------------------------------------------------------------------------
# get_json — fail-soft
# ---------------------------------------------------------------------------

def test_get_json_returns_dict_on_success(monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(json_data={"a": 1}))
    assert net.get_json("https://example/x") == {"a": 1}


def test_get_json_returns_none_on_connection_error(monkeypatch):
    monkeypatch.setattr(net.requests, "get", _conn_error)
    assert net.get_json("https://example/x") is None


def test_get_json_returns_none_on_http_error(monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(status_ok=False))
    assert net.get_json("https://example/x") is None


def test_get_json_returns_none_on_malformed_json(monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(raise_json=True))
    assert net.get_json("https://example/x") is None


def test_get_json_returns_none_on_dns_failure(offline):
    assert net.get_json("https://nope.invalid/x") is None


# ---------------------------------------------------------------------------
# require_digest — fail-closed
# ---------------------------------------------------------------------------

def test_require_digest_returns_clean_lowercase_hex(monkeypatch):
    digest = "a" * 64
    monkeypatch.setattr(
        net.requests, "get",
        lambda *_a, **_k: _FakeResponse(text=f"{digest.upper()}  file.tar.gz\n"),
    )
    assert net.require_digest("https://example/x.sha256") == digest


def test_require_digest_raises_when_url_is_empty():
    with pytest.raises(net.NetworkError, match="checksum URL"):
        net.require_digest("")


def test_require_digest_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(status_ok=False))
    with pytest.raises(net.NetworkError, match="fetch checksum"):
        net.require_digest("https://example/x.sha256")


def test_require_digest_raises_on_connection_error(monkeypatch):
    monkeypatch.setattr(net.requests, "get", _conn_error)
    with pytest.raises(net.NetworkError):
        net.require_digest("https://example/x.sha256")


def test_require_digest_raises_on_dns_failure(offline):
    with pytest.raises(net.NetworkError):
        net.require_digest("https://nope.invalid/x.sha256")


def test_require_digest_raises_on_empty_response(monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(text=""))
    with pytest.raises(net.NetworkError, match="empty"):
        net.require_digest("https://example/x.sha256")


def test_require_digest_raises_on_invalid_format(monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(text="not-a-hex-digest"))
    with pytest.raises(net.NetworkError, match="SHA256"):
        net.require_digest("https://example/x.sha256")


def test_require_digest_raises_on_wrong_length(monkeypatch):
    """A 32-char (MD5-shaped) digest must be rejected."""
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeResponse(text="abc" * 10))
    with pytest.raises(net.NetworkError, match="SHA256"):
        net.require_digest("https://example/x.sha256")


# ---------------------------------------------------------------------------
# stream_download — wall-clock + byte cap + cleanup
# ---------------------------------------------------------------------------

def test_stream_download_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeStream([b"hello ", b"world"]))
    dst = tmp_path / "out.bin"
    net.stream_download("https://example/x", str(dst))
    assert dst.read_bytes() == b"hello world"


def test_stream_download_enforces_byte_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeStream([b"x" * 1024] * 10))
    dst = tmp_path / "out.bin"
    with pytest.raises(net.NetworkError, match="bytes"):
        net.stream_download("https://example/x", str(dst), max_bytes=2048)
    assert not dst.exists(), "partial file must be cleaned up on failure"


def test_stream_download_enforces_wall_clock(tmp_path, monkeypatch):
    monkeypatch.setattr(net.requests, "get",
                        lambda *_a, **_k: _FakeStream([b"a", b"b", b"c"]))
    # 1st monotonic() call sets deadline=100+10=110. Subsequent calls
    # return 105 (under deadline), 200 (over → raise).
    times = iter([100.0, 105.0, 200.0, 200.0, 200.0])
    monkeypatch.setattr(net.time, "monotonic", lambda: next(times))

    dst = tmp_path / "out.bin"
    with pytest.raises(net.NetworkError, match="wall-clock"):
        net.stream_download("https://example/x", str(dst), total_timeout=10)
    assert not dst.exists()


def test_stream_download_cleans_up_on_http_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        net.requests, "get",
        lambda *_a, **_k: _FakeStream([b"data"], status_ok=False),
    )
    dst = tmp_path / "out.bin"
    with pytest.raises(net.NetworkError):
        net.stream_download("https://example/x", str(dst))
    assert not dst.exists()


def test_stream_download_cleans_up_on_connection_error(tmp_path, monkeypatch):
    monkeypatch.setattr(net.requests, "get", _conn_error)
    dst = tmp_path / "out.bin"
    with pytest.raises(net.NetworkError):
        net.stream_download("https://example/x", str(dst))
    assert not dst.exists()
