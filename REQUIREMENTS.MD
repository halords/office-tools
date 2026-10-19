# Offline Toolbox

## Architecture & Requirements Specification

**Version:** 1.0
**Status:** Planning / Architecture
**Target:** Desktop application
**Primary platform:** Windows
**Secondary targets:** Linux, macOS
**Architecture:** Offline-first, modular desktop application
**Primary language:** Python

---

# 1. Product Vision

Offline Toolbox is a privacy-first desktop application for working with PDFs, images, and related document formats without requiring an internet connection.

The application should replace the need for repeatedly visiting online utilities for common tasks such as:

* PDF merging
* PDF splitting
* PDF page extraction
* PDF rotation
* PDF reordering
* PDF conversion
* PDF compression
* Image conversion
* Image resizing
* Image compression
* Image-to-PDF conversion
* PDF-to-image conversion
* OCR
* Annotation
* Signing
* Basic PDF editing
* Metadata management
* Batch processing

The core product principle is:

> **Files stay on the user's computer unless the user explicitly chooses otherwise.**

The application should continue functioning with Wi-Fi and network connectivity completely disabled.

---

# 2. Product Goals

## 2.1 Primary Goals

1. Provide a simple alternative to online PDF/image tools.
2. Keep all processing local.
3. Support batch operations.
4. Provide a fast and intuitive desktop UI.
5. Preserve original files by default.
6. Preserve PDF quality and structure wherever technically possible.
7. Provide useful PDF editing without pretending to fully replicate Adobe Acrobat.
8. Support drag-and-drop workflows.
9. Provide clear error messages.
10. Make common operations require as few clicks as possible.

---

# 3. Non-Goals

The application will NOT initially attempt to perfectly replicate Adobe Acrobat.

Specifically, the first versions should not promise:

* Perfect editing of arbitrary PDF text
* Perfect reconstruction of complex PDF layouts
* Full enterprise document-management functionality
* Cloud collaboration
* Browser-based editing
* Online file sharing
* Adobe-specific proprietary functionality

Advanced PDF editing should only modify content when it can be done safely.

---

# 4. Core Design Principles

## 4.1 Offline First

All normal functionality must work without network connectivity.

The application must not require:

* Cloud APIs
* Online conversion services
* Remote OCR
* Remote storage
* Online authentication
* Telemetry services

Optional update checking may exist later, but must be disabled by default or clearly controlled by the user.

---

## 4.2 Privacy First

User files must never be uploaded automatically.

The application should:

* Process files locally
* Avoid unnecessary temporary copies
* Clean temporary files
* Avoid storing file contents in application logs
* Avoid sending filenames to external services
* Provide a privacy status indicator

Suggested UI:

> 🟢 Offline — Files are processed locally

---

## 4.3 Preserve Originals

Operations should default to creating a new file.

Example:

```text
report.pdf
```

becomes:

```text
report_compressed.pdf
```

rather than overwriting the original.

The user may explicitly choose "Replace original" if desired.

---

## 4.4 Progressive Complexity

Simple tasks should remain simple.

The UI should expose advanced options only when needed.

Example:

```text
Convert Image

Input:
photo.png

Convert to:
[JPEG ▼]

Quality:
[90]

[ Convert ]
```

Advanced settings can be expandable:

```text
Advanced
  DPI
  Color profile
  Metadata
  Background
  Chroma subsampling
```

---

# 5. Target Users

## Primary

* Students
* Office workers
* Developers
* Researchers
* Photographers
* Administrative workers
* Freelancers
* Small businesses
* Privacy-conscious users
* Users with unreliable internet

## Secondary

* IT technicians
* Government/enterprise environments
* Offline workstations
* Portable/USB workflows

---

# 6. Supported Platforms

## Phase 1

Windows 10/11, 64-bit.

## Phase 2

Linux.

## Phase 3

macOS.

Architecture should avoid unnecessary platform-specific code.

---

# 7. Technology Stack

## 7.1 Core Language

Python 3.11 – 3.12 (64-bit).

* Python 3.11+ provides substantial performance enhancements.
* Pinning to 3.11/3.12 guarantees broad compatibility across PySide6, PyMuPDF, and PyInstaller / Nuitka packaging toolchains.

---

# 8. GUI Framework

## PySide6

PySide6 should be the primary GUI framework.

Reasons:

* Native desktop application model
* Mature widgets
* Good drag-and-drop support
* Model/View architecture
* PDF/image preview integration options
* Cross-platform
* Professional UI potential
* Qt styling
* Threading support

---

# 9. Core Libraries

The exact library versions should be pinned during implementation.

## 9.1 Pillow

Purpose:

* Image loading
* Image conversion
* Resizing
* Cropping
* Rotation
* Compression
* Metadata handling
* ICO generation
* Basic image manipulation

Potential formats:

* JPEG
* PNG
* WebP
* GIF
* BMP
* TIFF
* ICO
* JPEG 2000
* PPM
* PGM
* PBM

Additional formats may be added through optional backends.

---

## 9.2 PDF Engine & Licensing Strategy

