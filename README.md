# Solar Panel Defect Detection & Inspection System ☀️🔍

An AI-powered solar photovoltaic (PV) inspection platform that analyzes aerial Thermal and RGB imagery to identify, classify, and map panel-level defects and anomalies.

---

## 🚀 Features

* **Dual-Modal Image Analysis**: Supports both **Thermal (Infrared)** and **RGB (Visible Light)** drone imagery.
* **Role-Specific Inference**: Separate weight paths for panel localization, thermal defects, and RGB defects. Missing models are reported as unavailable; no predictions are simulated.
* **Panel Mapping & Numbering**:
  * Uses model detections and PCA-oriented row grouping. Panel identities are scoped to each image until image registration or geospatial evidence supports cross-image identity.
* **Evidence-Based Review**: Severity rules are independent from detection confidence; low-confidence and unmatched findings request review.
* **Analysis Jobs**: Batch uploads use a visible PENDING / PROCESSING / COMPLETED / FAILED lifecycle.

---

## 🛠️ Tech Stack

### Frontend
* **Framework**: React 18 with Vite
* **Icons**: Lucide Icons
* **Styling**: Modern responsive CSS with custom dark/light theme support
* **HTTP Client**: Native Fetch / Axios

### Backend
* **Framework**: FastAPI (Python 3.10+)
* **Database**: MongoDB (via PyMongo)
* **Computer Vision**: OpenCV, Ultralytics YOLOv8, Pillow
* **Server**: Uvicorn ASGI

---

## 📂 Project Structure

```text
solar/
├── backend/                  # FastAPI Application
│   ├── database.py           # MongoDB connection & collections
│   ├── detector.py           # Compatibility facade for vision services
│   ├── main.py               # Projects, validated uploads, analysis jobs, findings and reports
│   ├── vision/               # Model registry, inference, mapping, registration and risk
│   ├── requirements.txt      # Python dependencies
│   ├── start.bat             # Windows startup script
│   └── .env.example          # Sample environment configuration
├── src/                      # React Frontend Source
│   ├── assets/               # Branding and illustrations
│   ├── components/           # Reusable UI components (Sidebar, BrandLogo)
│   ├── pages/                # Main application views (Dashboard, Mapping, Reports)
│   │   └── workflow/         # Step-by-step inspection wizard
│   ├── utils/                # Frontend helper utilities
│   ├── App.jsx               # Main React entry & routing
│   └── main.jsx
├── public/                   # Static assets & favicons
├── package.json              # Frontend scripts & dependencies
├── vite.config.js            # Vite configuration
└── README.md
```

---

## ⚡ Getting Started

### Prerequisites
* **Node.js** (v18 or higher)
* **Python** (v3.10 or higher)
* **MongoDB** (running locally on port `27017` or MongoDB Atlas URI)

---

### 1. Backend Setup

1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   Copy `.env.example` to `.env` and adjust if necessary:
   ```env
   MONGO_URI=mongodb://localhost:27017
   DB_NAME=solar_inspect
   UPLOAD_DIR=uploads
   ```

5. Start the backend server:
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   The backend API will be available at `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup

1. From the project root directory, install npm packages:
   ```bash
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:5173`.

---

## 🧠 Model Configuration

Set independent model paths with `PANEL_MODEL_PATH`, `THERMAL_MODEL_PATH`, and `RGB_MODEL_PATH`. Defaults are `backend/models/panel_detection.pt`, `thermal_defects.pt`, and `rgb_defects.pt`. Each checkpoint can have a sibling JSON manifest. The deployment manifest schema and model registry behavior are described in [backend/vision/README.md](backend/vision/README.md). Model files are ignored by Git and should be distributed through Git LFS or an artifact store.

The repository currently contains no model weights or labeled evaluation set. The API therefore returns `MODEL_UNAVAILABLE` until role-appropriate weights are configured. No model accuracy is claimed. Use `python backend/scripts/validate_models.py` to validate manifests/checksums and optionally run actual smoke-test images (`--image ROLE=PATH`). Evaluation requires images, YOLO labels, a dataset manifest declaring `validation` or `test`, and actual role-specific weights:

```bash
python backend/scripts/evaluate_models.py --model-role thermal_defect_detection \
  --images-dir data/validation/images --labels-dir data/validation/labels \
  --dataset-manifest data/validation/dataset.json --split validation \
  --require-site-holdout --output reports/thermal-validation.json
```

The evaluator writes JSON and Markdown reports with detection metrics, per-class results, error lists, and latency. Segmentation IoU/Dice is emitted only when polygon ground truth and predicted masks exist. Memory usage is reported as unavailable when it cannot be measured safely. See [backend/evaluation/README.md](backend/evaluation/README.md) for annotation format and limitations.

RGB/thermal registration is an explicit feature-matching request and reports `UNREGISTERED` when matches do not pass quality checks. Reports distinguish suspected observations and inspection priority from validated severity; thermal pixel values are not treated as calibrated temperatures. The report displays image-level observations and does not claim unique physical panel totals across overlapping images.

## Authentication and deployment boundary

The API uses configurable OIDC/JWKS bearer-token validation. In production, set `AUTH_ENABLED=true`, `AUTH_ISSUER`, `AUTH_AUDIENCE`, and an HTTPS `AUTH_JWKS_URL`; the provider must issue short-lived asymmetric-signed JWT access tokens. Tokens must include `sub`, `exp`, `iss`, and `aud`. Projects are owned by the creating subject, with optional project membership IDs and an administrator role configured by claim names in `.env.example`. Existing projects without `ownerSubject` require an administrator or a trusted `project_ids` claim until they are migrated. `/api/health` remains public for liveness. Uploaded image bytes are served only through project-authorized API routes.

The web host must complete its chosen OIDC login/refresh flow and pass the short-lived access token to `setAccessToken()` in `src/api.js`; this repository does not select an identity provider or implement a login screen. `AUTH_ENABLED=false` is a local development bypass that grants development-admin access and must not be used in production. Apply rate limits at the API gateway/reverse proxy as well as the configured upload size and image-count limits. No authentication or rate-limiting behavior should be considered deployed until provider configuration and ingress policy are verified.

Run backend checks with `python -m pytest backend/tests -q`; frontend checks are `npm run lint` and `npm run build`. Production deployment requires persistent MongoDB; the in-memory fallback is explicitly for development/testing.

---

## 📄 License
This project is developed for academic and solar inspection research purposes.
