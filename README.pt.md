<p align="center">
  <img src="vscode/media/icon.png" width="128" alt="Ícone do Siren: uma cauda de sereia de cristal saindo da água">
</p>

<h1 align="center">Siren</h1>

<p align="center">
  Debug com print em Python, sem a faxina depois.<br>
  Uma extensão do VS Code: escreva <code>siren(x)</code>, rode o código e veja o valor no fim da linha. Remova todas as chamadas com um clique.
</p>

<p align="center">
  <a href="https://marketplace.visualstudio.com/items?itemName=alebona.siren"><img src="https://vsmarketplacebadges.dev/version-short/alebona.siren.svg" alt="Versão no VS Code Marketplace"></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=alebona.siren"><img src="https://vsmarketplacebadges.dev/installs-short/alebona.siren.svg" alt="Instalações"></a>
  <img src="https://img.shields.io/badge/Python-2.7%20%7C%203.6%2B-3776AB" alt="Python 2.7 e 3.6+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/Licen%C3%A7a-MIT-yellow.svg" alt="Licença MIT"></a>
</p>

<p align="center"><a href="README.md">English</a> · <b>Português</b></p>

---

## Instalação

Procure **Siren** no painel de extensões do VS Code (`Ctrl+Shift+X`), instale pela [página no Marketplace](https://marketplace.visualstudio.com/items?itemName=alebona.siren) ou pelo terminal:

```bash
code --install-extension alebona.siren
```

Não é preciso `pip install`. A extensão traz o próprio runtime Python e deixa o `siren` disponível para todo programa Python que você inicia pelo VS Code. Basta ter Python 2.7 ou 3.6+ na máquina.

## Começando

```python
usuario = {"nome": "Ana", "itens": [1, 2, 3]}
siren(usuario)

for i in range(3):
    siren(i, label="loop")
```

Clique em ▶ **Run current file** no topo do editor (ou rode o arquivo num terminal do VS Code, ou com F5). Cada valor aparece no fim da sua linha:

```text
siren(usuario)              🧜 usuario = {'nome': 'Ana', 'itens': [1, 2, 3]}
    siren(i, label="loop")  🧜 i = 2 (last of 3)
```

Não precisa de import: dentro do VS Code, `siren` é um builtin. Quando terminar, clique no contador **🧜** da barra de status para remover todas as chamadas do arquivo.

## O que a extensão tem

Tudo fica no painel lateral do Siren (o ícone da cauda de sereia) e na paleta de comandos, em **Siren:**.

| | |
| --- | --- |
| **Valores na linha** | Cada `siren()` mostra o último valor no fim da linha; passe o mouse para ver os cinco últimos. |
| **Inserir** | `Ctrl+Alt+S` adiciona `siren()` com o cursor dentro, pronto para digitar, ou envolve a seleção em `siren(...)`. |
| **Run current file** | Roda o arquivo num terminal novo com o Siren ativo, e os valores aparecem sem configurar nada. |
| **Calls** | Todos os `siren()` do projeto, agrupados por arquivo, com o último valor. O ícone lateral mostra o total. |
| **Limpeza** | Remove as chamadas de um arquivo ou do projeto inteiro, com prévia. Uma chamada que é a única linha de um bloco vira `pass`. |
| **Qualidade de código** | Imports e funções sem uso, `except:` sem tipo, breakpoints esquecidos, TODOs e funções complexas, no painel Problems. |
| **`.env`** | Chaves faltando no `.env` ou no `.env.example`, com correção rápida que adiciona a chave. |
| **Modelos** | Novo script, classe, data class, teste ou pacote pelo botão direito no Explorer. |
| **Snippets** | Salve o código que você reusa num formulário (nome, tags, código) e insira com um clique; `{{nome}}` vira um campo a preencher. |
| **Requisições HTTP** | Envie requisições, salve as que você repete e veja a resposta ao lado do código. |

O [README da extensão](vscode/README.md) (em inglês) explica cada recurso e suas configurações.

## A API do `siren()`

O `siren()` devolve o que recebe, então pode ficar dentro de uma expressão:

```python
siren(x, dados, usuario)            # vários valores de uma vez
total = siren(calcular())           # continua devolvendo o valor de calcular()
siren(pedido, label="ANTES DE SALVAR")  # marca a chamada
siren(x, timeit=True)               # mostra também quanto tempo levou
siren(itens, if_len_gt=100)         # só quando len(itens) > 100
siren(x, if_equals=5)               # também: if_len_lt, if_true, if_false
siren(x, quiet=True)                # mantém a chamada, sem imprimir nada
```

Outras ferramentas no mesmo objeto:

```python
@siren.trace                        # registra cada chamada: argumentos, retorno, tempo e exceções
def somar(a, b):
    return a + b

siren.diff(antes, depois)           # o que mudou entre dois dicts, listas ou objetos
siren.breakpoint()                  # pausa e mostra as variáveis locais
siren.memory(top=5)                 # memória atual e de pico, mais os maiores pontos de alocação (Python 3.4+)

with siren.catch():                 # mostra um traceback legível e relança a exceção
    chamada_arriscada()

siren.patch_requests()              # registra toda chamada feita com requests (também: patch_httpx)
siren.set_quiet(True)               # silencia todas as chamadas até set_quiet(False)
siren.set_logfile("debug.log")      # também grava a saída num arquivo
```

O `@siren.trace` aceita `timeit`, `show_args`, `show_return` e `show_type`, todos `True` por padrão.

## Como o runtime entra

A extensão coloca o pacote `siren` que ela traz no `PYTHONPATH` dos terminais integrados abertos depois que ela inicia (inclusive o **Run Python File**) e das sessões de debug Python. Um módulo `sitecustomize` registra o `siren` como builtin; se o seu ambiente já tem um `sitecustomize`, ele continua rodando.

Programas iniciados em qualquer outro lugar não recebem o runtime: um terminal externo, um terminal aberto antes de a extensão carregar, um servidor iniciado fora do VS Code ou um script que um assistente de código com IA roda para você. Nesses casos, um `siren(x)` esquecido gera `NameError`; por isso, remova as chamadas antes de entregar o código.

## Versões do Python

O runtime suporta Python 2.7 e 3.6+. O CI roda os testes no Python 3.10 a 3.13 (Linux, Windows e macOS) e uma verificação de ponta a ponta de um projeto legado (sintaxe Python 2, texto com acentos, linha `coding:`) no Python 2.7 e no 3.

## Siren Pro

O Pro vai trazer a produção para dentro do editor: as exceções dos seus servidores na linha que as gerou, e o tempo de resposta real de cada função acima da sua definição, além de alertas, sincronização entre máquinas e espaços de trabalho para times. Ele está em desenvolvimento; a extensão gratuita continua gratuita.

## Repositório

| Caminho | O que é |
| --- | --- |
| `vscode/` | A extensão do VS Code (TypeScript) |
| `siren/` | O runtime Python que a extensão traz: `siren()`, limpeza, qualidade, snippets, HTTP |
| `siren/_bridge.py` | Ponto de entrada JSON via stdin que a extensão usa para chamar o lado Python |
| `tests/` | Testes Python e o `smoke_legacy.py`, a verificação de ponta a ponta que também roda no Python 2.7 |

### Desenvolvimento

```bash
# Testes Python
python -m unittest discover -s tests
python tests/smoke_legacy.py

# Extensão: testes unitários e depois os de integração num VS Code de verdade
cd vscode
npm ci
npm test
npm run test:integration
```

Com a pasta `vscode/` aberta no VS Code, aperte F5 para testar a extensão numa janela de desenvolvimento.

### Publicação

Atualize o `version` em `vscode/package.json` e adicione uma entrada em `vscode/CHANGELOG.md`, faça o merge na `main` e envie uma tag `vscode-v<versão>` na `main`. O [workflow de publicação](.github/workflows/publish-vscode.yml) roda todos os testes e publica no Marketplace.

### O pacote `siren-debug` no PyPI

O Siren começou como o pacote `siren-debug` no PyPI, com os comandos de terminal `siren-*`. Esse pacote está sendo aposentado em favor da extensão, que inclui tudo o que ele fazia. A última versão continua instalável para quem ainda depende dela.

## Licença

[MIT](LICENSE)
