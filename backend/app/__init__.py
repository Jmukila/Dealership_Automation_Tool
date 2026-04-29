from flask import Flask, send_from_directory

from pathlib import Path

from .db import init_app as init_db_app
from .routes import api


def create_app() -> Flask:
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="")
    app.config.from_object("app.config.Config")

    init_db_app(app)
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/")
    def serve_index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/favicon.ico")
    def favicon():
        return ("", 204)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return response

    return app
