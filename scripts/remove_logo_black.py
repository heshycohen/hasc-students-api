"""
Make black/near-black pixels in the logo transparent and save.
Run from repo root: python scripts/remove_logo_black.py
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow")
    sys.exit(1)

# Paths: rock-access-web/frontend/public/logo.png
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Script lives in rock-access-web/scripts/ so repo root is parent of SCRIPT_DIR's parent
REPO_ROOT = os.path.dirname(SCRIPT_DIR)  # rock-access-web
LOGO_PATH = os.path.join(REPO_ROOT, "frontend", "public", "logo.png")

if not os.path.isfile(LOGO_PATH):
    print(f"Logo not found: {LOGO_PATH}")
    sys.exit(1)

# Threshold: pixels with R,G,B all below this become transparent
BLACK_THRESHOLD = 40

img = Image.open(LOGO_PATH).convert("RGBA")
pixels = img.load()
w, h = img.size
for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        if r <= BLACK_THRESHOLD and g <= BLACK_THRESHOLD and b <= BLACK_THRESHOLD:
            pixels[x, y] = (r, g, b, 0)

img.save(LOGO_PATH, "PNG")
print(f"Updated {LOGO_PATH}: black pixels set to transparent.")
