from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    jsonify,
    request,
    send_file,
    send_from_directory,
    session,
)
from werkzeug.utils import secure_filename

from .db import get_db
from .generator import OUTPUT_FORMATS, generate_creatives


api = Blueprint("api", __name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
OBJECTIVE = (
    "Build a web-based tool that lets a user pick a brand, select one or more dealerships, "
    "upload a background image, optionally apply logos or brand assets, and generate "
    "downloadable social creatives in bulk with consistent alignment and smart scaling."
)


def _require_login():
    if "user_id" not in session:
        return jsonify({"error": "Login required."}), 401
    return None


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api.route("/objective", methods=["GET"])
def objective():
    return jsonify({"objective": OBJECTIVE})


@api.route("/session", methods=["GET"])
def session_status():
    return jsonify(
        {
            "authenticated": "user_id" in session,
            "username": session.get("username"),
        }
    )


@api.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    db = get_db()
    user = db.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if user is None or user["password_hash"] != password:
        return jsonify({"error": "Invalid username or password."}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"authenticated": True, "username": user["username"]})


@api.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"authenticated": False})


@api.route("/accounts", methods=["GET"])
def accounts():
    auth_error = _require_login()
    if auth_error:
        return auth_error

    db = get_db()
    rows = db.execute("SELECT id, name FROM accounts ORDER BY name").fetchall()
    return jsonify([dict(row) for row in rows])


@api.route("/dealerships", methods=["GET"])
def dealerships():
    auth_error = _require_login()
    if auth_error:
        return auth_error

    account_id = request.args.get("account_id", type=int)
    db = get_db()

    if account_id:
        rows = db.execute(
            """
            SELECT id, account_id, name, panel_path, logo_light_path, logo_dark_path
            FROM dealerships
            WHERE account_id = ?
            ORDER BY name
            """,
            (account_id,),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, account_id, name, panel_path, logo_light_path, logo_dark_path
            FROM dealerships
            ORDER BY name
            """
        ).fetchall()
    return jsonify([dict(row) for row in rows])


@api.route("/asset-file/<path:asset_path>", methods=["GET"])
def asset_file(asset_path: str):
    auth_error = _require_login()
    if auth_error:
        return auth_error

    assets_dir = current_app.config["ASSETS_DIR"].resolve()
    requested_path = (assets_dir / asset_path).resolve()
    if assets_dir not in requested_path.parents and requested_path != assets_dir:
        return jsonify({"error": "Invalid asset path."}), 400
    if not requested_path.exists():
        return jsonify({"error": "Asset not found."}), 404
    return send_from_directory(assets_dir, asset_path)


@api.route("/assets/logos", methods=["GET"])
def logos():
    auth_error = _require_login()
    if auth_error:
        return auth_error

    db = get_db()
    rows = db.execute(
        "SELECT id, type, name, file_path FROM assets WHERE type = 'logo' ORDER BY name"
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@api.route("/generate", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return ("", 204)

    auth_error = _require_login()
    if auth_error:
        return auth_error

    account_id = request.form.get("account_id", type=int)
    dealership_ids = request.form.getlist("dealership_ids")
    selected_formats = request.form.getlist("formats")
    include_logo = request.form.get("include_logo", "false").lower() == "true"

    background_file = request.files.get("background")
    uploaded_logo = request.files.get("uploaded_logo")

    if not account_id:
        return jsonify({"error": "Account is required."}), 400
    if not dealership_ids:
        return jsonify({"error": "Select at least one dealership."}), 400
    if not selected_formats:
        return jsonify({"error": "Select at least one output format."}), 400
    if background_file is None or not background_file.filename:
        return jsonify({"error": "Background image is required."}), 400

    background_name = secure_filename(background_file.filename)
    background_ext = Path(background_name).suffix.lower()
    if background_ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": "Unsupported background file type."}), 400

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    background_path = upload_dir / f"{uuid4().hex}_{background_name}"
    background_file.save(background_path)

    uploaded_logo_path = None
    if uploaded_logo and uploaded_logo.filename:
        logo_name = secure_filename(uploaded_logo.filename)
        logo_ext = Path(logo_name).suffix.lower()
        if logo_ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Unsupported logo file type."}), 400
        uploaded_logo_path = upload_dir / f"{uuid4().hex}_{logo_name}"
        uploaded_logo.save(uploaded_logo_path)

    db = get_db()
    placeholders = ",".join("?" for _ in dealership_ids)
    dealership_rows = db.execute(
        f"""
        SELECT id, account_id, name, panel_path, logo_light_path, logo_dark_path
        FROM dealerships
        WHERE account_id = ? AND id IN ({placeholders})
        ORDER BY name
        """,
        [account_id, *dealership_ids],
    ).fetchall()

    dealerships = [dict(row) for row in dealership_rows]
    outputs, zip_path, job_id = generate_creatives(
        current_app.config["ASSETS_DIR"],
        current_app.config["GENERATED_FOLDER"],
        background_path,
        dealerships,
        [fmt for fmt in selected_formats if fmt in OUTPUT_FORMATS],
        include_logo,
        uploaded_logo_path,
    )

    db.execute(
        """
        INSERT INTO generation_jobs (job_id, account_id, background_path, zip_path)
        VALUES (?, ?, ?, ?)
        """,
        (
            job_id,
            account_id,
            str(background_path),
            str(zip_path),
        ),
    )

    for item in outputs:
        db.execute(
            """
            INSERT INTO generated_creatives (job_id, dealership_id, format, output_path)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, item["dealership_id"], item["format"], str(item["output_path"])),
        )
    db.commit()

    response = {
        "job_id": job_id,
        "download_zip": f"/api/downloads/{job_id}/zip",
        "creatives": [
            {
                "dealership": item["dealership_name"],
                "format": item["format"],
                "download_url": f"/api/downloads/{job_id}/file/{item['file_name']}",
                "preview_url": f"/api/previews/{job_id}/file/{item['file_name']}",
            }
            for item in outputs
        ],
    }
    return jsonify(response)


@api.route("/downloads/<job_id>/zip", methods=["GET"])
def download_zip(job_id: str):
    auth_error = _require_login()
    if auth_error:
        return auth_error

    db = get_db()
    row = db.execute("SELECT zip_path FROM generation_jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Job not found."}), 404
    return send_file(row["zip_path"], as_attachment=True)


@api.route("/downloads/<job_id>/file/<filename>", methods=["GET"])
def download_file(job_id: str, filename: str):
    auth_error = _require_login()
    if auth_error:
        return auth_error

    path = current_app.config["GENERATED_FOLDER"] / job_id / filename
    if not path.exists():
        return jsonify({"error": "File not found."}), 404
    return send_file(path, as_attachment=True)


@api.route("/previews/<job_id>/file/<filename>", methods=["GET"])
def preview_file(job_id: str, filename: str):
    auth_error = _require_login()
    if auth_error:
        return auth_error

    path = current_app.config["GENERATED_FOLDER"] / job_id / filename
    if not path.exists():
        return jsonify({"error": "File not found."}), 404
    return send_file(path)
