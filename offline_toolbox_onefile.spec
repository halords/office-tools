# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

root_dir = Path.cwd().resolve()
src_dir = root_dir / "src"

# 1. Collect app resources (icons, themes)
datas = []
resources_dir = src_dir / "offline_toolbox" / "resources"
if resources_dir.exists():
    datas.append((str(resources_dir), "offline_toolbox/resources"))
    datas.append((str(resources_dir), "resources"))

# 2. Collect RapidOCR ONNX models and docx templates
datas += collect_data_files("rapidocr_onnxruntime")
datas += collect_data_files("docx")

# Hidden imports for dynamic loaders
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
    "fitz",
    "pdf2docx",
    "rapidocr_onnxruntime",
    "docx",
    "PIL",
    "PIL.Image",
    "PIL.ImageOps",
    "PIL.ImageCms",
    "numpy",
]
hiddenimports += collect_submodules("rapidocr_onnxruntime")
hiddenimports += collect_submodules("docx")

# Exclude heavy unnecessary packages from the user's environment to ensure portability and small size
excludes = [
    "tensorflow",
    "keras",
    "torch",
    "torchvision",
    "scipy",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    "pandas",
    "openpyxl",
    "pytest",
    "tkinter",
    "tk",
    "tcl",
    "test",
    "unittest",
]

a = Analysis(
    [str(src_dir / "offline_toolbox" / "__main__.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

ico_path = str(resources_dir / "icons" / "app_logo.ico")

# Standalone Single-File Executable: Everything packed into ONE .exe
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OfflineToolbox_Standalone",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windowed desktop application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ico_path,
)
