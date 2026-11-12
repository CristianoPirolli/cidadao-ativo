# syntax=docker/dockerfile:1

# ─── Etapa 1: instala as dependências em um virtualenv isolado ────────────
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements/ /tmp/requirements/
RUN pip install -r /tmp/requirements/base.txt


# ─── Etapa 2: imagem final enxuta, executando como usuário sem privilégios ─
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_STATIC_ROOT=/vol/static \
    DJANGO_MEDIA_ROOT=/vol/media \
    DJANGO_DATA_DIR=/vol/data \
    FRONTEND_DIR=/app/frontend

RUN groupadd --system app && useradd --system --gid app --home /app app \
    && mkdir -p /vol/static /vol/media/residence_proofs /vol/data \
    && chown -R app:app /vol

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app/backend
COPY --chown=app:app backend/ /app/backend/
COPY --chown=app:app frontend/ /app/frontend/
COPY --chown=app:app docker/backend/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
