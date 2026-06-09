import builtins
from .core import siren, trace, info, set_quiet, set_logfile, set_enabled, get_config, diff, breakpoint_debug

__all__ = ["siren", "trace", "info", "set_quiet", "set_logfile", "set_enabled", "get_config", "diff", "breakpoint_debug"]

builtins.siren = siren

siren.trace = trace
siren.info = info
siren.set_quiet = set_quiet
siren.set_logfile = set_logfile
siren.set_enabled = set_enabled
siren.get_config = get_config
siren.diff = diff
siren.breakpoint = breakpoint_debug