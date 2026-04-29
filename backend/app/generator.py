from __future__ import annotations

from pathlib import Path
from uuid import uuid4
import zipfile

from PIL import Image, ImageStat


OUTPUT_FORMATS = {
    "post-square": (1080, 1080),
    "post-portrait": (1080, 1350),
    "story": (1080, 1920),
}

DEFAULT_LAYOUT = {
    "logo_anchor": "top-right",
    "logo_width_ratio": 0.15,
    "top_padding_ratio": 0.04,
    "side_padding_ratio": 0.04,
    "background_focus_x": 0.5,
    "background_focus_y": 0.42,
}

DEALERSHIP_LAYOUTS = {
    "VW-Autobhan": {
        "logo_anchor": "top-right",
        "logo_width_ratio": 0.12,
        "top_padding_ratio": 0.02,
        "side_padding_ratio": 0.03,
        "background_focus_y": 0.56,
    },
    "VW-Hubli": {
        "logo_anchor": "top-left",
        "logo_width_ratio": 0.12,
        "top_padding_ratio": 0.16,
        "side_padding_ratio": 0.06,
        "background_focus_y": 0.5,
    },
    "Bellad-tata": {
        "logo_anchor": "top-left",
        "logo_width_ratio": 0.12,
        "top_padding_ratio": 0.03,
        "side_padding_ratio": 0.03,
        "story_preserve_full_background": True,
        "background_focus_y": 0.46,
    },
}


def generate_creatives(
    assets_dir: Path,
    generated_dir: Path,
    background_path: Path,
    dealerships: list[dict],
    selected_formats: list[str],
    include_logo: bool,
    uploaded_logo_path: Path | None = None,
):
    job_id = uuid4().hex
    job_dir = generated_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    background = Image.open(background_path).convert("RGBA")

    for dealership in dealerships:
        layout = _layout_for(dealership["name"])
        panel_path = assets_dir / dealership["panel_path"]
        panel = Image.open(panel_path).convert("RGBA") if panel_path.exists() else None

        logo = None
        if include_logo:
            logo = _resolve_logo(assets_dir, dealership, uploaded_logo_path, background)

        for format_key in selected_formats:
            width, height = OUTPUT_FORMATS[format_key]
            canvas = _build_canvas(background, panel, logo, width, height, layout, format_key)
            filename = f"{dealership['name']}_{format_key}.png".replace(" ", "_")
            output_path = job_dir / filename
            canvas.convert("RGB").save(output_path, quality=95)
            outputs.append(
                {
                    "job_id": job_id,
                    "dealership_id": dealership["id"],
                    "dealership_name": dealership["name"],
                    "format": format_key,
                    "file_name": filename,
                    "output_path": output_path,
                }
            )

    zip_path = job_dir / f"{job_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for item in outputs:
            zip_file.write(item["output_path"], arcname=item["file_name"])

    return outputs, zip_path, job_id


def _build_canvas(
    background: Image.Image,
    panel: Image.Image | None,
    logo: Image.Image | None,
    width: int,
    height: int,
    layout: dict,
    format_key: str,
):
    footer_ratio = _footer_ratio(panel)
    focus_x = layout.get(f"{format_key}_background_focus_x", layout["background_focus_x"])
    if layout.get(f"{format_key}_preserve_full_background", False):
        canvas = _fit_full_background(background, width, height, focus_x, layout["background_focus_y"], footer_ratio)
    else:
        canvas = _smart_cover(
            background,
            width,
            height,
            focus_x,
            layout["background_focus_y"],
            footer_ratio,
        )

    if panel:
        panel_overlay = _scale_overlay(panel, width)
        panel_y = height - panel_overlay.height
        canvas.alpha_composite(panel_overlay, (0, panel_y))

    if logo:
        placed_logo = _scale_logo(logo, width, layout["logo_width_ratio"])
        logo_x, logo_y = _logo_position(placed_logo, width, height, layout)
        canvas.alpha_composite(placed_logo, (logo_x, logo_y))

    return canvas


