# -*- mode: python ; coding: utf-8 -*-
# Specyfikacja PyInstaller dla Amber.
# Budowa:  pyinstaller Amber.spec
import os

block_cipher = None

# Ścieżka do katalogu UI (statyczne pliki) i config.json
root = os.path.abspath(os.path.dirname(SPEC))
static = os.path.join(root, "ui", "static")

a = Analysis(
    ["run.py"],
    pathex=[root],
    binaries=[],
    datas=[
        (os.path.join(static, "index.html"), os.path.join("ui", "static")),
        (os.path.join(static, "style.css"), os.path.join("ui", "static")),
        (os.path.join(static, "app.js"), os.path.join("ui", "static")),
        (os.path.join(root, "config.json"), "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "mss",
        "pyautogui",
        "pyautogui._pyautogui_win",
        "pyautogui._pyautogui_osx",
        "pyautogui._pyautogui_x11",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Amber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Amber",
)
