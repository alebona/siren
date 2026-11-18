# -*- coding: utf-8 -*-
"""
End-to-end smoke test of everything the VS Code extension asks of Python,
on a project that looks like a real legacy codebase: Python 2 syntax,
accented text, a coding declaration. Runs on Python 2.7 and 3 with only the
standard library (no pytest, no mock), as a script:

    python tests/smoke_legacy.py

Exits non-zero and prints what failed.
"""
from __future__ import print_function

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(ROOT, "vscode", "python")  # holds sitecustomize.py

LEGACY_MODULE = u'''# -*- coding: utf-8 -*-
from siren import siren


def reajustar(servicos, percentual):
    siren("Calculando preços reajustados de %d serviços..." % len(servicos))
    total = 0
    for s in servicos:
        siren(s)
    try:
        total = sum(s["preço"] for s in servicos) * (1 + percentual)
    except Exception, e:
        print "erro:", e
    print "total reajustado:", total
    return total
'''

RUNNABLE = u'''# -*- coding: utf-8 -*-
servicos = [{"nome": u"Manutenção", "preço": 10}, {"nome": "Limpeza", "preço": 5}]
siren("Calculando preços reajustados de %d serviços..." % len(servicos))
siren(u"texto unicode: ação", label="rótulo")
for s in servicos:
    siren(s)
siren(len(servicos), timeit=True)


@siren.trace
def aplicar(nome, descricao=u"ação"):
    return u"%s: %s" % (nome, descricao)


aplicar(u"Manutenção")
siren.diff({u"preço": 1, "nome": "ação"}, {u"preço": 2, "nome": "ação"})
print("fim")
'''

failures = []


def check(name):
    def wrap(fn):
        try:
            fn()
            print("  ok   " + name)
        except Exception:
            failures.append(name)
            print("  FAIL " + name)
            traceback.print_exc()
        return fn
    return wrap


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def read(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        return f.read()


def env_with(**extra):
    env = dict(os.environ)
    env.update(extra)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run(args, cwd, env, stdin=None):
    proc = subprocess.Popen(
        args, cwd=cwd, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(stdin)
    if proc.returncode != 0:
        raise AssertionError("exit %d\nstdout: %s\nstderr: %s" % (
            proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")))
    return out.decode("utf-8"), err.decode("utf-8")


def bridge(op, args, cwd, env):
    out, _ = run([sys.executable, "-m", "siren._bridge"], cwd, env,
                 stdin=json.dumps({"op": op, "args": args}).encode("utf-8"))
    response = json.loads(out)
    if not response.get("ok"):
        raise AssertionError("bridge %s failed: %s" % (op, response.get("error")))
    return response["result"]


def main():
    work = tempfile.mkdtemp()
    home = os.path.join(work, "home")
    proj = os.path.join(work, "projeto")
    os.makedirs(home)
    os.makedirs(proj)
    events = os.path.join(work, "events.jsonl")
    # What the extension sets for terminals and debug sessions.
    pythonpath = os.pathsep.join([RUNTIME, ROOT])
    env = env_with(PYTHONPATH=pythonpath, SIREN_VSCODE_EVENTS=events, HOME=home, USERPROFILE=home)
    print("Python %s" % sys.version.split()[0])

    @check("run a script that calls siren() with accents, no import (sitecustomize)")
    def _():
        script = os.path.join(proj, "rodar.py")
        write(script, RUNNABLE)
        out, err = run([sys.executable, script], proj, env)
        assert u"preços" in out, out
        assert u"Returned from aplicar" in out, out  # @siren.trace
        assert u"(changed)" in out, out  # siren.diff
        assert out.rstrip().endswith(u"fim"), out  # the script ran to the end
        assert not err.strip(), err

    @check("each siren() call reports file, line and value to the editor")
    def _():
        lines = [json.loads(l) for l in read(events).splitlines() if l.strip()]
        assert len(lines) >= 5, lines
        first = lines[0]
        assert first["file"].endswith("rodar.py"), first
        assert first["line"] == 3, first
        assert u"preços" in first["value"], first
        labelled = [l for l in lines if l.get("label")]
        assert labelled and labelled[0]["label"] == u"rótulo", lines

    legacy = os.path.join(proj, "servico.py")

    @check("code quality on a Python 2 file (bridge)")
    def _():
        write(legacy, LEGACY_MODULE)
        result = bridge("quality", {"path": legacy, "threshold": 10}, proj, env)
        if sys.version_info[0] >= 3:
            # Python 2 syntax can't be parsed by Python 3: reported, not crashing.
            assert result["unparseable"], result
        else:
            assert result["files"] and not result["unparseable"], result

    @check("remove siren() calls from a Python 2 file")
    def _():
        write(legacy, LEGACY_MODULE)
        out, _ = run([sys.executable, "-m", "siren.clean", legacy], proj, env)
        cleaned = read(legacy)
        assert "siren" not in cleaned, cleaned
        assert "for s in servicos:\n        pass\n" in cleaned, cleaned
        assert u'print "total reajustado:", total' in cleaned, cleaned
        assert "3 linhas removidas" in out, out

    @check("dry run lists the file and count")
    def _():
        write(legacy, LEGACY_MODULE)
        out, _ = run([sys.executable, "-m", "siren.clean", legacy, "--dry-run"], proj, env)
        assert "(3 linhas)" in out, out
        assert "siren" in read(legacy)

    @check("snippets: save with accents, list, rename, remove (bridge)")
    def _():
        bridge("snippets_save", {"name": "consulta", "content": u"SELECT preço FROM {{tabela}}", "tags": ["sql"]}, proj, env)
        listed = bridge("snippets_list", {}, proj, env)
        assert [s["name"] for s in listed] == ["consulta"], listed
        assert u"preço" in listed[0]["content"], listed
        bridge("snippets_rename", {"old": "consulta", "new": "consulta2"}, proj, env)
        bridge("snippets_remove", {"name": "consulta2"}, proj, env)
        assert bridge("snippets_list", {}, proj, env) == []

    @check("HTTP requests: save, list, load, remove (bridge)")
    def _():
        bridge("http_save", {"name": "itens", "method": "POST", "url": "http://127.0.0.1:9/x", "json": {"preço": 1}}, proj, env)
        assert [r["name"] for r in bridge("http_list", {}, proj, env)] == ["itens"]
        assert bridge("http_load", {"name": "itens"}, proj, env)["method"] == "POST"
        assert bridge("http_remove", {"name": "itens"}, proj, env) is True

    @check("new file from template (bridge)")
    def _():
        created = bridge("scaffold", {"template": "class", "name": "Pedido", "path": proj}, proj, env)
        assert os.path.isfile(created[0]), created

    shutil.rmtree(work, ignore_errors=True)
    if failures:
        print("\n%d check(s) failed: %s" % (len(failures), ", ".join(failures)))
        sys.exit(1)
    print("\nall checks passed")


if __name__ == "__main__":
    main()