### Primary: PyMuPDF (Fitz)
* **Purpose:** High-performance PDF rendering, page inspection, text/image extraction, visual annotations, rotation, page insertion/deletion, preview generation.
* **Licensing Requirement:** PyMuPDF is licensed under **GNU AGPL v3** (or a paid commercial Artifex license).
  * If the project is released under **GNU AGPL v3**, PyMuPDF may be freely distributed.
  * If the project is released under a **permissive / proprietary** license without a commercial Artifex agreement, the rendering and inspection backend **MUST** be abstracted behind an interface and use **`pypdfium2` (Apache 2.0 / BSD-3-Clause)** for rendering and **`pypdf` (BSD-3-Clause)** for manipulation.

---

## 9.3 pypdf

Purpose:

* Pure-Python PDF merging
* PDF splitting
* Page manipulation and structure reordering
* PDF metadata read/write
* Encryption/decryption workflows (Standard PDF security handler)
* Structure repair fallback

Combine PyMuPDF (or pypdfium2) for rendering with pypdf where structural manipulation without rendering is preferred.

---

## 9.4 OCR Engine & Deployment Architecture

Local OCR is executed via a decoupled backend interface:

```text
               ┌───────────────────────┐
               │     OCRService        │
               └───────────┬───────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐
│  TesseractBackend       │ │  LocalOnnxBackend       │
│  (CLI / PyTesseract)    │ │  (e.g., PaddleOCR / ONNX│
│  Bundled/System Engine  │ │   pure local model)     │
└─────────────────────────┘ └─────────────────────────┘
```

### Deployment & Binary Strategy:
1. **Windows Distribution:** Native `tesseract.exe` and English training data (`eng.traineddata`, ~23MB) are packaged inside the application's runtime assets directory or managed via a built-in "Language Pack Downloader" for additional languages (German, Spanish, French, Chinese, etc.).
2. **Subprocess Execution:** Invocation of local Tesseract binaries must use explicit argument lists via `subprocess.Popen` / `QProcess` with non-blocking pipes, explicitly setting `TESSDATA_PREFIX` to the application's local directory.
3. **No External Network:** OCR must execute 100% locally with zero cloud API fallbacks.

---

## 9.5 Optional ImageMagick Backend

ImageMagick may be integrated as an optional local backend for formats not supported by Pillow (e.g., vector EPS, multi-layer PSD, specialized RAW formats).

* It must remain local and run in isolated subprocesses.
* Pillow remains the default and mandatory image engine. ImageMagick is strictly a pluggable, optional tool if present on the system.

---

# 10. Application Architecture

The application should use a layered architecture.

```text
┌──────────────────────────────────────────────┐
│                  GUI Layer                   │
│                  PySide6                     │
├──────────────────────────────────────────────┤
│              Application Layer               │
│       Commands / Workflows / Jobs            │
├──────────────────────────────────────────────┤
│                Service Layer                 │
│     PDF / Image / OCR / Metadata Services    │
├──────────────────────────────────────────────┤
│                 Core Layer                   │
│ Models / Validation / Configuration / Events │
├──────────────────────────────────────────────┤
│             Processing Backends              │
│ Pillow / PyMuPDF / pypdf / OCR / optional    │
│ ImageMagick                                  │
├──────────────────────────────────────────────┤
│               File System                    │
└──────────────────────────────────────────────┘
```

---

# 11. Proposed Project Structure

```text
offline_toolbox/
│
├── pyproject.toml
├── README.md
├── LICENSE
├── ARCHITECTURE_AND_REQUIREMENTS.md
├── CHANGELOG.md
│
├── src/
│   └── offline_toolbox/
│       │
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── app/
│       │   ├── application.py
│       │   ├── bootstrap.py
│       │   └── dependencies.py
│       │
│       ├── core/
│       │   ├── models/
│       │   ├── enums.py
│       │   ├── errors.py
│       │   ├── events.py
│       │   ├── result.py
│       │   └── validators.py
│       │
│       ├── pdf/
│       │   ├── service.py
│       │   ├── models.py
│       │   ├── reader.py
│       │   ├── writer.py
│       │   ├── renderer.py
│       │   ├── merger.py
│       │   ├── splitter.py
│       │   ├── pages.py
│       │   ├── rotation.py
│       │   ├── extraction.py
│       │   ├── compression.py
│       │   ├── metadata.py
│       │   ├── encryption.py
│       │   ├── annotations.py
│       │   ├── forms.py
│       │   ├── editing.py
│       │   ├── repair.py
│       │   └── validation.py
│       │
│       ├── images/
│       │   ├── service.py
│       │   ├── converter.py
│       │   ├── resize.py
│       │   ├── crop.py
│       │   ├── rotate.py
│       │   ├── compression.py
│       │   ├── metadata.py
│       │   └── formats.py
│       │
│       ├── ocr/
│       │   ├── service.py
│       │   ├── engine.py
│       │   ├── models.py
│       │   └── preprocessing.py
│       │
│       ├── jobs/
│       │   ├── manager.py
│       │   ├── job.py
│       │   ├── queue.py
│       │   └── worker.py
│       │
│       ├── filesystem/
│       │   ├── manager.py
│       │   ├── temporary.py
│       │   ├── naming.py
│       │   └── permissions.py
│       │
│       ├── config/
│       │   ├── settings.py
│       │   ├── defaults.py
│       │   └── persistence.py
│       │
│       └── ui/
│           ├── main_window.py
│           ├── home/
│           ├── pdf/
│           ├── images/
│           ├── tools/
│           ├── dialogs/
│           ├── widgets/
│           ├── models/
│           └── resources/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── regression/
│
├── scripts/
│   ├── build.py
│   ├── package.py
│   └── version.py
│
└── resources/
    ├── icons/
    ├── themes/
    └── templates/
```

