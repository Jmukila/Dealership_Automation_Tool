import sqlite3
from pathlib import Path

from flask import current_app, g

from .seed import seed_database


def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    schema_path = Path(current_app.root_path).parent / "database.sql"
    with schema_path.open("r", encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())
    seed_database(db, current_app.config["ASSETS_DIR"])
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)

    with app.app_context():
        current_app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
        current_app.config["GENERATED_FOLDER"].mkdir(parents=True, exist_ok=True)
        init_db()
