from flask import render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from datetime import datetime
import os
from app import app, db
from app.models.models import Report, User

# --- Rotas Web ---
@app.route("/")
def index():
    return render_template("index.html")

# Tela de Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("admin"))
        else:
            flash("Credenciais inválidas. Tente novamente.", "danger")

    return render_template("login.html")

# Tela de Registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        errors = []
        if not username:
            errors.append("Nome de usuário é obrigatório.")
        if not email:
            errors.append("E-mail é obrigatório.")
        if not password:
            errors.append("Senha é obrigatória.")

        if User.query.filter_by(email=email).first():
            errors.append("E-mail já está em uso.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("register"))

        # Cria e salva o novo usuário
        hashed = generate_password_hash(password)
        new_user = User(name=username, email=email, password_hash=hashed)
        db.session.add(new_user)
        db.session.commit()

        flash("Cadastro realizado com sucesso! Faça login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Logout
@app.route("/logout")
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("login"))

# Painel administrativo
@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html")

# --- Rotas API ---
@app.route("/api/reports", methods=["GET"])
def list_reports():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports])

@app.route("/api/reports", methods=["POST"])
def create_report():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip() or "outros"
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    image = request.files.get("image")

    errors = []
    if not title:
        errors.append("Título é obrigatório.")
    if not description:
        errors.append("Descrição é obrigatória.")
    try:
        lat = float(lat)
        lng = float(lng)
    except Exception:
        errors.append("Localização inválida.")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    image_path = None
    if image and image.filename:
        filename = secure_filename(image.filename)
        filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    report = Report(
        title=title,
        description=description,
        category=category,
        lat=lat,
        lng=lng,
        image_path=image_path
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({"ok": True, "report": report.to_dict()}), 201

@app.route("/api/reports/<int:report_id>", methods=["PATCH"])
def update_report(report_id):
    report = Report.query.get_or_404(report_id)
    status = request.json.get("status")
    if status in {"aberto", "em_execucao", "resolvido"}:
        report.status = status
        db.session.commit()
        return jsonify(report.to_dict())
    return jsonify({"error": "Status inválido"}), 400

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
