import gzip
import io
import json
import re
import shutil
import threading
import time
from pathlib import Path

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
RAW = "https://web.archive.org/web/{ts}id_/{url}"
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "wayback"
DELAY = 1.0  # pour pas se faire rate-limit par archive.org

USER_AGENT = "outcome-switching-meta-research (academic, low rate)"
_local = threading.local()


def _session():
    if not hasattr(_local, "s"):
        _local.s = requests.Session()
        _local.s.headers["User-Agent"] = USER_AGENT
    return _local.s


class Unavailable(Exception):
    pass


def _get_json(url, params=None, tries=6):
    wait = 10
    for _ in range(tries):
        try:
            r = _session().get(url, params=params, timeout=90)
            time.sleep(DELAY)
            if r.status_code == 404:
                return None
            if r.status_code == 200:
                text = r.text.strip()
                if not text:
                    return []
                return json.loads(text)  # une page HTML « Temporarily Offline » lève ici
            if r.status_code == 429:
                wait = max(wait, 60)
        except (requests.RequestException, ValueError):
            pass
        time.sleep(wait)
        wait = min(wait * 2, 600)
    raise Unavailable(url)


MIN_FREE = 500 * 2**20  # les données brutes font ~540 Mo, on garde de la marge


class DiskFull(Exception):
    pass


def read_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_gz(path, data):
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise DiskFull(f"moins de {MIN_FREE >> 20} Mo libres")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.GzipFile(tmp, "wb", mtime=0) as raw, io.TextIOWrapper(raw, encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(path)


def _cached(path, fetch):
    if path.exists():
        return read_gz(path)
    data = fetch()
    if data is not None:
        write_gz(path, data)
    return data


def list_versions(nct):
    # -> {n° de version: (timestamp, url)}
    # l'historique n'est plus dispo sur ct.gov depuis mars 2026, archive.org l'a crawlé en fev 2025
    rows = _cached(CACHE / nct / "cdx.json.gz", lambda: _get_json(CDX, {
        "url": f"clinicaltrials.gov/api/int/studies/{nct}", "matchType": "prefix",
        "output": "json", "filter": "statuscode:200", "fl": "timestamp,original"}))
    versions = {}
    for ts, url in (rows or [])[1:]:
        m = re.search(r"/history/(\d+)$", url)
        if m:
            versions.setdefault(int(m.group(1)), (ts, url))
    return versions


def get_version(nct, n, ts, url):
    return _cached(CACHE / nct / f"v{n}.json.gz", lambda: _get_json(RAW.format(ts=ts, url=url)))
