from datetime import datetime
from database import db

class Report(db.Model):
    __tablename__ = "reports"

    VALID_CATEGORIES = [
        "Roads & Footpaths",
        "Water Supply",
        "Electricity",
        "Garbage & Waste",
        "Drainage & Sewage",
        "Public Wi-Fi",
        "Other"
    ]

    VALID_STATUSES = [
        "Pending",
        "In Progress",
        "Resolved"
    ]

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Pending", index=True)
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", name="fk_reports_user_id_users", ondelete="SET NULL"), nullable=True, index=True)
    user = db.relationship("User", back_populates="reports")

    def to_dict(self):
        """Serialize complaint entity to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "latitude": round(float(self.latitude), 6),
            "longitude": round(float(self.longitude), 6),
            "status": self.status,
            "admin_notes": self.admin_notes,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M")
        }

    def __repr__(self):
        return f"<Report {self.id}: {self.title[:25]} [{self.status}]>"
