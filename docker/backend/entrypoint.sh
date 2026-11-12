#!/bin/sh
set -e

echo "Aguardando o PostgreSQL em ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os
import sys
import time

import psycopg

params = dict(
    host=os.environ.get('POSTGRES_HOST', 'db'),
    port=int(os.environ.get('POSTGRES_PORT', 5432)),
    dbname=os.environ.get('POSTGRES_DB', 'cidadao_ativo'),
    user=os.environ.get('POSTGRES_USER', 'cidadao_ativo'),
    password=os.environ.get('POSTGRES_PASSWORD', ''),
    connect_timeout=3,
)
for attempt in range(1, 31):
    try:
        psycopg.connect(**params).close()
        print('PostgreSQL pronto.')
        sys.exit(0)
    except psycopg.OperationalError:
        print(f'  tentativa {attempt}/30: banco ainda indisponível...')
        time.sleep(2)
print('PostgreSQL não respondeu a tempo.', file=sys.stderr)
sys.exit(1)
PY

if [ "${DJANGO_MIGRATE:-true}" = "true" ]; then
  echo "Aplicando migrações..."
  python manage.py migrate --noinput
fi

if [ "${DJANGO_COLLECTSTATIC:-true}" = "true" ]; then
  echo "Coletando arquivos estáticos..."
  python manage.py collectstatic --noinput
fi

exec "$@"
