from pathlib import Path


BRAND_FOLDER_MAP = {
    "Volkswagen": "VW-dealers",
    "Tata": "Tata-dealers",
}


def seed_database(db, assets_dir: Path):
    has_accounts = db.execute("SELECT COUNT(*) AS count FROM accounts").fetchone()["count"]
    if has_accounts:
        return

    for account_name, folder_name in BRAND_FOLDER_MAP.items():
        cursor = db.execute(
            "INSERT INTO accounts (name) VALUES (?)",
            (account_name,),
        )
        account_id = cursor.lastrowid
        dealers_dir = assets_dir / "Dealership-panels" / folder_name
        if not dealers_dir.exists():
            continue

        for dealer_dir in sorted(path for path in dealers_dir.iterdir() if path.is_dir()):
            template_path = _pick_first_existing(dealer_dir, ["template.png", "template1.png"])
            logo_light = _pick_first_existing(dealer_dir, ["logo-light.png"])
            logo_dark = _pick_first_existing(dealer_dir, ["logo-dark.png"])

            db.execute(
                """
                INSERT INTO dealerships (
                    account_id, name, panel_path, logo_light_path, logo_dark_path
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    dealer_dir.name,
                    _relative_or_empty(template_path, assets_dir),
                    _relative_or_empty(logo_light, assets_dir),
                    _relative_or_empty(logo_dark, assets_dir),
                ),
            )

    for logo_path in sorted((assets_dir / "Logos").glob("*")):
        if logo_path.is_file():
            db.execute(
                "INSERT INTO assets (type, name, file_path) VALUES (?, ?, ?)",
                ("logo", logo_path.stem, _relative_or_empty(logo_path, assets_dir)),
            )


def _pick_first_existing(folder: Path, names):
    for name in names:
        candidate = folder / name
        if candidate.exists():
            return candidate
    return None


def _relative_or_empty(path: Path | None, base_dir: Path) -> str:
    if path is None:
        return ""
    return str(path.relative_to(base_dir)).replace("\\", "/")
