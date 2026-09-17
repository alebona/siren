import sys

if sys.version_info[0] >= 3:
    import builtins
else:
    import __builtin__ as builtins

from .core import (
    siren, trace, info, set_quiet, set_logfile, set_enabled, get_config,
    diff, breakpoint_debug, memory, catch,
)
from .http_patch import patch_requests, unpatch_requests, patch_httpx, unpatch_httpx
from .events import report

__all__ = [
    "siren", "trace", "info", "set_quiet", "set_logfile", "set_enabled",
    "get_config", "diff", "breakpoint_debug", "memory", "catch",
    "patch_requests", "unpatch_requests", "patch_httpx", "unpatch_httpx",
    "report",
]

builtins.siren = siren

siren.trace = trace
siren.info = info
siren.set_quiet = set_quiet
siren.set_logfile = set_logfile
siren.set_enabled = set_enabled
siren.get_config = get_config
siren.diff = diff
siren.breakpoint = breakpoint_debug
siren.memory = memory
siren.catch = catch
siren.patch_requests = patch_requests
siren.unpatch_requests = unpatch_requests
siren.patch_httpx = patch_httpx
siren.unpatch_httpx = unpatch_httpx
siren.report = report