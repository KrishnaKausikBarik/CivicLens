from datetime import datetime
from sqlalchemy import BigInteger
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

    id = db.Column(BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=True, default="Pending", server_default="Pending", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, server_default=db.func.current_timestamp(), nullable=True)
    user_id = db.Column(
        BigInteger().with_variant(db.Integer, "sqlite"),
        db.ForeignKey("users.id", name="fk_reports_user_id_users", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
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
            # Older database records may predate timestamps/status values. The
            # existing Supabase schema has no admin_notes or updated_at column.
            "admin_notes": None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
            "updated_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None
        }

    def __repr__(self):
        return f"<Report {self.id}: {self.title[:25]} [{self.status}]>"
