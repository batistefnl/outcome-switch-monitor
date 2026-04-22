#!/bin/sh
# lance la démo sur http://127.0.0.1:8000
# OPENROUTER_API_KEY=... demo/run.sh pour avoir le classement en direct
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[ -x "$PY" ] || PY=python3
# normalement les données de la démo sont dans le repo, ça sert juste si on les a supprimées
if [ ! -f demo/app/data/trials.json ]; then
  "$PY" demo/build_data.py --warm
fi
exec "$PY" demo/server.py --port "${PORT:-8000}"
