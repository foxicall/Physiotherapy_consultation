"""Rebuild the original geometric app icon; Pillow is only a development dependency."""
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parents[1] / 'docs' / 'icons'
folder.mkdir(exist_ok=True)
canvas = Image.new('RGB', (1024, 1024), '#183e36')
draw = ImageDraw.Draw(canvas)
draw.rounded_rectangle((240, 260, 784, 714), radius=116, fill='#e4efdf')
draw.polygon(((305, 680), (305, 800), (450, 690)), fill='#e4efdf')
draw.rounded_rectangle((465, 345, 559, 629), radius=20, fill='#32664e')
draw.rounded_rectangle((370, 440, 654, 534), radius=20, fill='#32664e')
for name, size in [('icon-192.png',192), ('icon-512.png',512), ('maskable-512.png',512), ('apple-touch-icon.png',180)]:
    canvas.resize((size,size), Image.Resampling.LANCZOS).save(folder/name, optimize=True)
print('Built 4 PWA icons')
