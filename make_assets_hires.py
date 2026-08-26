from PIL import Image, ImageFilter, ImageFont, ImageDraw
import numpy as np
import os

PROJ = os.path.dirname(os.path.abspath(__file__))
src = Image.open(os.path.join(PROJ, "_ref_hi.png")).convert("RGBA")

# normalize to a clean transparent cutout (drop faint edge alpha, keep crisp edges)
a = np.array(src)
a[..., 3] = np.where(a[..., 3] > 120, 255, 0)
src = Image.fromarray(a)

# base pet image
pet = src.copy()
pet.thumbnail((720, 720), Image.LANCZOS)
pet = pet.filter(ImageFilter.UnsharpMask(radius=2, percent=45, threshold=3))
pet.save(os.path.join(PROJ, "pet.png"))
print("pet.png:", pet.size)
