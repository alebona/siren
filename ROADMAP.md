# Siren — Roadmap para "canivete suíço" (free + pago)

> Rascunho de visão e arquitetura. Documento vivo — atualizar conforme decisões forem tomadas.

## Visão geral

Siren vira uma "dev toolbelt" Python: um pacote CLI/lib que junta debug avançado,
produtividade de projeto, testes de API e qualidade de código, com um core
gratuito robusto e um tier pago que entrega valor que só faz sentido vindo de
nuvem/conta (não só "mais funções no código local").

### Por que isso importa para a arquitetura

Ferramenta que roda 100% local (como hoje) é fácil de burlar um gate de
licença — é só ler o código Python. Então o tier pago não deve ser "as mesmas
features com uma trava fraca", e sim **features que dependem de um backend
real**, onde a trava é natural (sem servidor, não funciona). Enforcement local
só faz sentido pra coisas de menor risco (ex: mensagem de aviso, watermark).

## Arquitetura proposta

```
siren-debug (PyPI, MIT, free)          → core.py, clean.py, autoload.py (como hoje)
siren-debug[pro] extra ou siren-cloud   → módulo que fala com api.siren.dev
                                            - login (siren login)
                                            - valida licença/plano no startup (cache local com TTL)
                                            - features que precisam de rede

Backend (novo):
  - API leve (FastAPI) + Postgres: users, licenses, subscriptions (Stripe)
  - Endpoint de auth (device flow tipo `gh auth login` ou API key simples)
  - Endpoint(s) por feature paga que precisa de nuvem (ex: sync, dashboard, storage de logs)
```

Free continua exatamente o que já existe hoje (siren, trace, diff, breakpoint,
clean, autoload) — isso não muda, é o gancho de aquisição.

## Mapeamento por área

| Área | Free | Pago (precisa de conta) |
|---|---|---|
| **Debug/profiling** | print/pprint context-aware, trace, timer, diff, breakpoint (já existe) | memory profiling, captura de exceções com upload pra dashboard web, log estruturado pesquisável na nuvem |
| **Produtividade CLI** | scaffolding básico, snippets locais | templates de time compartilhados via conta, sync de config entre máquinas |
| **API/HTTP** | cliente tipo httpie embutido, inspeção de requests local | mock server hospedado (URL pública), collections compartilhadas de equipe |
| **Qualidade de código** | lint helpers locais, detecção de código morto (via `ast`, sem rede) | relatórios agregados no dashboard, comparação histórica entre commits |

Padrão geral: **local = grátis, colaborativo/persistente/hospedado = pago.**

## Lista detalhada de features (free vs. pago)

Critério de corte: **local roda sem conta → grátis; qualquer coisa que dependa
de servidor/conta (sync, dashboard, compartilhamento) → pago.** Toda área tem
pelo menos uma feature grátis como porta de entrada.

### 🐞 Debug & Profiling — free ✅ concluído (v0.6.0)

**Grátis (local)**
- ✅ `siren()` print/pprint com contexto de arquivo/linha
- ✅ `@siren.trace`, `timeit=True`, `siren.diff`, `siren.breakpoint`
- ✅ Logging condicional (`if_equals`, `if_len_gt`, etc.), quiet mode, logfile local
- ✅ `siren-clean`, `siren-autoload`
- ✅ Snapshot de memória (`siren.memory()`, wrapper sobre `tracemalloc`; degrada com aviso no Python 2, onde `tracemalloc` não existe)
- ✅ Formatação bonita de traceback de exceções (`siren.catch`, context manager)

**Pago (nuvem)**
- Upload de sessões de debug pra um dashboard web com histórico pesquisável
- Captura de exceções em produção com notificação (tipo mini-Sentry)
- Log estruturado centralizado, pesquisável, com retenção configurável
- Compartilhar uma sessão de debug via link com o time

### 🛠️ Produtividade de CLI/projeto — free ✅ concluído (v0.6.0)

**Grátis (local)**
- ✅ Scaffolding com templates locais embutidos (`siren-scaffold`: script, package, class, dataclass, test)
- ✅ Gerenciador de `.env` local (`siren-env diff` — valida/compara `.env.example` e `.env`)
- ✅ Snippets locais (`siren-snippet`: save/show/list/remove)
- ✅ Geração de boilerplate (classe, teste, dataclass) — consolidado dentro do próprio `siren-scaffold`

**Pago (nuvem)**
- Templates de time compartilhados via conta (sync entre devs)
- Sync de configs/snippets entre máquinas
- Histórico de scaffolds gerados por projeto/equipe

### 🌐 Integração com API/HTTP — free ✅ concluído (v0.6.0)

**Grátis (local)**
- ✅ Cliente HTTP embutido tipo httpie (`siren-http GET/POST/PUT/PATCH/DELETE`)
- ✅ "Collections" de requests salvas em arquivo local (JSON, via `--save`/`replay`/`list`)
- ✅ Inspeção/log automático de requests feitas por `requests`/`httpx` via patch (`siren.patch_requests()` / `siren.patch_httpx()`, opt-in, sem dependência obrigatória — só o `httpx.Client` síncrono é coberto, não `AsyncClient`)

**Pago (nuvem)**
- Mock server hospedado com URL pública
- Collections compartilhadas de equipe (sync via conta)
- Histórico de chamadas de API na nuvem com replay

### ✅ Qualidade de código — free ✅ concluído (v0.6.0)

**Grátis (local)**
- ✅ Detecção de código morto via `ast` (`siren-quality deadcode` — imports e defs de módulo não usados; heurística restrita ao próprio arquivo)
- ✅ Lint helpers simples (`siren-quality lint` — `except:` genérico, `pdb.set_trace()`/`breakpoint()` esquecidos, TODOs/FIXMEs)
- ✅ Complexidade ciclomática (`siren-quality complexity` — por função, não por arquivo como rascunhado originalmente)