---

# 12. UI Architecture
 
 Use Qt's Model/View architecture wherever appropriate.
 
 Major UI components:
 
 ```text
 MainWindow
 │
 ├── NavigationSidebar
 │
 ├── HomePage
 │
 ├── PDFWorkspace
 │   ├── PageThumbnailPanel (QListView / custom QAbstractListModel with async QPixmap loaders)
 │   ├── PDFViewerCanvas (QGraphicsView / QGraphicsScene interactive viewport)
 │   │   ├── RenderedPageBackgroundItem (QGraphicsPixmapItem)
 │   │   ├── InteractiveOverlayLayer (QGraphicsItemGroup for annotations/text/stamps)
 │   │   └── SelectionTransformer (QGraphicsItem handles: resize, move, rotate)
 │   ├── Toolbar (Tool selection: pan, zoom, select, annotate, text, shapes)
 │   └── PropertiesPanel (Stroke, fill, font, opacity, rotation)
 │
 ├── ImageWorkspace
 │
 ├── BatchJobPanel
 │
 └── SettingsPage
 ```
 
 ### 12.1 Interactive PDF Canvas Design (QGraphicsView / QGraphicsScene)
 * **Decoupled Interactive State:** PDF pages are rendered at target DPI to off-screen pixmaps and set as static background items in a `QGraphicsScene`.
 * **Vector Overlay Items:** User additions (highlights, arrows, rectangles, freehand paths, text blocks) exist as live `QGraphicsItem` instances with full undo/redo, move, resize, and styling capabilities.
 * **Baking/Commit Pipeline:** Only when saving or exporting does the command subsystem translate the `QGraphicsScene` coordinates and vector/text primitives into PDF drawing commands and form annotations via the PDF engine.
 
 ---
 
 # 13. Home Screen

The Home screen should provide large, obvious actions.

```text
┌──────────────────────────────────────────────┐
│ Offline Toolbox                             │
│                                              │
│       Drop files anywhere                   │
│                                              │
│  ┌────────────┐ ┌────────────┐               │
│  │  PDF       │ │  Images    │               │
│  │  Tools     │ │  Tools     │               │
│  └────────────┘ └────────────┘               │
│                                              │
│  Quick Actions                               │
│  • Merge PDFs                                │
│  • Split PDF                                 │
│  • Images → PDF                              │
│  • Convert Image                             │
│  • Compress PDF                              │
│                                              │
│  🟢 Offline                                  │
└──────────────────────────────────────────────┘
```

---

# 14. Drag-and-Drop

The application must support dragging files into:

* Home screen
* PDF workspace
* Image workspace
* Conversion dialogs
* Batch processing areas

The application should automatically determine compatible operations.

---

# 15. PDF Feature Requirements

## 15.1 Open PDF

The application shall:

* Open PDF files
* Display page count
* Display file size
* Render pages
* Display thumbnails
* Handle encrypted PDFs gracefully
* Detect invalid PDFs

---

# 16. PDF Page Management

Required:

* Select one page
* Select multiple pages
* Select all pages
* Delete selected pages
* Duplicate selected pages
* Reorder pages
* Extract selected pages
* Export selected pages
* Insert pages
* Replace pages
* Append pages
* Prepend pages

Drag-and-drop should control page order.

---

# 17. PDF Rotation

Required:

### Individual

* 90° clockwise
* 90° counter-clockwise
* 180°

### Multiple selection

Rotate selected pages.

### Entire document

Rotate all pages.

### Reset

Restore page rotation to original state before saving.

Rotations should modify PDF page orientation rather than rasterizing pages.

---

# 18. PDF Merge

Users shall be able to:

1. Select multiple PDFs.
2. Preview files.
3. Reorder files.
4. Merge them.
5. Choose output location.

Example:

```text
A.pdf
B.pdf
C.pdf

        ↓

Merged.pdf
```

---

# 19. PDF Split

Support:

* Split by page ranges
* Split every N pages
* Split into individual pages
* Extract selected pages

Example:

```text
1-5
6-10
11-20
```

Output:

```text
document_001.pdf
document_002.pdf
document_003.pdf
```

---

# 20. PDF Compression

Provide presets:

* Maximum quality
* Balanced
* Small file
* Custom

Potential controls:

* Image resolution
* JPEG quality
* Image recompression
* Remove unused objects
* Metadata removal
* Font optimization where safe

The application must warn that aggressive compression may reduce quality.

---

# 21. PDF-to-Image

Supported output:

* PNG
* JPEG
* WebP
* TIFF

Options:

* Page selection
* DPI
* Quality
* Output folder
* Filename template
* Background color
* Batch export

---

# 22. Image-to-PDF

Support:

* Single image → PDF
* Multiple images → one PDF
* Each image → separate PDF

Options:

* Page size
* Orientation
* Margins
* Fit to page
* Crop to page
* Center image
* DPI
* JPEG quality
* Background

