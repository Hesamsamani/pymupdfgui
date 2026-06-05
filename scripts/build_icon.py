#!/usr/bin/env python3
"""Build icon.ico from icon.png with every Windows-required size.

Run from the repo root:

    python scripts/build_icon.py

This is invoked automatically by the release-build workflow before
PyInstaller, so the bundled .exe always carries an .ico that matches
the latest icon.png in the repo.
"""
from pathlib import Path
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow not installed. Run: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "icon.png"
DST = ROOT / "icon.ico"

# Windows reads multiple resolutions from a single .ico for the taskbar
# (16/20/24/32), Alt-Tab (40/48), Start menu (64–96), and high-DPI/Settings
# (128/256). Shipping all of them avoids the blurry / fallback-icon issue.
ICO_SIZES = [(16, 16), (20, 20), (24, 24), (32, 32),
             (40, 40), (48, 48), (64, 64), (96, 96),
             (128, 128), (256, 256)]


def main() -> int:
    if not SRC.exists():
        print(f"error: {SRC} not found", file=sys.stderr)
        return 1
    img = Image.open(SRC).convert("RGBA")
    if img.size[0] < 256 or img.size[1] < 256:
        print(f"warning: source is {img.size}; recommend ≥ 256×256 for crisp scaling",
              file=sys.stderr)
    img.save(DST, format="ICO", sizes=ICO_SIZES)
    print(f"wrote {DST.relative_to(ROOT)} with {len(ICO_SIZES)} sizes "
          f"({', '.join(f'{w}' for w, _ in ICO_SIZES)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
