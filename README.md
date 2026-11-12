# Cidadão Ativo

**Plataforma de participação cidadã para registrar e acompanhar problemas urbanos com geolocalização.**

Cidadãos abrem chamados (iluminação, vias, água e esgoto, limpeza…) com foto e localização GPS; o órgão público do município recebe, atualiza o status e responde; a comunidade prioriza os chamados com votos de urgência e participa da ouvidoria municipal.

Projeto desenvolvido no PRATIC IV — UNOESC. Os materiais acadêmicos estão em [`docs/pratic-iv`](docs/pratic-iv).

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Stack](#stack)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Executando com Docker](#executando-com-docker)
- [Desenvolvimento local](#desenvolvimento-local)
- [Testes e qualidade](#testes-e-qualidade)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [API](#api)
- [Perfis de usuário](#perfis-de-usuário)
- [Segurança](#segurança)

---

## Funcionalidades

**Cidadão**
- Cadastro com CPF e comprovante de residência (aprovado pelo órgão do seu município)
- Abertura de chamados com foto, categoria e localização (GPS ou clique no mapa)
- Detecção automática do município pela coordenada (geocodificação reversa + IBGE)
- Voto de urgência em chamados próximos (até 200 m, configurável)
- Ouvidoria municipal

**Órgão público (prefeitura)**
- Painel com mapa, mapa de calor e regiões com mais ocorrências
- Atualização de status, comentários e histórico completo do chamado
- Métricas de tempo de resolução
- Aprovação ou rejeição de cadastros de cidadãos do município

**Administrador / dono da plataforma (SaaS)**
- Aprovação de órgãos, gestão de usuários e de administradores
- Moderação da ouvidoria
- Estatísticas gerais da plataforma

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, Django 5.2 |
| Banco de dados | PostgreSQL 16 (driver psycopg 3) |
| Frontend | Templates Django, Bootstrap 5, Leaflet (OpenStreetMap) |
| Servidor | Gunicorn + Nginx, WhiteNoise para estáticos |
| Infra | Docker / Docker Compose |
| Qualidade | pytest + pytest-django, Ruff, GitHub Actions |

## Estrutura do projeto

```
cidadao-ativo/
├── backend/                     # Aplicação Django
│   ├── config/                  # Projeto Django
│   │   ├── settings/
│   │   │   ├── base.py          # Configurações comuns
│   │   │   ├── development.py   # Desenvolvimento local
│   │   │   ├── production.py    # Produção (Docker)
│   │   │   └── test.py          # Suíte de testes
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── core/                # Páginas públicas, healthcheck, validações (CPF, CNPJ, arquivos), e-mail
│   │   ├── accounts/            # Usuário customizado, login, cadastro, aprovações
│   │   ├── reports/             # Chamados, histórico, votos de urgência, API
│   │   ├── ouvidoria/           # Mural de mensagens por município
│   │   ├── dashboards/          # Painéis por perfil
│   │   └── locations/           # Municípios (IBGE) e geocodificação
│   ├── requirements/
│   │   ├── base.txt             # Produção
│   │   └── dev.txt              # Testes e lint
│   ├── conftest.py
│   ├── pyproject.toml           # pytest, Ruff, coverage
│   └── manage.py
├── frontend/
│   ├── templates/               # Templates organizados por app
│   └── static/                  # CSS e JavaScript
├── docker/
│   ├── backend/                 # Dockerfile e entrypoint
│   └── nginx/                   # Configuração do proxy reverso
├── docs/pratic-iv/              # Relatório, diagnóstico e apresentação
├── docker-compose.yml           # Stack completa (db + backend + nginx)
├── docker-compose.dev.yml       # Sobrescrita para desenvolvimento
└── .env.example
```

Cada app segue a mesma organização: `models.py`, `views.py`, `urls.py`, `admin.py`, `services/` (regras de negócio, sem dependência de request) e `tests/`.

## Executando com Docker

Pré-requisito: Docker com o plugin Compose.

```bash
cp .env.example .env
# edite .env: defina DJANGO_SECRET_KEY e POSTGRES_PASSWORD

docker compose up -d --build
```

Acesse **http://localhost:8000**. As migrações e o `collectstatic` rodam automaticamente na subida do container.

Criar o primeiro administrador:

```bash
docker compose exec backend python manage.py createsuperuser
```

Para gerar uma `DJANGO_SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Comandos úteis:

```bash
docker compose logs -f backend         # logs da aplicação
docker compose exec db psql -U cidadao_ativo cidadao_ativo
docker compose down                    # para os containers (mantém os dados)
docker compose down -v                 # para e apaga os volumes (banco e uploads)
```

**Modo desenvolvimento no Docker** (código montado como volume, recarga automática, Postgres exposto na porta 5432):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# runserver em http://localhost:8001
```

## Desenvolvimento local

Pré-requisitos: Python 3.12+ e PostgreSQL 16 (local ou via Docker).

```bash
# 1. Banco de dados (se não tiver Postgres instalado)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db   # expõe a porta 5432

# 2. Ambiente Python
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt

# 3. Configuração
cp ../.env.example ../.env         # ajuste POSTGRES_* se necessário

# 4. Banco e servidor
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Por padrão o `manage.py` usa `config.settings.development` (DEBUG ligado, e-mails no console, uploads servidos pelo Django).

## Testes e qualidade

Os testes rodam contra PostgreSQL (o pytest-django cria o banco `test_cidadao_ativo` automaticamente).

```bash
cd backend
pytest                    # suíte completa
pytest --cov              # com cobertura
ruff check .              # lint
python manage.py makemigrations --check --dry-run
```

O workflow em `.github/workflows/ci.yml` executa lint, verificação de migrações, testes e o build da imagem Docker a cada push e pull request.

## Variáveis de ambiente

Todas estão documentadas em [`.env.example`](.env.example). As principais:

| Variável | Descrição |
|---|---|
| `DJANGO_SECRET_KEY` | Chave secreta (obrigatória em produção) |
| `DJANGO_DEBUG` | `true` apenas em desenvolvimento |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origens confiáveis para CSRF (com esquema) |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Conexão com o PostgreSQL (as mesmas variáveis configuram o container do banco) |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`… | SMTP para e-mails de aprovação |
| `PLATFORM_OWNER_EMAIL` | E-mail do dono da plataforma (acesso ao painel SaaS) |
| `URGENCY_VOTE_MAX_DISTANCE_METERS` | Distância máxima para votar urgência |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_COOKIES` | Ative quando estiver atrás de HTTPS |

## API

Todas as rotas retornam JSON no formato `{"success": bool, "data": ..., "error": ...}`. Rotas que alteram dados exigem sessão autenticada e o token CSRF no cabeçalho `X-CSRFToken` (disponível na meta tag `csrf-token` das páginas).

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/reports` | autenticado | Lista paginada (`page`, `per_page`, `status`, `category`), ordenada por votos de urgência |
| POST | `/api/reports/create` | autenticado | Cria chamado (multipart: `title`, `description`, `category`, `lat`, `lng`, `image`, `municipio_*`) |
| GET | `/api/reports/<id>` | autenticado | Detalhe do chamado |
| POST | `/api/reports/<id>/update` | órgão / admin | Altera status (`{"status": "...", "comment": "..."}`) |
| POST | `/api/reports/<id>/comment` | órgão | Adiciona comentário |
| POST | `/api/reports/<id>/vote` | cidadão | Voto de urgência (`{"lat": ..., "lng": ...}`) |
| GET | `/api/reports/<id>/history` | autenticado | Histórico do chamado |
| POST/DELETE | `/api/reports/<id>/delete` | admin | Remove chamado |
| GET | `/api/stats` | público | Totais por status e categoria |
| GET | `/api/municipios?q=&uf=` | público | Busca de municípios (IBGE) |
| GET | `/api/municipios/com-orgaos` | público | Municípios com órgão cadastrado |
| POST | `/api/geocode` | público (CSRF) | Município a partir de `lat`/`lng` |
| GET | `/health` | público | Healthcheck da aplicação e do banco |

Status de chamado: `aberto`, `visualizado`, `em_andamento` (alias `em_execucao`), `resolvido`, `rejeitado`.
Categorias: `iluminacao`, `via_publica`, `agua_esgoto`, `limpeza`, `outros`.

## Perfis de usuário

| Perfil | Como é criado | Quem aprova |
|---|---|---|
| Cidadão | Cadastro público com CPF e comprovante | Órgão do município |
| Órgão | Cadastro público com CNPJ | Administrador |
| Administrador | `createsuperuser` ou promoção pelo dono | — |
| Dono da plataforma | Usuário cujo e-mail é `PLATFORM_OWNER_EMAIL` | — |

O Django Admin fica em `/django-admin/`.

## Segurança

- Senhas com hash do Django (PBKDF2) e validadores de senha
- Proteção CSRF em todos os formulários e chamadas da API
- Ações que alteram dados aceitam apenas `POST`
- Limite de tentativas de login e cadastro por IP (django-ratelimit)
- Proteção contra *open redirect* no parâmetro `next` do login
- Comprovantes de residência nunca são servidos publicamente (bloqueados no Nginx; acesso somente pela view autenticada, restrita ao órgão do município)
- Validação de imagens/documentos (extensão, MIME, tamanho e conteúdo via Pillow) e nomes de arquivo gerados com UUID
- Container executando com usuário sem privilégios; `SECRET_KEY` obrigatória em produção