Preset page sizes:

* A4
* Letter
* Legal
* A3
* A5
* Original image dimensions
* Custom

---

# 23. Image Conversion

Supported common formats:

* JPEG
* PNG
* WebP
* GIF
* BMP
* TIFF
* ICO
* JPEG 2000
* PPM
* PGM
* PBM

Optional extended support:

* AVIF
* HEIC/HEIF
* SVG
* RAW formats
* Other ImageMagick-compatible formats

---

# 24. ICO Generation

The application should support:

```text
PNG/JPEG
   ↓
ICO
```

ICO sizes:

* 16×16
* 24×24
* 32×32
* 48×48
* 64×64
* 128×128
* 256×256

Allow multiple resolutions in a single ICO.

---

# 25. Image Operations
 
 Required:
 
 * Resize
 * Crop
 * Rotate
 * Flip horizontally
 * Flip vertically
 * Grayscale
 * Compression
 * DPI adjustment
 * Canvas resizing
 * Background color
 * Transparency handling
 
 ### 25.1 Color Space & Alpha Handling Rules
 Pillow raises runtime exceptions (e.g., `cannot write mode RGBA as JPEG`) if color conversions are unhandled. The image engine must adhere to strict conversion pipelines:
 
 1. **RGBA/LA to JPEG Conversion:**
    * Automatically flatten alpha onto a matte background before JPEG encoding.
    * User-configurable matte color (Default: White `#FFFFFF`).
 2. **CMYK to RGB/sRGB Conversion:**
    * Convert CMYK to RGB using standard ICC color profiles where present, or Pillow's standard `convert('RGB')` transform to prevent inverted/washed out colors.
 3. **P Mode (Paletted with transparency):**
    * Convert to RGBA prior to transformation or export.
 
 ---
 
 # 26. Batch Image Processing

Example:

```text
Input:
100 PNG files

Operation:
Resize to 1920px
Convert to JPEG
Quality 90

Output:
100 JPEG files
```

Requirements:

* Progress indicator
* Cancel operation
* Retry failed files
* Skip unsupported files
* Output naming
* Output folder selection
* Collision handling

---

# 27. Metadata

Support viewing and, where safe, modifying:

* Filename
* File size
* Creation time
* Modification time
* Image dimensions
* DPI
* EXIF
* PDF metadata
* Author
* Title
* Subject
* Keywords
* Creator
* Producer

Provide:

> Remove metadata

option.

---

# 28. PDF Annotation

Required annotation types:

* Highlight
* Underline
* Strikethrough
* Text note
* Freehand drawing
* Line
* Arrow
* Rectangle
* Ellipse
* Checkmark
* Cross
* Stamp

Annotations should remain editable where the underlying PDF format supports it.

---

# 29. PDF Text Addition
 
 Users should be able to:
 
 * Click on a page
 * Add text
 * Choose font size
 * Choose font
 * Choose alignment
 * Choose color
 * Move text
 * Resize text area
 
 ### 29.1 Typography & Font Embedding Strategy
 * **Cross-Platform Embedding:** To guarantee that PDFs render identically on all devices and viewers, standard open-source variable/static fonts must be bundled with the application:
   * **Sans-serif:** Inter or Roboto (Regular, Bold, Italic)
   * **Serif:** Noto Serif or Liberation Serif
   * **Monospace:** JetBrains Mono or Inconsolata
 * **System Fonts:** System fonts queried via Qt's `QFontDatabase` may also be used, with the PDF engine embedding the font subset or warning if an un-embeddable system font is selected.
 * **Encoding:** Text addition must support standard UTF-8 text strings with proper glyph lookup to prevent corrupted character encoding (mojibake).
 
 ---

# 30. PDF Image Addition

Users should be able to:

* Insert image
* Move image
* Resize image
* Rotate image
* Delete image

Supported input formats should follow the image engine.

---

# 31. Existing PDF Content Editing

This feature must use a conservative approach.

The system should attempt to edit existing content only where safe.

Possible supported operations:

* Detect text blocks
* Select text blocks
* Replace text in supported PDFs
* Move text blocks
* Delete content
* Replace images where safely identifiable

The system must NOT rasterize the entire document merely to fake editing.

If safe editing cannot be performed:

> "This content cannot be safely edited without changing the PDF structure."

The user should be offered alternatives such as adding replacement text or covering/redacting the original content.

---

# 32. Redaction

Provide true redaction where technically supported.

Workflow:

```text
Select content
      ↓
Mark for redaction
      ↓
Apply redactions
      ↓
Remove underlying content
```

Important:

Redaction must not merely draw a black rectangle over sensitive information.

---

# 33. OCR

OCR should be completely local.

Supported workflows:

```text
Image → OCR → Text
```

```text
Scanned PDF → OCR → Searchable PDF
```

Requirements:

* Language selection
* Multiple language support
* Page selection
* OCR confidence where available
* Text extraction
* Searchable PDF output

OCR engine must be abstracted from the rest of the application.

---

# 34. PDF Forms

Future feature.

Support:

* Fill forms
* Text fields
* Checkboxes
* Radio buttons
* Dropdowns
* Signature fields
* Reset fields
* Flatten forms

---

# 35. Digital Signatures

