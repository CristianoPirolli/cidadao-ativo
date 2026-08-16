FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema para psycopg3 (libpq)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários e tornar entrypoint executável
RUN mkdir -p app/uploads/residence_proofs staticfiles && \
    chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
