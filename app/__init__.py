from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

db = SQLAlchemy(app)

# ⚠️ Importa o modelo antes de criar as tabelas
from app.models.models import Report

@app.cli.command("init-db")
def init_db():
    """Cria as tabelas do banco MySQL."""
    db.create_all()
    print("Banco inicializado com sucesso.")

# Importa rotas para registrar endpoints
from app.controllers import routes
