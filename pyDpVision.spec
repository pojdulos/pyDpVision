# -*- mode: python ; coding: utf-8 -*-

import os
import glob

block_cipher = None

# Funkcja do rekurencyjnego zbierania plików
# def collect_files(src_folder, dest_folder):
#     data_files = []
#     for root, _, files in os.walk(src_folder):
#         for file in files:
#             src_file = os.path.join(root, file)
#             dest_file = os.path.join(dest_folder, os.path.relpath(root, src_folder))
#             data_files.append((src_file, dest_file))
#     return data_files

def collect_files(src_folder, dest_folder):
    data_files = []
    for root, _, files in os.walk(src_folder):
        for file in files:
            if not file.endswith('.py') and '__pycache__' not in root:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_folder, os.path.relpath(root, src_folder))
                data_files.append((src_file, dest_file))
    return data_files

def collect_all_files(src_folder, dest_folder):
    """Collect all files including .py (used for plugins loaded via importlib at runtime)."""
    data_files = []
    for root, _, files in os.walk(src_folder):
        for file in files:
            if '__pycache__' not in root and not file.endswith('.pyc'):
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_folder, os.path.relpath(root, src_folder))
                data_files.append((src_file, dest_file))
    return data_files

gui_files = collect_files('dpVision/gui', 'dpVision/gui')
shader_files = collect_files('dpVision/shaders', 'dpVision/shaders')
preset_files = collect_files('dpVision/presets', 'dpVision/presets')

a = Analysis(
    ['main.py'],
    pathex=['d:/praca/pyDpVision'],
    binaries=[],
    datas=gui_files + shader_files + preset_files,
    hiddenimports=['pydicom.encoders.gdcm','pydicom.encoders.pylibjpeg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,	
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pyDpVision',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pyDpVision',
)

# Kopiuj plugins obok exe (nie do _internal)
import shutil
_dist_plugins = os.path.join('dist', 'pyDpVision', 'plugins')
if os.path.exists(_dist_plugins):
    shutil.rmtree(_dist_plugins)
shutil.copytree('plugins', _dist_plugins)
