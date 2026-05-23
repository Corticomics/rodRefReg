"""Central network policy for RRR.

All outbound HTTPS in the application goes through this module so that
timeouts, error mapping, and integrity rules live in one place and tests
can substitute the whole network layer with a single monkeypatch.

Two rules govern the helpers here:

* **Fail-soft for UX operations.** The startup update check must never
  raise into the GUI — it returns ``None`` when anything goes wrong. The
  deployed Pi may sit in an animal nest with no internet; the app must
  keep delivering water normally regardless.
* **Fail-closed for security operations.** :func:`require_digest` raises
  ``NetworkError`` when the SHA256 cannot be obtained, replacing the
  previous "if expected and ..." silent-skip in the apply engine.

Phase 2 of the offline-resilience plan.
"""

from __future__ import annotations

import os
import time

import requests

# (connect, read) tuple: connect must be short so a dead network is
# detected quickly; read can be more generous for slow links.
_DEFAULT_TIMEOUT: tuple[float, float] = (5, 10)

# Hard ceiling for streamed bodies — guards against a runaway response
# filling the disk. Tuned for the update bundle, which is well under 50 MB.
_DEFAULT_MAX_BYTES: int = 200 * 1024 * 1024

# Wall-clock budget for a streamed download. ``requests``' read timeout is
# per-read, so a trickle of 1-byte reads could otherwise stall the apply
# for an hour; this enforces a single absolute deadline.
_DEFAULT_TOTAL_TIMEOUT: float = 600


class NetworkError(Exception):
    """A network operation could not be completed within its budget.

    The single exception type the apply engine catches — every failure
    mode (DNS, connection refused, HTTP error, timeout, oversize body,
    invalid checksum format) is mapped to this one class.
    """


def get_json(url: str, *, timeout: tuple[float, float] = _DEFAULT_TIMEOUT,
             headers: dict | None = None) -> dict | None:
    """GET a JSON document. ``None`` on any failure — never raises.

    Used by non-security operations that must degrade silently — the
    startup update check is the canonical caller.
    """
    try:
        response = requests.get(url, timeout=timeout, headers=headers or {})
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def require_digest(url: str, *,
                   timeout: tuple[float, float] = _DEFAULT_TIMEOUT) -> str:
    """Fetch and validate a SHA256 from a ``.sha256`` asset.

    Returns the lowercase 64-char hex digest. Raises :class:`NetworkError`
    when the asset is missing, unreachable, empty, or malformed — the
    apply engine then refuses to install. This is the fail-closed
    integrity rule that replaces the previous silent-skip.
    """
    if not url:
        raise NetworkError("no checksum URL was provided")
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:
        raise NetworkError(f"could not fetch checksum: {exc}") from exc
    text = (response.text or "").strip()
    if not text:
        raise NetworkError("checksum response was empty")
    digest = text.split()[0].lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise NetworkError(f"checksum is not a valid SHA256: {digest!r}")
    return digest


def stream_download(url: str, dest: str, *,
                    connect_timeout: float = 10,
                    read_timeout: float = 60,
                    total_timeout: float = _DEFAULT_TOTAL_TIMEOUT,
                    max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
    """Stream a URL to ``dest`` with wall-clock and byte caps.

    Raises :class:`NetworkError` on any failure (timeout, HTTP error,
    half-open connection, body exceeding ``max_bytes``, wall-clock
    exceeded). On error, ``dest`` is removed so the caller never sees a
    partial file.
    """
    deadline = time.monotonic() + total_timeout
    try:
        with requests.get(url, stream=True,
                          timeout=(connect_timeout, read_timeout)) as resp:
            resp.raise_for_status()
            written = 0
            with open(dest, "wb") as handle:
                for chunk in resp.iter_content(1 << 16):
                    if chunk:
                        written += len(chunk)
                        if written > max_bytes:
                            raise NetworkError(
                                f"download exceeded {max_bytes} bytes")
                        handle.write(chunk)
                    if time.monotonic() > deadline:
                        raise NetworkError(
                            f"download exceeded {total_timeout:.0f}s "
                            f"wall-clock budget")
    except NetworkError:
        _safe_unlink(dest)
        raise
    except Exception as exc:
        _safe_unlink(dest)
        raise NetworkError(f"download failed: {exc}") from exc


def _safe_unlink(path: str) -> None:
    """``os.unlink`` that does not raise when the file is already gone."""
    try:
        os.unlink(path)
    except OSError:
        pass
