# collecte du corpus : enregistrements actuels (API v2) + versions historiques (wayback)
# python collect/run.py [--limit N] [--workers 4]
# ~10h en tout, on peut couper et relancer, ça reprend où ça en était
import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wayback import ROOT, DiskFull, Unavailable, get_version, list_versions, read_gz, write_gz

API = "https://clinicaltrials.gov/api/v2/studies"
QUERY = {
    "query.term": "AREA[Phase]PHASE3 AND AREA[DesignAllocation]RANDOMIZED "
    "AND AREA[PrimaryCompletionDate]RANGE[2012-01-01,2022-12-31]",
    "filter.overallStatus": "COMPLETED",
    "aggFilters": "results:with",
}
DATA = ROOT / "data"
CURRENT = DATA / "current"
INDEX = DATA / "index.jsonl"


def fetch_current():
    CURRENT.mkdir(parents=True, exist_ok=True)
    ids_file = DATA / "corpus_ids.json"
    if ids_file.exists():
        return json.loads(ids_file.read_text())
    ids, token = [], None
    while True:
        params = {**QUERY, "pageSize": 200}
        if token:
            params["pageToken"] = token
        d = requests.get(API, params=params, timeout=120).json()
        for s in d["studies"]:
            nct = s["protocolSection"]["identificationModule"]["nctId"]
            write_gz(CURRENT / f"{nct}.json.gz", s)
            ids.append(nct)
        print(f"  enregistrements actuels : {len(ids)}", flush=True)
        token = d.get("nextPageToken")
        if not token:
            break
        time.sleep(0.5)
    ids_file.write_text(json.dumps(ids))
    return ids


def primaries(v):
    return v["study"]["protocolSection"].get("outcomesModule", {}).get("primaryOutcomes", [])


def submit_date(v):
    return v["study"]["protocolSection"]["statusModule"].get("lastUpdateSubmitDate", "")


def signature(outcomes):
    norm = lambda s: " ".join((s or "").lower().split())
    return sorted(norm(o["measure"]) + "|" + norm(o.get("timeFrame")) for o in outcomes)


def collect_trial(nct):
    versions = list_versions(nct)
    if not versions:
        return {"nct": nct, "status": "absent_wayback"}
    last = max(versions)
    complete = set(versions) == set(range(last + 1))
    load = lambda n: get_version(nct, n, *versions[n]) if n in versions else None
    cur = read_gz(CURRENT / f"{nct}.json.gz")
    start = cur["protocolSection"]["statusModule"].get("startDateStruct", {}).get("date", "")[:7]

    # version de ref = dernière soumise au plus tard le mois de début. dichotomie pour pas tout télécharger
    lo, hi, ref = 0, last, None
    while lo <= hi:
        mid = (lo + hi) // 2
        v = load(mid)
        if v is None:
            return {"nct": nct, "status": "trou_versions", "n_versions": len(versions)}
        if submit_date(v)[:7] <= start:
            ref, lo = mid, mid + 1
        else:
            hi = mid - 1
    retro = ref is None
    ref = 0 if retro else ref
    ref_sig = signature(primaries(load(ref)))

    # première version où les critères principaux changent (dichotomie aussi)
    lo, hi, change = ref + 1, last, None
    while lo <= hi:
        mid = (lo + hi) // 2
        v = load(mid)
        if v is None:
            return {"nct": nct, "status": "trou_versions", "n_versions": len(versions)}
        if signature(primaries(v)) != ref_sig:
            change, hi = mid, mid - 1
        else:
            lo = mid + 1
    load(last)  # juste pour l'avoir en cache
    return {
        "nct": nct, "status": "ok", "n_versions": len(versions), "complete": complete,
        "start": start, "ref_version": ref, "retrospective": retro,
        "first_change_version": change,
        "first_change_date": submit_date(load(change)) if change is not None else None,
        "last_version": last, "last_version_date": submit_date(load(last)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    ids = fetch_current()
    # ordre aléatoire fixe : si on coupe en route on a quand même un échantillon aléatoire
    order = random.Random(2026).sample(ids, len(ids))
    done = set()
    if INDEX.exists():
        done = {json.loads(l)["nct"] for l in INDEX.read_text().splitlines() if l.strip()}
    todo = [n for n in order if n not in done][: args.limit]
    print(f"corpus {len(ids)} | déjà faits {len(done)} | à faire {len(todo)}", flush=True)

    stop = threading.Event()
    lock = threading.Lock()
    count = [0]
    t0 = time.time()

    def work(nct):
        if stop.is_set():
            return
        try:
            row = collect_trial(nct)
        except DiskFull as e:
            print(f"disque plein ({e}), on arrête", flush=True)
            stop.set()
            return
        except Unavailable as e:
            print(f"wayback down ({e}), relancer plus tard", flush=True)
            stop.set()
            return
        except Exception as e:  # quelques essais mal formés, on note et on continue
            row = {"nct": nct, "status": "erreur", "error": repr(e)[:300]}
        with lock:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            count[0] += 1
            i = count[0]
            if i % 20 == 0 or i == len(todo):
                rate = (time.time() - t0) / i
                eta = rate * (len(todo) - i) / 3600
                print(f"{len(done) + i}/{len(ids)}  {rate:.1f} s/essai  reste ~{eta:.1f} h", flush=True)

    with INDEX.open("a") as out, ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, todo))
    print("terminé" if not stop.is_set() else "interrompu", flush=True)

if __name__ == "__main__":
    main()
