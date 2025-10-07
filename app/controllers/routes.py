from flask import render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app import app, db
from app.models.models import Report

# --- Routes (Web) ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

# --- Routes (API) ---
@app.route("/api/reports", methods=["GET"])
def list_reports():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reports])

@app.route("/api/reports", methods=["POST"])
def create_report():
    # Accept multipart/form-data for image uploads
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip() or "outros"
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    image = request.files.get("image")

    # Basic validation
    errors = []
    if not title: errors.append("Título é obrigatório.")
    if not description: errors.append("Descrição é obrigatória.")
    try:
        lat = float(lat); lng = float(lng)
    except Exception:
        errors.append("Localização inválida.")

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    image_path = None
    if image and image.filename:
        filename = secure_filename(image.filename)
        # Avoid collisions by prefixing id-like timestamp
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