Future feature.

Potential support:

* Draw signature
* Type signature
* Import signature image
* Place signature
* Date
* Name

Cryptographic digital signatures should be treated as a separate advanced feature from visual signatures.

---

# 36. PDF Security

Support:

* Open password
* Encryption
* Permissions
* Printing restrictions
* Copy restrictions
* Editing restrictions

Password removal must only be supported when the user supplies the required password/authorization.

---

# 37. PDF Repair

Future feature.

Potential repair operations:

* Rebuild cross-reference tables
* Remove invalid objects
* Repair metadata
* Reconstruct document structure where possible
* Recover readable pages
* Validate output

The repair tool must always create a new file.

---

# 38. PDF Validation

Before saving processed PDFs:

* Verify document can be reopened
* Verify page count
* Verify pages are readable
* Verify expected output exists
* Verify file is not zero bytes
* Verify basic PDF structure

For destructive operations, the application should validate before replacing anything.

---

# 39. Job System
 
 Long-running operations must not block the UI.
 
 ### 39.1 Concurrency & Execution Architecture (Windows-Safe)
 To prevent UI freezing, avoid GIL deadlocks, and cleanly handle Windows `spawn` process semantics:
 
 1. **Thread Pool for I/O & C-Extension Tasks (`QThreadPool` + `QRunnable`):**
    * Image conversions, standard PDF merging/splitting, and page rendering release the Python GIL in underlying C-libraries (Pillow/MuPDF/PDFium).
    * These run via a bounded `QThreadPool` using custom `QRunnable` workers with dedicated `QObject` signal emitters (`progress`, `result`, `error`).
 2. **Process Isolation for Heavy / Untrusted Tasks (`QProcess` or isolated worker pool):**
    * Local OCR (Tesseract CLI execution) and external converters (ImageMagick CLI) must run as detached asynchronous subprocesses managed via `QProcess` or a supervised multiprocessing worker.
    * This guarantees that any native crashes (segfaults or memory spikes in malformed document parsers) do not take down the primary Qt application.
 3. **Cancellation & Cleanup:**
    * Every worker checks an `is_cancelled` token at safe step intervals (e.g., between pages or batch items).
    * On cancellation, partial files are deleted immediately by the temporary file manager.
 
 Example:
 
 ```text
 UI
  │
  ▼
 JobManager
  │
  ├── QThreadPool (In-process C-extensions: Rendering, Pillow, PDF Merge)
  └── QProcess / Subprocess (Out-of-process isolation: OCR, External Binaries)
        │
        ▼
 Processing Engine
 ```
 
 UI requirements:
 
 * Progress
 * Current file
 * Current operation
 * Estimated progress where possible
 * Cancel
 * Pause where practical
 * Error reporting
 * Completed count
 * Failed count
 
 ---

# 40. Batch Job Model

Each job should contain:

```text
Job
├── ID
├── Operation
├── Input files
├── Output configuration
├── Options
├── Status
├── Progress
├── Error
└── Result
```

Statuses:

* Pending
* Running
* Completed
* Failed
* Cancelled

---

# 41. Error Handling

Errors should be understandable.

Bad:

> ValueError: xref table invalid

Better:

> This PDF appears to be damaged or uses a PDF feature that this operation cannot modify safely.

Provide:

* Human-readable explanation
* Technical details expandable
* Suggested solution
* Continue batch processing where possible

---

# 42. Temporary Files

All temporary files must be created in an application-managed temporary directory.

Requirements:

* Unique temporary directory per operation
* Cleanup after completion
* Cleanup after cancellation
* Cleanup on application startup
* Cleanup on application shutdown
* Avoid retaining user documents unnecessarily

---

# 43. File Naming

Default naming:

```text
filename_converted.ext
filename_compressed.pdf
filename_merged.pdf
filename_split_001.pdf
filename_page_001.png
```

Users should be able to customize naming templates.

---

# 44. Overwrite Protection

Default:

> Never overwrite original files.

If output already exists:

```text
file.pdf
file_1.pdf
file_2.pdf
```

or prompt the user.

Settings should allow:

* Ask every time
* Automatically rename
* Overwrite

---

# 45. Undo / Redo

The PDF workspace should support an operation history where technically possible.

Example:

```text
Rotate page
Add text
Move image
Delete page

Undo
Undo
Redo
```

The application should distinguish:

* UI editing history
* File-saving history

Original files must remain untouched until saving.

---

# 46. Autosave / Recovery

Future feature.

The application may periodically save workspace state.

Recovery data must:

* Remain local
* Be temporary
* Be cleaned after successful save
* Never upload documents

---

# 47. Recent Files

Optional local recent-file history.

Store only:

* File path
* Last opened time
* File type

Do not store document contents.

Provide:

> Clear Recent Files

---

# 48. Search

PDF search should support:

* Find text
* Next/previous
* Case-sensitive option
* Highlight results
* Page navigation

OCR text should be searchable after OCR processing.

---

# 49. Page Thumbnail System

Requirements:

* Thumbnail generation
* Lazy loading
* Page selection
* Multi-selection
* Drag-and-drop reordering
* Visual rotation state
* Page number
* Optional page size information

Large PDFs must not load every full-resolution page into memory simultaneously.

---

