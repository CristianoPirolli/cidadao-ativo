from app import db
from datetime import datetime
from flask import url_for
import os
from flask_login import UserMixin

class Report(db.Model):
    __tablename__ = "report"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="aberto")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        image_url = (
            url_for("uploaded_file", filename=os.path.basename(self.image_path), _external=True)
            if self.image_path else None
        )
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "lat": self.lat,
            "lng": self.lng,
            "image_url": image_url,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }


class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat()
        }