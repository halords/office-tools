# Offline Toolbox

A high-performance, privacy-first, 100% offline desktop application for manipulating PDFs and images without sending files to the cloud.

---

## 🌟 Key Features

* **🛡️ 100% Offline & Private:** Zero internet connection required. Files never leave your local storage.
* **📄 PDF Workspace:**
  * Interactive page viewing, smooth zooming, and panning.
  * Reorder, duplicate, delete, and rotate pages (0°, 90°, 180°, 270°) without quality-degrading rasterization.
  * Merge multiple PDF documents into one unified file while preserving bookmarks.
  * Split PDFs by custom page ranges.
  * PDF stream compression and optimization.
* **🖼️ Image Workspace:**
  * High-speed batch format conversion: **JPEG, PNG, WebP, BMP, TIFF, and multi-resolution ICO**.
  * Multi-resolution ICO generation (16×16 to 256×256) for icons and favicons.
  * RGBA/LA alpha transparency flattening to configurable matte backgrounds.
  * Aspect-ratio preserving resizing, cropping, and rotation.
  * One-click conversion from image collections to standardized PDFs (A4, Letter, auto-fit).
  * PDF to image rasterization with customizable DPI.
  * Automatic EXIF / camera metadata stripping for privacy.
* **💾 Data Integrity & Safety:**
  * Non-destructive file output by default (never overwrites original documents).
  * Atomic file writes and automatic temporary cleanup.
  * Post-operation verification check (validates readable xrefs and pages before confirming).

---

## 🚀 Quickstart

### 1. Requirements
* Python 3.11 or 3.12 (64-bit)

### 2. Installation
```powershell
pip install -e .
```

### 3. Run Application
```powershell
python -m offline_toolbox
```

---

## 🧪 Testing

Run the automated test suite with:
```powershell
pytest -v tests/
```
