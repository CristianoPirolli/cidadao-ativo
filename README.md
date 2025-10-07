# Cidadão Ativo — Esboço de Plataforma

Protótipo funcional em Flask + Leaflet para reportar problemas urbanos com geolocalização e upload de imagem.

## Como rodar

```bash
python -m venv venv
source venv/bin/activate  # no Windows: venv\Scripts\activate
pip install -r requirements.txt
flask --app app.py init-db
python app.py  # abre em http://localhost:8000
```

## Endpoints

- `GET /` — formulário do cidadão, mapa e envio de chamado
- `GET /admin` — mapa com marcadores + lista com mudança de status
- `GET /api/reports` — lista chamados (JSON)
- `POST /api/reports` — cria chamado (multipart/form-data)
- `PATCH /api/reports/<id>` — altera status (`aberto|em_execucao|resolvido`)
- `GET /uploads/<filename>` — serve imagens enviadas

> Obs.: este é um esboço. Para produção, adicionar autenticação (incluindo título eleitoral), CSRF, validação, limites de taxa, e armazenamento de imagens em serviço externo (S3, etc.).