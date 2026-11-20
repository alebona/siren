# -*- coding: utf-8 -*-
"""
End-to-end check of Siren in real web frameworks, the way people use them:
the framework's own dev server, with its autoreloader on (which runs the app
in a child process), a request to a view that calls siren() with no import,
then removing the calls from the project.

    python tests/frameworks_e2e.py django flask fastapi

The frameworks must be installed. Runs on Python 2.7 (Django 1.11, Flask 1.1)
and 3. Exits non-zero and prints what failed.
"""
from __future__ import print_function

import io
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback

try:
    from urllib.request import urlopen
    from urllib.error import URLError
except ImportError:  # Python 2
    from urllib2 import urlopen, URLError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNTIME = os.path.join(ROOT, "vscode", "python")  # holds sitecustomize.py
MARKER = u"pedido aprovado"


def write(path, text):
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def read_bytes(path):
    with io.open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")[-4000:]


def line_of(path, needle):
    for number, line in enumerate(read(path).splitlines(), 1):
        if needle in line:
            return number
    raise AssertionError("%r not in %s" % (needle, path))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def get(url, timeout=60):
    """GET url, retrying until the server is up."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            return urlopen(url, timeout=10).read().decode("utf-8")
        except (URLError, socket.error, IOError) as e:
            last = e
            time.sleep(0.5)
    raise AssertionError("no answer from %s: %s" % (url, last))


class Server(object):
    """The framework's dev server in its own process group, stopped with all its children."""

    def __init__(self, args, cwd, env, log):
        self.log = log
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["preexec_fn"] = os.setsid
        self.proc = subprocess.Popen(args, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, **kwargs)

    def stop(self):
        if self.proc.poll() is not None:
            return
        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except OSError:
                pass
        self.proc.wait()


# --- the projects -----------------------------------------------------------

def django_project(proj):
    write(os.path.join(proj, "manage.py"), u"""import os, sys
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "loja.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
""")
    write(os.path.join(proj, "loja", "__init__.py"), u"")
    write(os.path.join(proj, "loja", "settings.py"), u"""SECRET_KEY = "test"
DEBUG = True
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "loja.urls"
INSTALLED_APPS = []
MIDDLEWARE = []
DATABASES = {}
""")
    write(os.path.join(proj, "loja", "urls.py"), u"""try:
    from django.urls import re_path as url
except ImportError:  # Django 1.x
    from django.conf.urls import url
from loja import views

urlpatterns = [url(r"^pedido/$", views.pedido), url(r"^dobro/$", views.dobro)]
""")
    views = os.path.join(proj, "loja", "views.py")
    write(views, u"""# -*- coding: utf-8 -*-
from django.http import HttpResponse


def pedido(request):
    total = 42
    siren(u"pedido aprovado", total)
    return HttpResponse("ok")


@siren.trace
def dobro(request):
    return HttpResponse(str(int(request.GET.get("n", 1)) * 2))
""")
    port = free_port()
    return {
        "args": [sys.executable, "manage.py", "runserver", "127.0.0.1:%d" % port],
        "env": {},
        "base": "http://127.0.0.1:%d" % port,
        "paths": {"marker": "/pedido/", "double": "/dobro/?n=3"},
        "double": "6",
        "view_file": views,
    }


def flask_project(proj):
    app = os.path.join(proj, "app.py")
    # Two traced routes: Flask names routes after the function, so the
    # decorator must keep the name or the app won't even start.
    write(app, u"""# -*- coding: utf-8 -*-
from flask import Flask, request

app = Flask(__name__)


@app.route("/pedido")
def pedido():
    total = 42
    siren(u"pedido aprovado", total)
    return "ok"


@app.route("/dobro")
@siren.trace
def dobro():
    return str(int(request.args.get("n", 1)) * 2)


@app.route("/triplo")
@siren.trace
def triplo():
    return str(int(request.args.get("n", 1)) * 3)
""")
    port = free_port()
    return {
        "args": [sys.executable, "-m", "flask", "run", "--host", "127.0.0.1", "--port", str(port), "--reload"],
        "env": {"FLASK_APP": "app.py", "FLASK_DEBUG": "1"},
        "base": "http://127.0.0.1:%d" % port,
        "paths": {"marker": "/pedido", "double": "/dobro?n=3"},
        "double": "6",
        "view_file": app,
    }


