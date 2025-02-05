# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],  # Changed from 'src/main.py' since file is on Desktop
    pathex=[r'c:\Users\Paulj\Desktop'],  # Added pathex to find the main file
    binaries=[],
    datas=[],
    hiddenimports=['PIL', 'PyQt6'],  # Added required hidden imports
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Image Converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version_info={  # Fixed version info format
        'fileversion': (1, 0, 0, 0),
        'productversion': (1, 0, 0, 0),
        'CompanyName': 'Zanz Softwares',
        'FileDescription': 'Image Converter',
        'ProductName': 'Image Converter',
        'FileVersion': '1.0.0',
        'ProductVersion': '1.0.0',
        'OriginalFilename': 'Image Converter.exe'
    },
    icon='icon.ico',  # Changed path to just icon name if it's in same directory
    uac_admin=True
)