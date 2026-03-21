import builtins
from .core import siren, trace, info  # importa a instância global da sua lib

# torna a instância disponível globalmente
builtins.siren = siren

siren.trace = trace
siren.info = info