**Pago (nuvem)**
- Dashboard de qualidade agregado com tendência histórica
- Comparação entre branches/PRs (integração com GitHub)
- Relatórios de equipe (quem introduziu dívida técnica, etc.)

## Riscos e decisões em aberto

1. **Escopo do backend** é o maior custo novo — antes não existia nenhum. Vale
   começar com o menor backend possível (auth + Stripe + 1 endpoint) e não
   construir tudo de uma vez.
2. **Nome/branding**: "canivete suíço" é amplo — recomendo focar o roadmap
   inicial em 1-2 áreas novas (ex: debug avançado + API/HTTP) antes de abrir
   as 4 ao mesmo tempo, senão o escopo trava o lançamento.
3. **Breaking change de import**: hoje `from siren import siren` e autoload em
   builtins — isso deve continuar igual no free tier pra não quebrar usuários
   atuais.

## Próximos passos

1. ✅ Definir a **primeira feature paga concreta** — captura de exceções
   (mini-Sentry). Ver "Atualização 2026-09-18" abaixo.
2. ✅ Schema mínimo de licenciamento (users/workspaces/licenses) e fluxo de
   `siren-login`.
3. **Decidir hospedagem do backend** — hoje só roda local
   (`uvicorn app.main:app`); sem isso, `siren-login signup` não funciona pra
   ninguém fora da própria máquina de dev. Precisa da conta/decisão do
   usuário (Render, Fly.io, Railway, VPS próprio, etc.) — não é algo pra
   decidir sozinho.
4. Integrar Stripe de verdade (hoje toda licença nasce `active=true` sem
   cobrança nenhuma — ver riscos).
5. Roadmap faseado (v0.5 → v1.0) com o que entra em cada versão.

## Repositórios

- **Público** (este): `siren` / pacote `siren-debug` no PyPI — core free, MIT.
- **Privado**: [siren-pro](https://github.com/alebona/siren-pro) — backend do
  tier pago (auth, licenciamento, billing). Scaffold inicial (FastAPI +
  health check + stubs de `/auth/login` e `/licenses/validate`) já criado em
  2026-09-13. GitHub não permite visibilidade por branch dentro de um mesmo
  repositório, por isso a separação é em dois repositórios.

## Contexto da decisão (respostas do usuário)

- **Monetização escolhida**: licença + backend (conta do usuário, chave de
  licença, validação online).
- **Escopo desejado**: debug/profiling avançado, produtividade de CLI/projeto,
  integração com APIs/HTTP, qualidade de código — todas as quatro áreas estão
  na mesa, mas devem ser faseadas (ver riscos acima).
- **Horizonte atual**: só planejamento, sem implementação ainda.

### Atualização 2026-09-13 — free tier implementado

Todas as 4 áreas tiveram seu lado grátis implementado em `v0.6.0`, numa
tacada só (decisão do usuário: "tudo de uma vez" em vez de fasear). O patch
de `requests`/`httpx` foi inicialmente adiado por decisão de escopo, e depois
implementado mesmo assim a pedido do usuário (`siren.patch_requests()` /
`siren.patch_httpx()`). Decisões tomadas durante a implementação:
- Vários bullets do roadmap foram consolidados em menos comandos do que o
  rascunho original sugeria (ex: scaffolding + boilerplate viraram um único
  `siren-scaffold`; deadcode + lint + complexity viraram um único
  `siren-quality` com subcomandos) — ver `CHANGELOG.md` 0.6.0 para a lista
  final de comandos.

### Atualização 2026-09-18 — MVP do tier pro (captura de exceções)

Primeira feature paga escolhida: **captura de exceções** (mini-Sentry),
área Debug/Profiling. Snippet sync foi cogitado primeiro, mas descartado —
o próprio usuário não usaria isso no dia a dia, e a barra pra primeira
feature paga é "eu sentiria falta disso de verdade". Escopo do MVP,
combinado explicitamente com o usuário:
- ✅ **Dentro do escopo**: signup (`POST /auth/signup`), validação de
  licença (`GET /licenses/validate`), captura/listagem/detalhe de eventos
  (`POST/GET /events`, `GET /events/{id}`), tudo com testes (backend: 11
  testes; CLI: 16 testes) e verificado ponta a ponta com o backend real
  rodando local.
- ⏸️ **Fora do escopo, deliberadamente adiado**: notificação por
  push/e-mail (a captura funciona, mas é "puxar" via `siren-events list`,
  não "empurrar" um alerta), cobrança real via Stripe (toda licença nasce
  `active=true`, sem cobrar nada ainda), verificação de e-mail no signup
  (qualquer e-mail funciona), convite de equipe (schema já suporta
  múltiplos membros por workspace, mas sem endpoint ainda), e hospedagem
  (backend só roda local por enquanto).
- **Arquitetura**: SQLite puro (sem ORM) do lado do backend, dados sempre
  escopados por `workspace_id` (não por usuário direto) — pra quando
  compartilhamento de equipe existir, é aditivo, não retrabalho.
- **Preço definido** (ainda não integrado ao Stripe): R$10/mês, US$5/mês,
  €5/mês — preço regional intencional, não conversão direta de câmbio (o
  usuário rejeitou atrelar o preço em real ao dólar, tanto pelo poder de
  compra quanto pela volatilidade cambial).
- Ambos os repositórios (`siren` e `siren-pro`) publicados/commitados;
  nenhuma versão nova do PyPI publicada ainda (`siren-login`/`siren-events`
  já estão no pacote, só não foram lançados — ver decisão de "lançar em
  lote" abaixo).
