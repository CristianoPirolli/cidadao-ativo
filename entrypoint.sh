#!/bin/bash
set -e

echo "Aguardando PostgreSQL ficar pronto..."
until python -c "
import psycopg, os, sys
try:
    psycopg.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=int(os.environ.get('DB_PORT', 5432)),
        dbname=os.environ.get('DB_NAME', 'cidadao_ativo'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'postgres'),
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  echo "  PostgreSQL ainda não está pronto, aguardando..."
  sleep 2
done
echo "PostgreSQL pronto!"

echo "Executando migrações..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Iniciando servidor Gunicorn..."
exec gunicorn \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  "project.wsgi:application"