# 50. Memory Management & Document Scale Guardrails
 
 The application must be designed for large documents and extreme batches.
 
 Avoid:
 
 ```text
 Load entire 500-page PDF as full-resolution images.
 ```
 
 ### 50.1 Memory Guardrails & Thresholds
 * **Document Scale Limits:**
   * Standard files: Full interactive viewing supported.
   * Large document warning threshold: > 500 pages or > 250 MB.
   * Hard processing strategy switch: For documents exceeding 1,000 pages, thumbnail rendering is throttled to on-demand viewport visibility, and batch operations execute via disk-streaming pipes rather than keeping objects in-memory.
 * **Thumbnail Cache Budget:**
   * Maximum in-memory thumbnail cache: 150 MB (approx. 300–500 low-res 150px thumbnails).
   * LRU cache eviction strategy; evicted thumbnails are re-rendered on demand when scrolled into view.
 * **Full Page Viewport Caching:**
   * Only the currently visible page (plus 1 page ahead and 1 page behind) is cached at full render resolution.
 
 ---
 
 # 51. Performance Requirements
 
 Target Benchmarks:
 
 * Application startup: under 2.5 seconds on SSD
 * Single image conversion (12MP JPEG to PNG/WebP): < 400ms
 * PDF page navigation / flip: < 100ms
 * Page thumbnail generation: > 20 pages/second on modern multicore CPU
 * UI thread responsiveness: Never block the main event loop for > 16ms (maintain 60fps UI animations)
 * Batch jobs: Distribute jobs across `min(cpu_count, 8)` parallel threads/workers without exceeding 80% RAM exhaustion
 
 Performance should be measured in automated integration benchmarks rather than assumed.

---

# 52. Accessibility

Support:

* Keyboard navigation
* Visible focus indicators
* Logical tab order
* Accessible button labels
* Tooltips
* Scalable UI
* High-contrast-friendly design
* Keyboard shortcuts

---

# 53. Keyboard Shortcuts

Suggested:

```text
Ctrl+O       Open
Ctrl+S       Save
Ctrl+Shift+S Save As
Ctrl+Z       Undo
Ctrl+Y       Redo
Ctrl+F       Search
Ctrl+A       Select all
Delete       Delete selected pages/items
Ctrl+Shift+M Merge
Ctrl+Shift+P Split
R            Rotate
```

Shortcuts should be configurable later.

---

# 54. Themes

Support:

* Light
* Dark
* System

Do not sacrifice usability for visual complexity.

---

# 55. Settings

Settings categories:

## General

* Default output folder
* Recent files
* Confirm destructive operations

## PDF

* Default page size
* Compression preset
* Default DPI
* Metadata behavior

## Images

* Default JPEG quality
* Default image format
* Default resize behavior

## Privacy

* Temporary file cleanup
* Metadata stripping
* Recent files
* Network/update settings

## Appearance

* Theme
* UI scaling

---

# 56. Offline Guarantee

The application must function with:

* Wi-Fi disabled
* Ethernet disconnected
* DNS unavailable
* Firewall blocking all network access

Normal processing must continue.

Automated tests should include an offline environment.

---

# 57. Telemetry

Default:

> No telemetry.

No analytics should be required for operation.

If telemetry is ever added, it must be:

* Explicitly opt-in
* Clearly documented
* Disabled by default
* Never contain file contents

---

# 58. Security Requirements

The application must:

* Avoid executing arbitrary document content
* Validate file paths
* Avoid unsafe shell execution
* Sanitize filenames
* Use subprocesses safely when external tools are used
* Never trust PDF metadata as executable content
* Handle malformed PDFs defensively

External executables must receive arguments through safe subprocess APIs rather than shell strings.

---

# 59. Licensing & Dependency Compliance Matrix

To ensure clean commercial and open-source distribution:

| Dependency | License | Distribution & Linking Rule |
| :--- | :--- | :--- |
| **PySide6 (Qt for Python)** | LGPL v3 | Permitted in closed/commercial apps via dynamic linking (standard wheel). Reverse engineering/re-linking terms satisfied. |
| **Pillow** | HPND / MIT-like | Permissive; attribution notice retained. |
| **pypdf** | BSD-3-Clause | Permissive; attribution notice retained. |
| **PyMuPDF (Fitz)** | AGPL v3 / Commercial | **Dual-licensed.** If app is AGPLv3, use freely. If proprietary, replace backend with **`pypdfium2` (Apache 2.0)** or purchase Artifex commercial license. |
| **Tesseract OCR (CLI)** | Apache 2.0 | Permissive; can be bundled as an isolated external executable with copyright notices. |

All bundled open-source licenses must be collected and exposed in an in-app `About -> Third-Party Licenses` dialog.

---

# 60. Testing Strategy

## Unit tests

Test:

* File validation
* Filename generation
* Page selection
* Rotation logic
* Conversion logic
* Compression options
* Configuration
* Job management

## Integration tests

Test:

* Image → PDF
* PDF → Image
* Merge
* Split
* Rotation
* OCR
* Metadata
* Encryption

## Regression tests

Maintain a collection of representative PDFs/images.

Test:

```text
Input
  ↓
Operation
  ↓
Output
  ↓
Reopen output
  ↓
Validate
```

