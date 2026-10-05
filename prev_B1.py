import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from render import render, section_img
from PIL import Image, ImageDraw
L = lambda n: trimesh.load(OUT + "/" + n + ".stl")
SC, H, W = 4.4, 700, 330
names = sys.argv[1:] or ["wazon_butelka", "wazon_owal", "wazon_walec", "swiecznik_tealight", "swiecznik_swieca"]
tiles = []
for n in names:
    m = L(n)
    zc = m.extents[2] / 2
    a = render([m], 0, 8, W, H, ext=SC, center=(0, zc))
    s = section_img([m], W, H, ext=SC, center=(0, zc))
    d = ImageDraw.Draw(a); d.text((8, 8), n, fill=(60, 60, 60))
    tiles += [a, s]
o = Image.new("RGB", (W * len(tiles), H), "white")
for i, t in enumerate(tiles):
    o.paste(t, (i * W, 0))
o.save(OUT + "/_prev_B1.png"); print(o.size)
