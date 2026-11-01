from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Initialize SQLAlchemy and verify PostgreSQL without modifying the schema."""
    db.init_app(app)
    with app.app_context():
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
