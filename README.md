# 🏙️ Cidadão Ativo

**Plataforma de participação cidadã para reportar problemas urbanos com geolocalização**

Sistema web desenvolvido em Flask que permite aos cidadãos reportar problemas de infraestrutura urbana (iluminação, vias, água e esgoto, limpeza, etc.) com localização GPS e fotos, e aos administradores públicos gerenciar e acompanhar a resolução dessas demandas.

---

## 📋 Índice

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [API](#api)
- [Testes](#testes)
- [Deploy](#deploy)
- [Roadmap](#roadmap)

---

## ✨ Funcionalidades

### Para Cidadãos:
- ✅ Reportar problemas urbanos via formulário web
- ✅ Geolocalização automática (GPS do navegador)
- ✅ Seleção manual de localização no mapa interativo
- ✅ Upload de fotos dos problemas
- ✅ Categorização (Iluminação, Vias, Água/Esgoto, Limpeza, Outros)
- ✅ Visualização de denúncias no mapa

### Para Administradores:
- ✅ Dashboard com mapa de todas as denúncias
- ✅ Lista de denúncias com filtros
- ✅ Atualização de status (Aberto → Em Execução → Resolvido)
- ✅ Visualização de fotos anexadas
- ✅ Sistema de autenticação seguro
- ✅ Estatísticas gerais

---

## 🛠️ Tecnologias

### Backend:
- **Flask 3.0** - Framework web Python
- **SQLAlchemy 2.0** - ORM para banco de dados
- **Flask-Login** - Gerenciamento de sessões
- **Flask-WTF** - Proteção CSRF
- **Flask-Limiter** - Rate limiting
- **PyMySQL** - Driver MySQL
- **Pillow** - Processamento de imagens

### Frontend:
- **Bootstrap 5.3** - Framework CSS
- **Leaflet 1.9** - Mapas interativos
- **OpenStreetMap** - Dados de mapas
- **Vanilla JavaScript** - Sem frameworks pesados

### Database:
- **MySQL 8.0+** - Banco de dados relacional

### Testes:
- **pytest** - Framework de testes
- **pytest-flask** - Integração Flask/pytest
- **pytest-cov** - Cobertura de código

---

## 🏗️ Arquitetura

```
cidadao-ativo/
├── app/
│   ├── __init__.py              # Application factory
│   ├── controllers/
│   │   ├── api_routes.py        # Endpoints REST API
│   │   └── view_routes.py       # Rotas de templates
│   ├── models/
│   │   └── models.py            # Modelos Report e User
│   ├── static/
│   │   ├── css/styles.css       # Estilos customizados
│   │   └── js/app.js            # JavaScript do frontend
│   ├── templates/
│   │   ├── base.html            # Template base
│   │   ├── index.html           # Página cidadã
│   │   ├── admin.html           # Dashboard admin
│   │   ├── login.html           # Login
│   │   └── register.html        # Registro
│   └── uploads/                 # Imagens enviadas
├── tests/                       # Testes automatizados
├── logs/                        # Logs da aplicação
├── config.py                    # Configurações por ambiente
├── requirements.txt             # Dependências Python
├── .env.example                 # Exemplo de variáveis de ambiente
└── run.py                       # Entry point
```

### Padrões Utilizados:
- **Application Factory Pattern** - Múltiplas instâncias do app
- **Blueprints** - Modularização de rotas
- **MVC Pattern** - Separação de responsabilidades
- **Repository Pattern** - Abstração de acesso a dados

---

## 🚀 Instalação

### Pré-requisitos:
- Python 3.8+
- MySQL 8.0+
- pip e venv

### Passo a passo:

1. **Clone o repositório:**
```bash
git clone https://github.com/seu-usuario/cidadao-ativo.git
cd cidadao-ativo
```

2. **Crie e ative um ambiente virtual:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

4. **Configure o banco de dados MySQL:**
```sql
CREATE DATABASE cidadao_ativo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cidadao_user'@'localhost' IDENTIFIED BY 'sua_senha_aqui';
GRANT ALL PRIVILEGES ON cidadao_ativo.* TO 'cidadao_user'@'localhost';
FLUSH PRIVILEGES;
```

5. **Configure as variáveis de ambiente:**
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

6. **Inicialize o banco de dados:**
```bash
flask init-db
```

7. **Crie um usuário administrador:**
```bash
flask create-admin
```

8. **Inicie o servidor:**
```bash
python run.py
```

O aplicativo estará disponível em `http://localhost:8000`

---

## ⚙️ Configuração

### Arquivo `.env`:

```env
# Flask
FLASK_ENV=development
SECRET_KEY=sua-chave-secreta-muito-segura

# Database
SQLALCHEMY_DATABASE_URI=mysql+pymysql://cidadao_user:senha@localhost:3306/cidadao_ativo

# Redis (opcional - para rate limiting em produção)
REDIS_URL=redis://localhost:6379/0
```

### Configurações por Ambiente:

O arquivo `config.py` define três ambientes:

- **Development**: Debug ativo, logs verbosos, sem rate limiting
- **Production**: Segurança máxima, HTTPS, rate limiting ativo
- **Testing**: Banco em memória, CSRF desabilitado

Para alternar entre ambientes, ajuste `FLASK_ENV` no `.env`.

---

## 📖 Uso

### Interface Cidadã:
1. Acesse `http://localhost:8000`
2. Preencha o formulário com título, descrição e categoria
3. Clique no mapa para marcar a localização (ou use geolocalização automática)
4. Anexe uma foto (opcional)
5. Envie a denúncia

### Dashboard Administrativo:
1. Acesse `http://localhost:8000/login`
2. Faça login com credenciais de admin
3. Visualize todas as denúncias no mapa
4. Clique em marcadores para ver detalhes
5. Altere status: Aberto → Em Execução → Resolvido

---

## 🔌 API

### Documentação da API REST:

#### **GET /api/reports**
Lista todas as denúncias com paginação.

**Query Parameters:**
- `page` (int): Número da página (padrão: 1)
- `per_page` (int): Itens por página (padrão: 50, max: 100)
- `status` (string): Filtrar por status (`aberto`, `em_execucao`, `resolvido`)
- `category` (string): Filtrar por categoria

**Resposta:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "Buraco na via",
      "description": "Grande buraco...",
      "category": "Vias",
      "lat": -23.55,
      "lng": -46.63,
      "status": "aberto",
      "image_url": "http://localhost:8000/uploads/foto.jpg",
      "created_at": "2025-01-15T10:30:00",
      "updated_at": "2025-01-15T10:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

#### **POST /api/reports**
Cria uma nova denúncia.

**Body (multipart/form-data):**
- `title` (string, obrigatório)
- `description` (string, obrigatório)
- `category` (string, obrigatório)
- `lat` (float, obrigatório)
- `lng` (float, obrigatório)
- `image` (file, opcional)

**Resposta:** `201 Created`

#### **GET /api/reports/:id**
Busca uma denúncia específica.

**Resposta:** `200 OK`

#### **PATCH /api/reports/:id** (Requer autenticação)
Atualiza o status de uma denúncia.

**Body (JSON):**
```json
{
  "status": "em_execucao"
}
```

**Resposta:** `200 OK`

#### **DELETE /api/reports/:id** (Requer autenticação)
Deleta uma denúncia.

**Resposta:** `200 OK`

#### **GET /api/stats**
Retorna estatísticas gerais.

**Resposta:**
```json
{
  "success": true,
  "data": {
    "total": 150,
    "by_status": {
      "aberto": 50,
      "em_execucao": 30,
      "resolvido": 70
    },
    "by_category": {
      "Iluminação": 40,
      "Vias": 60,
      "Água e Esgoto": 20,
      "Limpeza": 20,
      "Outros": 10
    }
  }
}
```

---

## 🧪 Testes

Execute os testes automatizados:

```bash
# Rodar todos os testes
pytest

# Com cobertura de código
pytest --cov=app --cov-report=html

# Rodar testes específicos
pytest tests/test_api.py
pytest tests/test_models.py

# Modo verbose
pytest -v
```

Cobertura atual: ~80% (veja `htmlcov/index.html`)

---

## 🚢 Deploy

### Deploy em Produção:

1. **Configure as variáveis de ambiente:**
```bash
export FLASK_ENV=production
export SECRET_KEY="chave-super-secreta-gerada-aleatoriamente"
export SQLALCHEMY_DATABASE_URI="mysql+pymysql://user:pass@db-server/cidadao_ativo"
```

2. **Use um servidor WSGI (Gunicorn):**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

3. **Configure HTTPS com Nginx:**
```nginx
server {
    listen 443 ssl;
    server_name cidadaoativo.com.br;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads {
        alias /path/to/cidadao-ativo/app/uploads;
    }
}
```

4. **Use Redis para rate limiting:**
```bash
export REDIS_URL=redis://localhost:6379/0
```

5. **Configure logs persistentes:**
```bash
mkdir -p logs
chmod 755 logs
```

### Docker (Opcional):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:create_app('production')"]
```

---

## 🗺️ Roadmap

### Implementações Futuras:

#### Curto Prazo:
- [ ] **Sistema de notificações** - Avisar cidadãos sobre status
- [ ] **Autenticação com título de eleitor** - Validação CPF/título
- [ ] **Comentários** - Cidadãos podem comentar em denúncias
- [ ] **Anexar múltiplas imagens** - Suporte a galeria
- [ ] **Exportação de relatórios** - CSV/PDF para gestores

#### Médio Prazo:
- [ ] **Sistema de votos** - Cidadãos podem votar em denúncias
- [ ] **Categorias customizáveis** - Admin pode criar categorias
- [ ] **Integração com APIs de órgãos públicos** - Integração automática
- [ ] **App mobile (PWA)** - Progressive Web App
- [ ] **Sistema de gamificação** - Badges e rankings

#### Longo Prazo:
- [ ] **IA para categorização automática** - Machine Learning
- [ ] **Análise de sentimento** - Priorização por urgência
- [ ] **Integração com WhatsApp** - Receber denúncias via bot
- [ ] **Dashboard analítico avançado** - BI e visualizações
- [ ] **Multi-tenancy** - Múltiplas cidades na mesma instância

---

## 🛡️ Segurança

### Recursos Implementados:
- ✅ Proteção CSRF em todos os formulários
- ✅ Rate limiting (200/dia, 50/hora)
- ✅ Hashing de senhas (Werkzeug)
- ✅ Validação de inputs
- ✅ Proteção contra SQL Injection (SQLAlchemy)
- ✅ Sessões seguras (HttpOnly, SameSite)
- ✅ Logs de atividades suspeitas

### Recomendações Adicionais:
- Use HTTPS em produção
- Configure firewall no servidor
- Monitore logs regularmente
- Faça backups automáticos do banco
- Atualize dependências regularmente

---

## 📄 Licença

Este projeto é open-source sob a licença MIT. Veja `LICENSE` para mais detalhes.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Diretrizes:
- Escreva testes para novas funcionalidades
- Mantenha cobertura de testes acima de 70%
- Siga PEP 8 (use `black` para formatação)
- Documente mudanças no README

---

## 📞 Suporte

Para dúvidas ou problemas:
- Abra uma [issue no GitHub](https://github.com/seu-usuario/cidadao-ativo/issues)
- Entre em contato: cidadaoativo@example.com

---

## 👏 Agradecimentos

- OpenStreetMap pela base de mapas
- Comunidade Flask pelo framework incrível
- Todos os contribuidores do projeto

---

**Desenvolvido com ❤️ para melhorar a participação cidadã no Brasil**