def fastapi_project(proj):
    main = os.path.join(proj, "main.py")
    # Traced endpoints, sync and async: FastAPI reads parameters from the
    # signature and awaits coroutine functions, so the decorator must keep both.
    write(main, u"""from fastapi import FastAPI

app = FastAPI()


@app.get("/pedido")
def pedido():
    total = 42
    siren("pedido aprovado", total)
    return {"ok": True}


@app.get("/dobro")
@siren.trace
def dobro(n: int = 1):
    return n * 2


@app.get("/async-dobro")
@siren.trace
async def async_dobro(n: int = 1):
    siren("async view", n)
    return n * 2
""")
    port = free_port()
    return {
        "args": [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port), "--reload"],
        "env": {},
        "base": "http://127.0.0.1:%d" % port,
        "paths": {"marker": "/pedido", "double": "/dobro?n=3", "async": "/async-dobro?n=4"},
        "double": "6",
        "async": "8",
        "view_file": main,
    }


PROJECTS = {"django": django_project, "flask": flask_project, "fastapi": fastapi_project}


# --- the check --------------------------------------------------------------

def check_framework(name, work):
    proj = os.path.join(work, name)
    events = os.path.join(work, name + "-events.jsonl")
    spec = PROJECTS[name](proj)
    env = dict(os.environ)
    # What the extension sets for VS Code terminals (or Enable everywhere).
    env.update({
        # The repo root first, so `import siren` gets this checkout, not the
        # copy npm build leaves in vscode/python; sitecustomize comes from there.
        "PYTHONPATH": os.pathsep.join([ROOT, RUNTIME]),
        "SIREN_VSCODE_EVENTS": events,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
    })
    env.update(spec["env"])
    log_path = os.path.join(work, name + ".log")
    with io.open(log_path, "wb") as log:
        server = Server(spec["args"], proj, env, log)
        try:
            assert "ok" in get(spec["base"] + spec["paths"]["marker"]), "marker view"
            assert get(spec["base"] + spec["paths"]["double"]).strip() == spec["double"], "traced view"
            if "async" in spec["paths"]:
                assert get(spec["base"] + spec["paths"]["async"]).strip() == spec["async"], "async traced view"
            time.sleep(0.5)
        except Exception as e:
            server.stop()
            raise AssertionError("%s\nserver log:\n%s" % (e, read_bytes(log_path)))
        finally:
            server.stop()

    # The value reached the editor, from the right file and line.
    lines = [json.loads(l) for l in read(events).splitlines() if l.strip()] if os.path.exists(events) else []
    marker = [e for e in lines if e["value"] == MARKER]
    assert marker, "no siren() event from the view; events: %r\nserver log:\n%s" % (lines, read(log_path))
    assert os.path.basename(marker[0]["file"]) == os.path.basename(spec["view_file"]), marker[0]
    assert marker[0]["line"] == line_of(spec["view_file"], u'siren(u"pedido aprovado"' if name != "fastapi" else u'siren("pedido aprovado"'), marker[0]
    totals = [e for e in lines if e["value"] == "42"]
    assert totals, lines
    if name == "fastapi":
        assert any(e["value"] == "async view" for e in lines), lines
    log = read(log_path)
    assert "Returned from dobro" in log, "trace output missing from the server log:\n" + log

    # Removing the calls leaves a project that still runs.
    out = subprocess.check_output([sys.executable, "-m", "siren.clean", proj],
                                  env=env, cwd=proj).decode("utf-8", "replace")
    for path in [spec["view_file"]]:
        text = read(path)
        assert "siren" not in text, text
        compile(text.encode("utf-8"), path, "exec")
    return out


def main():
    names = sys.argv[1:] or sorted(PROJECTS)
    print("Python %s" % sys.version.split()[0])
    work = tempfile.mkdtemp()
    failures = []
    try:
        for name in names:
            try:
                check_framework(name, work)
                print("  ok   %s" % name)
            except Exception:
                failures.append(name)
                print("  FAIL %s" % name)
                traceback.print_exc()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if failures:
        print("\nfailed: %s" % ", ".join(failures))
        sys.exit(1)
    print("\nall frameworks passed")


if __name__ == "__main__":
    main()
