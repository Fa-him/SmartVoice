# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).resolve().parent


def project_data(source: str, target: str):
    return (str(project_root / source), target)


hiddenimports = [
    "Backend.ImageGeneration",
    "Backend.YouTubeController",
    "PIL.Image",
]

for package in (
    "edge_tts",
    "selenium",
    "webdriver_manager",
    "huggingface_hub",
    "AppOpener",
):
    hiddenimports.extend(collect_submodules(package))


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        project_data("Frontend/Graphics", "Frontend/Graphics"),
        project_data(".env.example", "."),
        project_data("README.md", "."),
        project_data("LICENSE", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        ".env",
        "pygame.examples",
        "pygame.tests",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SmartVoice",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SmartVoice",
)
