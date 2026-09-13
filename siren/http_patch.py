# -*- coding: utf-8 -*-
"""
Optional, opt-in logging of HTTP calls made through `requests`/`httpx`.

Neither library is a dependency of siren — they're imported lazily, only
when a patch_*() function is actually called, so importing this module
(which siren/__init__.py does unconditionally) never requires them.

Usage:
    siren.patch_requests()   # every requests.Session call now logs
    siren.patch_httpx()      # every httpx.Client call now logs (sync only)
    siren.unpatch_requests()
    siren.unpatch_httpx()
"""
from __future__ import print_function

import time

from ._cli import banner
from ._output import safe_print

_original_requests_request = None
_original_httpx_request = None


def _log(method, url, status_code, elapsed):
    safe_print(banner("HTTP", "{} {} -> {} ({:.3f}s)".format(method, url, status_code, elapsed)))


def patch_requests():
    """Monkeypatch requests.Session.request to log method/url/status/duration."""
    global _original_requests_request

    try:
        import requests
    except ImportError:
        raise ImportError("siren.patch_requests() requires the 'requests' package to be installed")

    if _original_requests_request is not None:
        return  # already patched

    _original_requests_request = requests.Session.request

    def _patched_request(self, method, url, *args, **kwargs):
        start = time.time()
        response = _original_requests_request(self, method, url, *args, **kwargs)
        _log(method, url, response.status_code, time.time() - start)
        return response

    requests.Session.request = _patched_request


def unpatch_requests():
    """Undo patch_requests()."""
    global _original_requests_request

    if _original_requests_request is None:
        return

    import requests
    requests.Session.request = _original_requests_request
    _original_requests_request = None


def patch_httpx():
    """
    Monkeypatch httpx.Client.request to log method/url/status/duration.

    Only the sync httpx.Client is covered (not AsyncClient) to keep this
    module free of `async def`, so it stays importable on Python 2.7 even
    though httpx itself is Python 3 only.
    """
    global _original_httpx_request

    try:
        import httpx
    except ImportError:
        raise ImportError("siren.patch_httpx() requires the 'httpx' package to be installed")

    if _original_httpx_request is not None:
        return  # already patched

    _original_httpx_request = httpx.Client.request

    def _patched_request(self, method, url, *args, **kwargs):
        start = time.time()
        response = _original_httpx_request(self, method, url, *args, **kwargs)
        _log(method, url, response.status_code, time.time() - start)
        return response

    httpx.Client.request = _patched_request


def unpatch_httpx():
    """Undo patch_httpx()."""
    global _original_httpx_request

    if _original_httpx_request is None:
        return

    import httpx
    httpx.Client.request = _original_httpx_request
    _original_httpx_request = None
