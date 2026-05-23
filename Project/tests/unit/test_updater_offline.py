"""Characterization tests: the update system when GitHub is unreachable.

Phase 1 of the offline-resilience work. These tests pin down today's
behaviour so Phase 2 can harden the update path without regressions, and
plant a **strict xfail canary** on the one genuine defect found in the audit:
``apply_update`` silently skips SHA256 verification when the ``.sha256`` asset
cannot be fetched (``updater.py``: ``if expected and ...``). Phase 2 makes
that check fail-closed; the canary then flips to passing and its strict
marker forces removal.

No production code changes here.
"""

from __future__ import annotations

import io
import json
import tarfile

import pytest

# updater imports PyQt5 + requests; skip cleanly where they are absent.
pytest.importorskip("PyQt5.QtCore")
pytest.importorskip("requests")


@pytest.fixture
def updater(monkeypatch):
    """The updater module, with any ambient blue-green env vars cleared."""
    monkeypatch.delenv("RRR_HOME", raising=False)
    from utils import updater as _updater

    return _updater


class _FakeResponse:
    """Minimal stand-in for a ``requests`` response."""

    def __init__(self, *, json_data=None, text="", raise_json=False):
        self._json_data = json_data
        self._raise_json = raise_json
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        if self._raise_json:
            raise ValueError("not JSON")
        return self._json_data


def _make_bundle(dest_path, version):
    """Write a minimal but structurally valid ``.rrrupdate`` tar.gz."""
    with tarfile.open(dest_path, "w:gz") as tar:
        for name, payload in (
            ("Project/main.py", "# minimal release payload\n"),
            ("manifest.json", json.dumps({"version": version})),
        ):
            raw = payload.encode()
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))


# ---------------------------------------------------------------------------
# Version comparison — pure logic
# ---------------------------------------------------------------------------

def test_is_newer_compares_versions(updater):
    assert updater.is_newer("1.6.0", "1.5.3") is True
    assert updater.is_newer("1.5.3", "1.5.3") is False
    assert updater.is_newer("1.5.2", "1.5.3") is False
    assert updater.is_newer("2.0.0", "1.9.9") is True


def test_is_newer_ignores_prerelease_suffix(updater):
    assert updater.is_newer("1.6.0-beta", "1.5.3") is True


def test_is_newer_rejects_unparseable_input(updater):
    assert updater.is_newer("", "1.5.3") is False
    assert updater.is_newer("not-a-version", "1.5.3") is False
    assert updater.is_newer("1.6.0", "garbage") is False


# ---------------------------------------------------------------------------
# fetch_latest — must degrade silently when offline
# ---------------------------------------------------------------------------

def test_fetch_latest_returns_none_on_connection_error(updater, monkeypatch):
    """An offline device gets ``None`` — never an exception, never a banner.

    Phase 2 routed the HTTP call through ``utils.net``; the patch target is
    therefore ``net.requests`` (same module object, more honest naming).
    """
    import requests
    from utils import net

    def _boom(*_a, **_k):
        raise requests.exceptions.ConnectionError("offline")

    monkeypatch.setattr(net.requests, "get", _boom)
    assert updater.fetch_latest() is None


def test_fetch_latest_returns_none_on_dns_failure(updater, offline):
    """With DNS resolution failing for every host, the check is a no-op."""
    assert updater.fetch_latest() is None


def test_fetch_latest_returns_none_on_timeout(updater, monkeypatch):
    import requests
    from utils import net

    def _timeout(*_a, **_k):
        raise requests.exceptions.Timeout("slow network")

    monkeypatch.setattr(net.requests, "get", _timeout)
    assert updater.fetch_latest() is None


def test_fetch_latest_returns_none_on_malformed_json(updater, monkeypatch):
    """A reachable-but-garbage response must not crash the check."""
    from utils import net

    monkeypatch.setattr(
        net.requests, "get",
        lambda *_a, **_k: _FakeResponse(raise_json=True),
    )
    assert updater.fetch_latest() is None


# ---------------------------------------------------------------------------
# apply_update — off-device and bad-bundle paths
# ---------------------------------------------------------------------------

def test_apply_update_off_device_is_blocked_with_a_clear_message(updater):
    """On a dev clone (no RRR_HOME) apply is unavailable, not a crash."""
    info = updater.UpdateInfo(
        version="9.9.9", url="https://example/r", notes="", available=True,
        bundle_url="https://example/b.rrrupdate",
    )
    ok, message = updater.apply_update(info)
    assert ok is False
    assert "installed device" in message


def test_apply_update_rejects_a_corrupt_bundle_when_checksum_is_known(
    updater, tmp_path, monkeypatch,
):
    """When the .sha256 IS fetched and mismatches, the bundle is rejected.

    This is the verification path working correctly — locked in as a
    regression guard for the Phase 2 changes.
    """
    home = tmp_path / "rrr"
    (home / "releases").mkdir(parents=True)
    monkeypatch.setenv("RRR_HOME", str(home))

    monkeypatch.setattr(
        updater, "_download", lambda _url, dest: _make_bundle(dest, "9.9.9"),
    )
    monkeypatch.setattr(updater, "_fetch_sha256", lambda _url: "0" * 64)

    info = updater.UpdateInfo(
        version="9.9.9", url="https://example/r", notes="", available=True,
        bundle_url="https://example/b.rrrupdate",
        sha256_url="https://example/b.rrrupdate.sha256",
    )
    ok, message = updater.apply_update(info)
    assert ok is False
    assert "verification failed" in message.lower()


def test_apply_update_rejects_bundle_when_checksum_cannot_be_fetched(
    updater, tmp_path, monkeypatch,
):
    """An unreachable / 404 / rate-limited .sha256 asset must block the apply.

    The Phase 2 fail-closed integrity rule: when :func:`utils.net.require_digest`
    raises ``NetworkError``, ``apply_update`` refuses to install the bundle
    and surfaces a clear "could not verify" message. Replaces the
    pre-Phase-2 silent-skip (``if expected and ...``).
    """
    from utils import net

    home = tmp_path / "rrr"
    (home / "releases").mkdir(parents=True)
    monkeypatch.setenv("RRR_HOME", str(home))

    monkeypatch.setattr(
        updater, "_download", lambda _url, dest: _make_bundle(dest, "9.9.9"),
    )

    def _checksum_unreachable(_url):
        raise net.NetworkError("checksum asset unreachable (404)")

    monkeypatch.setattr(updater, "_fetch_sha256", _checksum_unreachable)

    info = updater.UpdateInfo(
        version="9.9.9", url="https://example/r", notes="", available=True,
        bundle_url="https://example/b.rrrupdate",
        sha256_url="https://example/b.rrrupdate.sha256",
    )
    ok, message = updater.apply_update(info)
    assert ok is False
    assert "verify" in message.lower()
