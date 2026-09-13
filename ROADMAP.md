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

### 🐞 Debug & Profiling

**Grátis (local)**
- `siren()` print/pprint com contexto de arquivo/linha *(já existe)*
- `@siren.trace`, `timeit=True`, `siren.diff`, `siren.breakpoint` *(já existe)*
- Logging condicional (`if_equals`, `if_len_gt`, etc.), quiet mode, logfile local *(já existe)*
- `siren-clean`, `siren-autoload` *(já existe)*
- Snapshot de memória básico (wrapper local sobre `tracemalloc`)
- Formatação bonita de traceback de exceções (local)

**Pago (nuvem)**
- Upload de sessões de debug pra um dashboard web com histórico pesquisável
- Captura de exceções em produção com notificação (tipo mini-Sentry)
- Log estruturado centralizado, pesquisável, com retenção configurável
- Compartilhar uma sessão de debug via link com o time

### 🛠️ Produtividade de CLI/projeto

**Grátis (local)**
- Scaffolding de projeto com templates locais embutidos (script, pacote, CLI)
- Gerenciador de `.env` local (validar, diff entre `.env.example` e `.env`)
- Snippets locais (salvar/inserir blocos de código)
- Geração de boilerplate (classe, teste, dataclass) via CLI

**Pago (nuvem)**
- Templates de time compartilhados via conta (sync entre devs)
- Sync de configs/snippets entre máquinas
- Histórico de scaffolds gerados por projeto/equipe

### 🌐 Integração com API/HTTP

**Grátis (local)**
- Cliente HTTP embutido tipo httpie (`siren http GET url`)
- Inspeção/log de requests feitas por `requests`/`httpx` via patch local
- "Collections" de requests salvas em arquivo local (JSON/YAML)

**Pago (nuvem)**
- Mock server hospedado com URL pública
- Collections compartilhadas de equipe (sync via conta)
- Histórico de chamadas de API na nuvem com replay

### ✅ Qualidade de código

**Grátis (local)**
- Detecção de código morto via `ast` (funções/imports não usados)
- Lint helpers simples (prints esquecidos, TODOs, etc.)
- Complexidade ciclomática por arquivo

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

1. Definir a **primeira feature paga concreta** — a que mais justifica
   conta+billing. Isso ancora o MVP do backend.
2. Desenhar o schema mínimo de licenciamento (users/licenses/plans) e o fluxo
   de `siren login`.
3. Roadmap faseado (v0.5 → v1.0) com o que entra em cada versão.

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
