import json
import socket
import sys

import pytest
import requests

from conftest import ROOT, STUB_LABEL, StubOpenRouter

sys.path.insert(0, str(ROOT / "classify"))
sys.path.insert(0, str(ROOT / "demo"))


def test_status(offline_server, live_server):
    assert requests.get(offline_server + "/api/status").json()["live"] is False
    s = requests.get(live_server + "/api/status").json()
    assert s["live"] is True and s["live_left"] == 30


def test_page_and_data_served(offline_server):
    r = requests.get(offline_server + "/")
    assert r.status_code == 200 and "Outcome Switch Monitor" in r.text
    assert r.headers["Content-Type"].startswith("text/html")
    assert len(requests.get(offline_server + "/data/trials.json").json()) == 5634


def test_trial_human_labelled(offline_server):
    p = requests.get(offline_server + "/api/trial/NCT03504423").json()
    assert p["source"] == "corpus"
    assert p["trial"]["human"]["verdict"] == "changement"
    assert set(p["trial"]["human"]["types"]) == {"retrograde", "ajoute"}
    assert p["trial"]["ai"]["verdict"] in {"identique", "reformulation", "precision", "changement", "indeterminable"}
    assert p["item"]["registered"] and p["item"]["deposited"]


def test_trial_auto_identical(offline_server):
    t = next(t for t in json.loads((ROOT / "demo/app/data/trials.json").read_text()) if t.get("auto"))
    p = requests.get(offline_server + f"/api/trial/{t['nct']}").json()
    assert p["trial"]["auto"] == "identique" and "ai" not in p["trial"]


@pytest.mark.parametrize("path,status,code", [
    ("/api/trial/NCT00000000", 404, "not_found"),
    ("/api/trial/hello", 400, "bad_id"),
    ("/api/history/NCT0000", 400, "bad_id"),
    ("/api/nothing", 404, "not_found"),
    ("/data/../../README.md", 404, "not_found"),
])
def test_errors(offline_server, path, status, code):
    r = requests.get(offline_server + path)
    assert r.status_code == status and r.json()["error"] == code


def test_path_traversal_raw(offline_server):
    host, port = offline_server.split("//")[1].split(":")
    with socket.create_connection((host, int(port))) as s:
        s.sendall(b"GET /../../README.md HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        resp = s.recv(4096).decode()
    assert " 404 " in resp.splitlines()[0]


def test_classify_requires_key(offline_server):
    r = requests.post(offline_server + "/api/classify/NCT01070316")
    assert r.status_code == 503 and r.json()["error"] == "no_key"


def test_classify_corpus_trial_needs_no_model(live_server):
    n = len(StubOpenRouter.calls)
    p = requests.post(live_server + "/api/classify/NCT03504423").json()
    assert p["source"] == "corpus" and len(StubOpenRouter.calls) == n


def test_history_cached_example(offline_server, stats):
    nct = stats["showcase"][0]["nct"]
    h = requests.get(offline_server + f"/api/history/{nct}", timeout=60).json()
    assert h["nct"] == nct and h["versions"] and any(v["is_reference"] for v in h["versions"])
    assert all(v["phase"] in {"before_start", "during", "after_primary_completion"} for v in h["versions"])


@pytest.mark.network
def test_classify_live_with_stub_model(live_server):
    r = requests.post(live_server + "/api/classify/NCT01070316", timeout=180)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["source"] == "live" and p["item"]["registered"] and p["item"]["deposited"]
    assert p["trial"]["ai"]["verdict"] == STUB_LABEL["verdict"] and p["trial"]["ai"]["model"] == "stub/model"
    call = StubOpenRouter.calls[-1]
    assert call["auth"] == "Bearer sk-test"
    assert "Write the note in English." in call["body"]["messages"][1]["content"]
    assert call["body"]["response_format"]["type"] == "json_schema"
    # mis en cache : servi ensuite par /api/trial, sans nouvel appel au modèle
    n = len(StubOpenRouter.calls)
    assert requests.get(live_server + "/api/trial/NCT01070316").json()["source"] == "live"
    assert requests.post(live_server + "/api/classify/NCT01070316").status_code == 200
    assert len(StubOpenRouter.calls) == n
    assert requests.get(live_server + "/api/status").json()["live_left"] == 29


@pytest.mark.skipif(not any((ROOT / "data" / "wayback").glob("NCT*/v*.json.gz"))
                    or len(list((ROOT / "data" / "current").glob("*.json.gz"))) < 5600,
                    reason="données brutes absentes (non versionnées) : lancer collect/run.py")
def test_build_item_matches_corpus():
    from batches import items
    from build_items import build_item
    idx = {r["nct"]: r for r in map(json.loads, (ROOT / "data/index.jsonl").read_text().splitlines())}
    its = items()
    for nct in list(its)[:: len(its) // 25]:
        assert build_item(nct, idx[nct]["ref_version"]) == its[nct]


def test_stats_consistent(stats):
    c = stats["counts"]
    assert c["trials"] == 5634 and c["auto_identical"] == 665 and c["non_identical"] == 4969
    assert c["human_labelled"] == 95 and c["ai_labelled"] == 4969
    assert round(100 * stats["human"]["changement"]["non_identical"][0]) == 32
    assert round(100 * stats["human"]["majeur"]["non_identical"][0]) == 17
    assert stats["agreement"] and len(stats["showcase"]) >= 7