def _smart_cover(
    image: Image.Image,
    width: int,
    height: int,
    focus_x: float,
    focus_y: float,
    footer_ratio: float,
):
    source_ratio = image.width / image.height
    target_ratio = width / height

    if source_ratio > target_ratio:
        scale = height / image.height
    else:
        scale = width / image.width

    resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.LANCZOS)
    max_left = max(resized.width - width, 0)
    max_top = max(resized.height - height, 0)

    safe_focus_x = min(max(focus_x, 0.0), 1.0)
    left = int((resized.width * safe_focus_x) - (width * 0.5))
    left = min(max(left, 0), max_left)

    safe_focus_y = min(max(focus_y - (footer_ratio * 0.25), 0.15), 0.85)
    top = int((resized.height * safe_focus_y) - (height * 0.5))
    top = min(max(top, 0), max_top)

    return resized.crop((left, top, left + width, top + height))


def _fit_full_background(
    image: Image.Image,
    width: int,
    height: int,
    focus_x: float,
    focus_y: float,
    footer_ratio: float,
):
    scale = width / image.width
    fitted_height = int(image.height * scale)
    fitted = image.resize((width, fitted_height), Image.LANCZOS)

    canvas = Image.new("RGBA", (width, height), fitted.getpixel((width // 2, fitted_height - 1)))
    canvas.alpha_composite(fitted, (0, 0))

    remaining_height = height - fitted_height
    if remaining_height > 0:
        strip_height = min(max(fitted_height // 4, 1), fitted_height)
        bottom_strip = fitted.crop((0, fitted_height - strip_height, width, fitted_height))
        extension = bottom_strip.resize((width, remaining_height), Image.LANCZOS)
        canvas.alpha_composite(extension, (0, fitted_height))

    return canvas


def _scale_overlay(panel: Image.Image, canvas_width: int):
    scale = canvas_width / panel.width
    target_height = int(panel.height * scale)
    return panel.resize((canvas_width, target_height), Image.LANCZOS)


def _scale_logo(logo: Image.Image, canvas_width: int, width_ratio: float):
    max_width = int(canvas_width * width_ratio)
    scale = min(max_width / logo.width, 1)
    return logo.resize((int(logo.width * scale), int(logo.height * scale)), Image.LANCZOS)


def _logo_position(logo: Image.Image, canvas_width: int, canvas_height: int, layout: dict):
    pad_x = int(canvas_width * layout["side_padding_ratio"])
    pad_y = int(canvas_height * layout["top_padding_ratio"])

    if layout["logo_anchor"] == "top-left":
        return pad_x, pad_y
    return canvas_width - logo.width - pad_x, pad_y


def _footer_ratio(panel: Image.Image | None):
    if panel is None:
        return 0.0

    alpha = panel.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return 0.0

    footer_height = panel.height - bbox[1]
    return max(min(footer_height / panel.height, 0.75), 0.0)


def _layout_for(dealership_name: str):
    layout = DEFAULT_LAYOUT.copy()
    layout.update(DEALERSHIP_LAYOUTS.get(dealership_name, {}))
    return layout


def _resolve_logo(
    assets_dir: Path,
    dealership: dict,
    uploaded_logo_path: Path | None,
    background: Image.Image,
):
    if uploaded_logo_path and uploaded_logo_path.exists():
        return Image.open(uploaded_logo_path).convert("RGBA")

    brightness = ImageStat.Stat(background.convert("L").resize((1, 1))).mean[0]
    preferred_keys = ("logo_dark_path", "logo_light_path") if brightness > 165 else (
        "logo_light_path",
        "logo_dark_path",
    )

    for key in preferred_keys:
        relative_path = dealership.get(key)
        if relative_path:
            candidate = assets_dir / relative_path
            if candidate.exists():
                return Image.open(candidate).convert("RGBA")
    return None
