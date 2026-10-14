# Solar Panel Defect Detection & Inspection System ☀️🔍

An AI-powered solar photovoltaic (PV) inspection platform that analyzes aerial Thermal and RGB imagery to identify, classify, and map panel-level defects and anomalies.

---

## 🚀 Features

* **Dual-Modal Image Analysis**: Supports both **Thermal (Infrared)** and **RGB (Visible Light)** drone imagery.
* **Automated Defect Detection**:
  * **Thermal Faults**: Hotspots, Loose Electrical Connections, Reverse Bias Cells, Bypass Diode Failures, Cell Mismatches, Open Circuits.
  * **RGB Physical Anomalies**: Cracked Glass, Broken Frames, Delamination, Dust Accumulation, Bird Droppings, Mud, Snow, Vegetation Shading.
* **Panel Mapping & Numbering**:
  * Uses computer vision / YOLO object detection to locate individual solar panels.
  * Groups panels into rows by geometric proximity and assigns sequential IDs for precise field remediation.
* **Severity Classification**: Automatically ranks defects by risk (*High*, *Medium*, *Low*).
* **Comprehensive Project Dashboard**: Create inspection projects, upload image batches, review interactive bounding boxes, and export audit reports.

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
│   ├── detector.py           # Defect simulation & YOLO panel detection
│   ├── main.py               # API endpoints (Projects, Upload, Analyze, Reports)
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

## 🧠 Model & Detection Pipeline

* **Model Architecture**: Ultralytics YOLOv8 for solar panel localization and defect bounding box regression.
* **Inference Pipeline**:
  1. Image upload (Thermal / RGB).
  2. Bounding box detection with center coordinate extraction (`cx = (x1 + x2) / 2`, `cy = (y1 + y2) / 2`).
  3. Row clustering based on vertical proximity.
  4. Left-to-right sorting within rows and sequential panel numbering.
  5. Severity mapping and report generation stored in MongoDB.

---

## 📄 License
This project is developed for academic and solar inspection research purposes.
