import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from render import render, section_img
from PIL import Image, ImageDraw
names = ["bombka_okragla_60", "bombka_okragla_80", "bombka_okragla_100", "bombka_kropla"]
SC, H, W = 4.8, 640, 420
tiles = []
for n in names:
    m = trimesh.load(OUT + "/" + n + ".stl")
    tiles.append(render([m], 0, 8, W, H, ext=SC, center=(0, 52)))
    tiles.append(render([m], 90, 8, W, H, ext=SC, center=(0, 52)))
o = Image.new("RGB", (W * len(tiles), H), "white")
for i, t in enumerate(tiles): o.paste(t, (i * W, 0))
o.save(OUT + "/_prev_B4.png"); print(o.size)
