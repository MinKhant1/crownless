# PyInstaller build recipe for Crownless.
#   Windows -> dist/Crownless.exe   (one file, no console window)
#   macOS   -> dist/Crownless.app   (app bundle)
# Build on the OS you are targeting: build_windows.ps1 or build_mac.sh, or the GitHub Actions workflow.
import sys

from PyInstaller.utils.hooks import collect_submodules

# The game finds these next to its modules (Path(__file__)), so keep the same folders inside the bundle.
datas = [
    ("assets", "assets"),
    ("rendering/shaders", "rendering/shaders"),
]
# moderngl picks its OpenGL backend (wgl / darwin / x11 / egl) at runtime by name.
hiddenimports = collect_submodules("glcontext")

a = Analysis(
    ["main.py"],
    datas=datas,
    hiddenimports=hiddenimports,
    # numpy is only used by tools/ (audio generation); the game never imports it
    excludes=["tkinter", "numpy"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="Crownless",
        console=False,
        upx=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="Crownless", upx=False)
    app = BUNDLE(
        coll,
        name="Crownless.app",
        bundle_identifier="com.crownless.game",
        info_plist={
            "CFBundleDisplayName": "Crownless",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="Crownless",
        console=False,
        upx=False,
    )
