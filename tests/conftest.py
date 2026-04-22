# le serveur de démo tourne en sous-processus, et openrouter est remplacé par un faux serveur
# (pas d'appel payant). -m "not e2e" pour sauter les tests navigateur
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

STUB_LABEL = {"verdict": "changement", "types": ["retrograde", "ajoute"], "gravite": "majeur",
              "note": "STUB: test label returned by the simulated model."}


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class StubOpenRouter(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        StubOpenRouter.calls.append({"auth": self.headers.get("Authorization"), "body": body})
        out = json.dumps({"model": "stub/model", "usage": {"cost": 0.0001},
                          "choices": [{"message": {"content": json.dumps(STUB_LABEL)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture(scope="session")
def stub_openrouter():
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), StubOpenRouter)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/api/v1/chat/completions"
    srv.shutdown()


def start_server(env_extra, tmp):
    port = free_port()
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    env.update({"DEMO_CACHE": str(tmp / f"live-{port}.jsonl"), **env_extra})
    proc = subprocess.Popen([PY, str(ROOT / "demo" / "server.py"), "--port", str(port)], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            requests.get(base + "/api/status", timeout=1)
            return proc, base
        except requests.RequestException:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("le serveur de démo n'a pas démarré :\n" + proc.stdout.read())


@pytest.fixture(scope="session")
def live_server(stub_openrouter, tmp_path_factory):
    proc, base = start_server({"OPENROUTER_API_KEY": "sk-test", "OPENROUTER_URL": stub_openrouter},
                              tmp_path_factory.mktemp("live"))
    yield base
    proc.terminate()


@pytest.fixture(scope="session")
def offline_server(tmp_path_factory):
    proc, base = start_server({}, tmp_path_factory.mktemp("offline"))
    yield base
    proc.terminate()


@pytest.fixture(scope="session")
def stats():
    return json.loads((ROOT / "demo" / "app" / "data" / "stats.json").read_text())


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: tests navigateur (Playwright)")
    config.addinivalue_line("markers", "network: interroge ClinicalTrials.gov")
