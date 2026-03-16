# Siren

Ferramenta minimalista de debug para Python.

Siren é uma alternativa leve ao print / pprint,
projetada para funcionar em qualquer versão do Python,
incluindo Python 2.7, e qualquer framework como Django,
Flask, FastAPI ou scripts simples.

Objetivo do Siren:

✔ Debug rápido  
✔ Remover debug automaticamente  
✔ Funcionar em qualquer lugar  
✔ Sem dependências  

---

## Recursos

- Funciona no Python 2.7+
- Funciona no Python 3+
- Sem dependências externas
- Usa print ou pprint automaticamente
- Mostra arquivo e linha
- Remove chamadas automaticamente
- Cleaner seguro com tokenize
- Funciona em Django / Flask / scripts

---

## Instalação (local)

Clone o repositório:


git clone https://github.com/seuuser/siren.git


Copie a pasta `siren` para dentro do seu projeto
ou adicione ao PYTHONPATH.

Exemplo:


from siren import siren


---

## Uso


from siren import siren

x = 10
data = {"a": 1, "b": [1, 2, 3]}

siren(x)
siren(data)


Saída:


[SIREN arquivo.py:10] 10
[SIREN arquivo.py:11] {'a': 1, 'b': [1, 2, 3]}


O Siren usa pprint automaticamente para objetos complexos.

---

## Múltiplos valores


siren(x, data, user)


---

## Cleaner (remover todos os siren)

Principal recurso da ferramenta.

Remove todas as linhas com `siren(...)`:


python -m siren.clean .


ou


python siren/clean.py .


Exemplo:

Antes:


siren(x)
print("hello")
siren(data)


Depois:


print("hello")


O cleaner é seguro e usa tokenize.

Não remove comentários nem strings.

---

## Por que usar Siren?

Usar print para debug é fácil,
mas remover depois é chato.

Siren resolve isso.

Use:


siren(valor)


Depois:


limpar tudo


Pronto.

---

## Objetivos

- Minimalista
- Seguro
- Compatível com versões antigas
- Sem dependências
- Fácil de limpar
- Funciona offline

---

## Licença

MIT