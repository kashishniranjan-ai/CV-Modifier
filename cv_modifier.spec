# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for CV-Modifier.
Builds a single portable Windows executable (.exe).
Application data, database, logs, and exports are maintained in a 'data' folder
alongside the .exe file.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Base data and hidden imports
datas = [
    ('data/assets', 'data/assets'),
    ('sample_data', 'sample_data'),
]
binaries = []
hidden_imports = [
    'reportlab',
    'reportlab.platypus',
    'reportlab.lib',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'sqlite3',
    'smtplib',
    'ssl',
    'email',
    'comtypes',
    'comtypes.client',
]

# Use collect_all for pymupdf, fitz, docx, keyring, and qtawesome (for font files)
for package_name in ['pymupdf', 'fitz', 'docx', 'keyring', 'qtawesome']:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
    datas += pkg_datas
    binaries += pkg_binaries
    hidden_imports += pkg_hiddenimports

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6',
        'PyQt6-Qt6',
        'PyQt6.sip',
        'tkinter',
        'matplotlib',
        'scipy',
        'torch',
        'transformers',
        'tensorflow',
        'pandas',
        'numpy.random._examples',
        'IPython',
        'jupyter',
    ],
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
    name='CV-Modifier',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI window without black cmd prompt
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='data/assets/app_icon.ico',
)

