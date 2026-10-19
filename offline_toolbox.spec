# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

root_dir = Path.cwd().resolve()
src_dir = root_dir / "src"

# Collect all package data
datas = []

# 1. App resources (icons, themes)
resources_dir = src_dir / "offline_toolbox" / "resources"
if resources_dir.exists():
    datas.append((str(resources_dir), "offline_toolbox/resources"))
    datas.append((str(resources_dir), "resources"))

# 2. Third-party package data (RapidOCR onnx models, python-docx templates)
datas += collect_data_files("rapidocr_onnxruntime")
datas += collect_data_files("docx")

# Hidden imports that might be dynamically loaded
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

a = Analysis(
    [str(src_dir / "offline_toolbox" / "__main__.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

ico_path = str(resources_dir / "icons" / "app_logo.ico")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OfflineToolbox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Desktop GUI app, no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ico_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="OfflineToolbox",
)
