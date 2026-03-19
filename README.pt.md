Perfeito! Aqui está a versão completa em **português**, em Markdown, pronta para copy-paste:

````markdown
# Siren

Ferramenta minimalista de debug para Python.

Siren é uma alternativa leve ao `print` / `pprint`, projetada para funcionar  
com qualquer versão do Python 3 e qualquer framework como Django, Flask, FastAPI ou scripts Python puros.

O objetivo principal do Siren é simples:

✔ Depurar rapidamente  
✔ Rastrear funções automaticamente  
✔ Medir tempo de execução  
✔ Remover linhas de debug automaticamente  
✔ Funcionar em qualquer lugar  
✔ Sem dependências  

---

## Funcionalidades

- Funciona em Python 3+  
- Sem dependências externas  
- Usa `print` ou `pprint` automaticamente para objetos complexos  
- Mostra arquivo e número da linha  
- Timer opcional (`timeit=True`)  
- Decorator trace para registrar chamadas e retornos de funções (`@siren.trace`)  
- Pode remover todas as chamadas de debug automaticamente  
- Cleaner seguro usando tokenize do Python  
- Funciona em Django / Flask / FastAPI / scripts / CLI  
- Saída colorida com emoji  

---

## Instalação

Instale o Siren via pip:

```bash
pip install siren-debug
````

Em seguida, adicione `siren` à configuração do seu framework:

```python
# Exemplo Django
INSTALLED_APPS = [
    # ...
    "siren",
]
```

---

## Uso

```python
x = 10
data = {"a": 1, "b": [1, 2, 3]}

siren(x)
siren(data)
```

Saída:

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN core.py:11] data = {'a': 1, 'b': [1, 2, 3]}
```

Siren usa `pprint` automaticamente para objetos complexos.

---

## Múltiplos valores

```python
siren(x, data, user)
```

---

## Timer

```python
siren(x, timeit=True)
```

Exibe o valor **e** o tempo de execução:

```text
[🧜‍ SIREN core.py:10] x = 10
[🧜‍ SIREN TIME] 0.000123s
```

---

## Decorator Trace

```python
@siren.trace
def soma(a, b):
    return a + b

soma(2, 3)
```

Saída:

```text
[🧜‍ SIREN core.py:10] Calling soma
[🧜‍ SIREN core.py:11] Returned from soma -> 5
```

---

## Cleaner (remover todas as chamadas de siren)

Esta é a principal funcionalidade.

Remove todas as linhas que chamam `siren(...)`:

```bash
siren-clean
```

Exemplo:

**Antes:**

```python
siren(x)
print("hello")
siren(data)
```

**Depois:**

```python
print("hello")
```

O cleaner é seguro e usa o tokenize do Python.
Ele **não remove comentários ou strings**.

---

## Por que usar Siren?

Usar `print` ou `pprint` para debug é fácil,
mas removê-los depois é doloroso.

Siren resolve isso.

Use:

```python
siren(value)
```

E depois:

```bash
siren-clean
```

Pronto.

---

## Objetivos

* Minimalista
* Seguro
* Cross-version
* Sem dependências
* Limpeza fácil
* Funciona offline
* Rastreio de funções e medição de tempo

---

## Licença

MIT
