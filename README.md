# Dealership Creative Automation Tool

Designed as a lightweight creative automation tool inspired by Canva-style workflows for dealership marketing teams.

## Project Overview

This web-based tool allows users to select a brand, dynamically load mapped dealerships, choose one or more dealerships, upload a background image, optionally apply logos, preview the creative, and generate social media creatives in bulk with smart scaling, automatic panel placement, logo alignment, and ZIP download support.

## Tech Stack

- Backend: Flask (Python)
- Database: SQLite
- Image Processing: Pillow
- Frontend: HTML, CSS, JavaScript

## Application Flow

### 1. App Initialization

- Flask app starts from `backend/app.py`
- SQLite database is initialized from `backend/database.sql`
- Brand, dealership, panel, and logo data are seeded from the `assets/` folder
- Frontend is served from the Flask root route

### 2. User Workflow

- Select brand/account
- Dealerships load dynamically based on selected brand
- Select one or multiple dealerships using checkboxes
- Upload a JPG/PNG background image
- Optionally enable/upload logo
- Choose output formats
- Preview creative on canvas
- Generate creatives

### 3. Creative Generation Pipeline

- Smart background scaling fills the target size without distortion
- Dealership panel is scaled and anchored to the bottom
- Logo is auto-scaled and aligned using layout rules
- Light/dark dealership logo is selected based on background brightness
- Bulk creatives are generated across selected dealerships and formats

### 4. Output

- Live canvas preview before generation
- Thumbnail grid after generation
- Individual image downloads
- ZIP download for the complete batch

## Intelligent Automation Implemented

- Smart background cover scaling while maintaining aspect ratio
- Automatic dealership panel scaling and bottom anchoring
- Automatic logo scaling and alignment
- Brightness-based logo selection for light/dark backgrounds

## Database Design

SQLite database file:

```text
backend/app.db
```

SQL dump:

```text
backend/database.sql
```

Tables:

- `users`
- `accounts`
- `dealerships`
- `assets`
- `generation_jobs`
- `generated_creatives`

## API Summary

- `GET /api/health`
- `GET /api/accounts`
- `GET /api/dealerships?account_id=<id>`
- `GET /api/assets/logos`
- `GET /api/asset-file/<asset_path>`
- `POST /api/generate`
- `GET /api/previews/<job_id>/file/<filename>`
- `GET /api/downloads/<job_id>/file/<filename>`
- `GET /api/downloads/<job_id>/zip`

## Screenshots / Sample Outputs

Generated output examples are available in:

```text
assets/Expected-output-examples/
```

Sample input images are available in:

```text
assets/Sample-input-images/
```

## Setup Instructions

1. Create and activate a Python virtual environment.

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the backend:

```bash
cd backend
python app.py
```

4. Open the application:

```text
http://127.0.0.1:5000/
```

## Default Admin Login

- Username: `admin`
- Password: `admin123`

Note: Admin credentials are included in the database as required. A full admin login UI is listed as a future improvement.

## Output Formats

- Instagram Post: `1080x1080`
- Instagram Post Portrait: `1080x1350`
- Instagram Story: `1080x1920`

## File Storage

- Uploaded files: `backend/uploads/`
- Generated creatives: `backend/generated/<job_id>/`
- ZIP files: `backend/generated/<job_id>/<job_id>.zip`

## Limitations / Future Improvements

- Admin login UI is not implemented yet, although DB support exists
- Predefined logo selection can be extended in the frontend UI
- Bulk generation is currently processed sequentially
- Job history/regenerate page can be added for admin/debug workflows
- Additional template styles can be added, such as side panel or minimal overlay layouts

## Final Submission Checklist

- `database.sql` included for database setup
- `README.md` includes setup instructions and default admin credentials
- `requirements.txt` included for Python dependencies
- Bulk creative generation supported
- ZIP download supported
- Intelligent automation clearly implemented and documented
