# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None

a = Analysis(
    ['gui_bollette.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'bill_extractor',
        'dateutil',
        'dateutil.parser',
        'dateutil.tz',
        'dateutil.relativedelta',
        'pypdf',
        'pypdf._reader',
        'pypdf._page',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.styles.numbers',
        'openpyxl.utils',
        'openpyxl.utils.dataframe',
        'pandas',
        'pandas.io.formats.excel',
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
    [],
    exclude_binaries=True,
    name='EstrattoreBollette',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # nessuna finestra terminale
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EstrattoreBollette',
)

# Su macOS produce il bundle .app (onedir mode, compatibile con Gatekeeper)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='EstrattoreBollette.app',
        icon=None,
        bundle_identifier='it.parser-bollette.gui',
        info_plist={
            'CFBundleDisplayName': 'Estrattore Bollette',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
