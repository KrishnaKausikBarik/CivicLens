from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.func.current_timestamp())
    reports = db.relationship("Report", back_populates="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
