# -*- coding: utf-8 -*-
"""
Performance sample capture for the pro tier.

Unlike siren.trace(timeit=True), which just prints one call's duration
locally, siren.profile buffers samples and uploads them in the
background to your siren-pro workspace, so siren-perf top can rank
bottlenecks across real runs over time instead of one call on one
machine.

Usage:
    @siren.profile
    def slow_thing():
        ...

    @siren.profile(label="checkout", min_duration_ms=50)
    def maybe_slow(...):
        ...

    with siren.profile_block("db-query"):
        ...

    siren.perf_flush()  # force an upload before a short script exits

CLI:
    siren-perf top [--hours 24] [--limit 20]
    siren-perf list [--name NAME] [--limit 50]
"""
from __future__ import print_function

import argparse
import atexit
import json
import random
import sys
import threading
import time

from . import account, http_client
from .http_client import URLError
from ._cli import banner
from ._output import safe_print

_perf_counter = getattr(time, "perf_counter", time.time)

_FLUSH_INTERVAL = 10.0  # seconds between background flushes
_BATCH_SIZE = 50        # flush as soon as the buffer reaches this many samples
_MAX_BUFFER = 500       # hard cap; samples are dropped past this until the next flush

_buffer = []
_lock = threading.Lock()
_flush_thread = None
_warned_not_logged_in = False
_warned_buffer_full = False


def _ensure_flush_thread():
    # Started lazily on the first sample (not at import time) so that on a
    # preforking server (e.g. gunicorn), the thread is created fresh in
    # each worker after the fork instead of dying with the parent's thread.
    global _flush_thread
    if _flush_thread is not None:
        return
    _flush_thread = threading.Thread(target=_flush_loop)
    _flush_thread.daemon = True
    _flush_thread.start()
    atexit.register(_flush, final=True)


def _flush_loop():
    while True:
        time.sleep(_FLUSH_INTERVAL)
        _flush()


def _record(name, duration_ms, ok, label):
    global _warned_buffer_full
    should_flush = False
    with _lock:
        if len(_buffer) >= _MAX_BUFFER:
            if not _warned_buffer_full:
                safe_print(banner("PERF", "buffer full ({} samples) - dropping new samples until the next flush".format(_MAX_BUFFER)))
                _warned_buffer_full = True
        else:
            _buffer.append({"name": name, "duration_ms": duration_ms, "ok": ok, "label": label})
            should_flush = len(_buffer) >= _BATCH_SIZE

    _ensure_flush_thread()
    if should_flush:
        _flush()


def perf_flush():
    """Force an immediate, synchronous upload of whatever's buffered."""
    _flush()


def _flush(final=False):
    global _warned_not_logged_in
    with _lock:
        if not _buffer:
            return
        batch = list(_buffer)
        del _buffer[:]

    creds = account.load_credentials()
    if creds is None:
        if not _warned_not_logged_in:
            safe_print(banner("PERF", "not logged in - run 'siren-login signup <email>' first (samples are being dropped)"))
            _warned_not_logged_in = True
        return

    try:
        result = http_client.send(
            "POST", creds["api_url"] + "/metrics/batch",
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
            json_body={"samples": batch},
            timeout=10.0,
        )
    except Exception:
        return  # best-effort; a background flush must never raise

    if result["status"] != 200 and not final:
        safe_print(banner("PERF", "failed to upload {} performance sample(s) ({})".format(len(batch), result["status"])))


