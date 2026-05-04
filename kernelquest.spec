# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Kernel Quest: The Memory Leak.

Build with:
    pyinstaller kernelquest.spec --noconfirm
"""

import sys

block_cipher = None
APP_NAME = "KernelQuest"

a = Analysis(
    ["src/kernelquest/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "kernelquest",
        "kernelquest.core",
        "kernelquest.data",
        "kernelquest.entities",
        "kernelquest.systems",
        "kernelquest.ui",
        "kernelquest.world",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="com.kernelquest.game",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": "Kernel Quest",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
