#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
python - <<'PY'
import os, time, socket
host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
for i in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("PostgreSQL is up.")
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("PostgreSQL did not become available in time.")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

# Dev server (simple). You can replace with gunicorn if desired.
python manage.py runserver 0.0.0.0:8000