def profile(func=None, label=None, sample_rate=1.0, min_duration_ms=0.0):
    """
    Decorator that times a function call and buffers the sample for
    upload. Exceptions are still recorded (ok=False) and always
    re-raised - never swallowed.

    Usage:
        @siren.profile
        def foo(...):
            ...

        @siren.profile(label="checkout", sample_rate=0.1, min_duration_ms=20)
    """
    def decorator(target):
        name = getattr(target, "__name__", repr(target))

        def wrapper(*args, **kwargs):
            start = _perf_counter()
            ok = True
            try:
                return target(*args, **kwargs)
            except Exception:
                ok = False
                raise
            finally:
                elapsed_ms = (_perf_counter() - start) * 1000.0
                if elapsed_ms >= min_duration_ms and (sample_rate >= 1.0 or random.random() < sample_rate):
                    _record(name, elapsed_ms, ok, label)

        return wrapper

    if func is None:
        return decorator

    return decorator(func)


class _ProfileBlockContext(object):
    def __init__(self, name, label=None):
        self.name = name
        self.label = label
        self._start = None

    def __enter__(self):
        self._start = _perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        elapsed_ms = (_perf_counter() - self._start) * 1000.0
        _record(self.name, elapsed_ms, exc_type is None, self.label)
        return False  # never suppress the exception


def profile_block(name, label=None):
    """
    Context manager that times a block of code (rather than a whole
    function) and buffers the sample for upload.

    Usage:
        with siren.profile_block("db-query"):
            ...
    """
    return _ProfileBlockContext(name, label)


def _require_credentials():
    creds = account.load_credentials()
    if creds is None:
        safe_print(banner("PERF", "not logged in - run 'siren-login signup <email>' first"))
        sys.exit(1)
    return creds


def _send_or_exit(api_url, *args, **kwargs):
    kwargs.setdefault("timeout", 60.0)  # Render's free tier can take a while to wake from sleep
    try:
        return http_client.send(*args, **kwargs)
    except URLError as e:
        safe_print(banner("PERF", "Could not reach siren-pro at {} - is it running? ({})".format(api_url, e)))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="siren-perf")
    subparsers = parser.add_subparsers(dest="command")

    top_parser = subparsers.add_parser("top")
    top_parser.add_argument("--hours", type=int, default=24)
    top_parser.add_argument("--limit", type=int, default=20)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--name", default=None)
    list_parser.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    if args.command == "top":
        creds = _require_credentials()
        result = _send_or_exit(
            creds["api_url"], "GET",
            "{}/metrics/top?hours={}&limit={}".format(creds["api_url"], args.hours, args.limit),
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
        )
        if result["status"] != 200:
            safe_print(banner("PERF", "Error ({}): {}".format(result["status"], result["body"])))
            sys.exit(1)

        rows = json.loads(result["body"])
        if not rows:
            safe_print(banner("PERF", "no performance samples in the last {}h".format(args.hours)))
        for row in rows:
            safe_print(banner("PERF", "{name} - {calls} calls, avg {avg_ms:.1f}ms, p95 {p95_ms:.1f}ms, total {total_ms:.0f}ms, {errors} errors".format(
                name=row["name"], calls=row["calls"], avg_ms=row["avg_ms"],
                p95_ms=row["p95_ms"], total_ms=row["total_ms"], errors=row["errors"],
            )))

    elif args.command == "list":
        creds = _require_credentials()
        url = "{}/metrics/list?limit={}".format(creds["api_url"], args.limit)
        if args.name:
            url += "&name={}".format(args.name)
        result = _send_or_exit(
            creds["api_url"], "GET", url,
            headers={"Authorization": "Bearer {}".format(creds["api_key"])},
        )
        if result["status"] != 200:
            safe_print(banner("PERF", "Error ({}): {}".format(result["status"], result["body"])))
            sys.exit(1)

        samples = json.loads(result["body"])
        if not samples:
            safe_print(banner("PERF", "no performance samples yet"))
        for sample in samples:
            label = " [{}]".format(sample["label"]) if sample.get("label") else ""
            status = "" if sample["ok"] else " FAILED"
            safe_print(banner("PERF", "{name} - {duration_ms:.1f}ms{status}{label} ({created_at})".format(
                name=sample["name"], duration_ms=sample["duration_ms"],
                status=status, label=label, created_at=sample["created_at"],
            )))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
