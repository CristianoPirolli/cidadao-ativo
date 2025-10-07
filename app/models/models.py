from app import db
from datetime import datetime
from flask import url_for
import os

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