---

# 61. Test File Categories

Test against:

* Simple text PDFs
* Image-only PDFs
* Scanned PDFs
* Large PDFs
* PDFs with embedded fonts
* PDFs with annotations
* PDFs with forms
* Encrypted PDFs
* Damaged PDFs
* PDFs containing transparency
* PDFs with unusual page sizes
* PDFs with mixed page orientations

Images:

* JPEG
* PNG
* WebP
* GIF
* TIFF
* BMP
* ICO
* Transparent images
* CMYK images
* Large images
* Animated formats where applicable

---

# 62. Architecture Rule: No UI Logic in Processing Engines

Bad:

```text
PDFWindow.rotate_page()
```

performing all PDF manipulation directly.

Preferred:

```text
UI
 ↓
RotatePagesCommand
 ↓
PDFService
 ↓
PDFBackend
```

This keeps the processing engine testable and reusable.

---

# 63. Architecture Rule: Backend Abstraction

Use interfaces/protocols where appropriate.

Example:

```text
ImageBackend
├── PillowBackend
└── ImageMagickBackend

OCRBackend
├── TesseractBackend
└── FutureOCRBackend
```

This allows technology changes without rewriting the UI.

---

# 64. Architecture Rule: Operations as Commands

Operations should ideally be represented as commands.

Example:

```text
RotatePagesCommand
MergePDFCommand
SplitPDFCommand
ConvertImageCommand
ResizeImageCommand
CompressPDFCommand
```

Benefits:

* Undo/redo
* Logging
* Testing
* Batch processing
* Consistent progress reporting

---

# 65. Architecture Rule: Immutable Inputs

Processing functions should treat input files as immutable.

Example:

```text
Input:
original.pdf

Operation:
compress

Output:
original_compressed.pdf
```

Never modify `original.pdf` unless explicitly requested.

---

# 66. Output Validation

Every major operation should validate its output.

Example:

```text
Process
  ↓
Write output
  ↓
Reopen output
  ↓
Validate
  ↓
Success
```

If validation fails:

```text
Output was not saved as the requested final file.
Original remains untouched.
```

---

# 67. Logging

Logs should contain:

* Operation
* Start/end time
* Success/failure
* Error category
* Processing duration

Logs should NOT contain:

* File contents
* Extracted personal data
* OCR text
* Passwords
* Sensitive PDF metadata

---

# 68. Packaging & Binary Distribution
 
 Primary target:
 
 ```text
 OfflineToolbox.exe (Self-contained Windows executable)
 ```
 
 Packaging Strategy:
 
 * **Toolchain:** PyInstaller / Nuitka with spec configuration.
 * **Embedded Asset Bundling:**
   * PySide6 Qt plugins (platforms, styles, image formats).
   * Bundled font family (`resources/fonts/Inter-*.ttf`).
   * Theme styles (`resources/themes/*.qss`).
   * Bundled Tesseract Windows engine binaries (`tesseract.exe`, DLL dependencies, and `tessdata/eng.traineddata`).
 * **Binary Integrity & Antivirus Heuristics:**
   * Executable code signing (EV / Standard Authenticode certificate) to eliminate Windows Defender SmartScreen false positives for offline utility binaries.
   * Portable build produces a folder distribution (`OfflineToolbox_Portable/`) with local relative paths and zero Windows Registry writes.
 
 ---

# 69. Installer

Future installer should provide:

* Install location
* Start menu shortcut
* Desktop shortcut
* File associations
* Uninstall support

Optional file associations:

```text
.pdf
.png
.jpg
.jpeg
.webp
.tiff
.ico
```

---

# 70. Portable Version

Provide optional:

```text
OfflineToolbox_Portable/
    OfflineToolbox.exe
    resources/
    config/
```

Portable mode must not require administrator privileges.

---

# 71. File Associations

Users may choose to associate:

* PDF
* JPEG
* PNG
* WebP
* TIFF
* ICO

Opening an associated file should launch the appropriate workspace.

---

# 72. Context Menu Integration

Future Windows feature:

Right-click:

```text
Convert to JPEG
Convert to PDF
Compress PDF
Open with Offline Toolbox
```

This should be optional.

---

# 73. First Release Scope

## Version 0.1 — Foundation

Implement:

* Application shell
* PySide6 UI
* Drag-and-drop
* File selection
* Configuration
* Job manager
* Temporary file manager
* Basic logging
* Basic error handling

---

# 74. Version 0.2 — Image Engine

Implement:

* JPEG
* PNG
* WebP
* BMP
* TIFF
* ICO
* Image conversion
* Resize
* Rotate
* Crop
* Compression
* Batch conversion

---

# 75. Version 0.3 — PDF Engine

Implement:

* PDF viewer
* Thumbnails
* Merge
* Split
* Extract
* Delete pages
* Reorder
* Duplicate
* Rotate individual pages
* Rotate selected pages
* Rotate entire document

---

# 76. Version 0.4 — PDF Conversion

Implement:

* Image → PDF
* PDF → PNG
* PDF → JPEG
* PDF → WebP
* Page selection
* DPI control
* Batch export

---

# 77. Version 0.5 — PDF Optimization

Implement:

* Compression
* Metadata
* Basic validation
* Output verification
* File-size reporting

---

# 78. Version 0.6 — Annotation

Implement:

* Text
* Highlight
* Underline
* Strikethrough
* Shapes
* Drawing
* Arrows
* Notes
* Images

---

# 79. Version 0.7 — OCR

Implement:

* Local OCR engine
* Image OCR
* PDF OCR
* Searchable PDF
* Text extraction
* Language selection

---

# 80. Version 0.8 — Security & Forms

Implement:

* Password protection
* Encryption
* PDF forms
* Form filling
* Visual signatures

---

# 81. Version 0.9 — Advanced PDF

Investigate:

* Existing text editing
* Image replacement
* Redaction
* PDF repair
* Advanced metadata
* Digital signatures

---

# 82. Version 1.0

Version 1.0 should only be released when:

* Major workflows are stable
* Files are not silently corrupted
* Output validation is reliable
* Offline operation is verified
* Crash recovery is acceptable
* Large PDFs can be handled reasonably
* Batch operations are reliable
* UI is polished
* Installer works
* Portable version works

---

# 83. Critical Safety Rule

The application must prioritize:

```text
Data integrity
    >
Feature completeness
    >
Convenience
```

If an operation could corrupt or significantly alter a document unexpectedly, the application should refuse the operation or clearly warn the user.

---

# 84. PDF Editing Philosophy

The PDF editor should use three levels of editing.

## Level 1 — Safe

Examples:

* Add text
* Add image
* Add annotation
* Rotate page
* Reorder pages

These should be supported aggressively.

## Level 2 — Controlled

Examples:

* Replace image
* Modify text blocks
* Modify metadata

These require structural analysis.

## Level 3 — Experimental

Examples:

* Arbitrary existing-text editing
* Complex layout reconstruction
* Advanced object manipulation

These should only be enabled once sufficiently reliable.

---

# 85. Recommended User Experience

The application should follow this workflow:

```text
Open / Drop Files
       ↓
Detect file type
       ↓
Show relevant actions
       ↓
Choose operation
       ↓
Preview
       ↓
Process
       ↓
Validate
       ↓
Save
       ↓
Show result
```

Example:

```text
Dropped:
12 images

Suggested actions:

[ Images → PDF ]
[ Convert to JPEG ]
[ Convert to PNG ]
[ Resize ]
[ Compress ]
```

---

# 86. Smart Batch Mode

If multiple files are dropped, detect whether they are compatible.

Example:

```text
5 PDFs
```

Suggested:

```text
Merge PDFs
Split PDFs
Compress PDFs
```

For:

```text
20 images
```

Suggested:

```text
Images → PDF
Batch Convert
Resize
Compress
```

For:

```text
PDF + images
```

Suggested:

```text
Combine into PDF
```

---

# 87. Future Features

Potential additions:

* PDF/A conversion
* PDF/X support
* EPUB → PDF
* HTML → PDF
* Markdown → PDF
* Text → PDF
* CSV → PDF
* Contact sheet generator
* Image montage
* QR code generation
* Barcode generation
* Watermarks
* Bates numbering
* Booklet printing
* Print optimization
* Duplicate image detection
* Image metadata editor
* Color profile management
* Screenshot utility
* Scan/import workflow
* Local document indexing
* Full-text local search

These should not block the core product.

---

# 88. Success Criteria

The project is successful if a user can install it and perform common operations without thinking about implementation details.

Examples:

### Convert image

```text
Drop image
→ Select JPEG
→ Convert
```

### Images to PDF

```text
Drop 30 images
→ Images → PDF
→ Save
```

### Merge PDF

```text
Drop 4 PDFs
→ Arrange
→ Merge
→ Save
```

### Rotate page

```text
Open PDF
→ Select page
→ Rotate
→ Save
```

### Rotate everything

```text
Open PDF
→ Rotate All
→ 90° clockwise
→ Save
```

### Compress

```text
Drop PDF
→ Compress
→ Balanced
→ Save
```

No website.
No account.
No upload.
No subscription.

---

# 89. Product Positioning

The application should not be marketed as:

> "A free Adobe Acrobat clone."

Instead:

> **A fast, private, offline toolbox for PDFs and images.**

Possible tagline:

> **Your files. Your computer. No upload required.**

---

# 90. Long-Term Vision

The long-term application should become a unified local document utility.

```text
                     OFFLINE TOOLBOX
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
         PDF              Images            OCR
          │                 │                 │
     ┌────┼────┐       ┌────┼────┐            │
     │    │    │       │    │    │            │
   Edit Pages Forms   Convert Resize Compress Search
     │    │    │       │    │    │            │
     └────┴────┴───────┴────┴────┴────────────┘
                            │
                     Local File System
```

The fundamental architectural goal is that new functionality can be added without redesigning the application.

---

# 91. Final Engineering Principle

Do not attempt to build every feature immediately.

Build a strong foundation:

```text
File handling
     ↓
Job system
     ↓
Processing engines
     ↓
PDF/image models
     ↓
GUI
     ↓
Preview
     ↓
Validation
```

Then add functionality incrementally.

The first milestone should be a **small, polished application that already works extremely well**, not a massive application with dozens of unreliable features.

The application should grow into a mini Acrobat-like offline suite rather than attempting to become Acrobat on day one.
