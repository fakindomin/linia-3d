import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from render import render, grid
from PIL import ImageDraw
S = "/tmp/claude-0/-home-claude/db1eb572-0fd4-5725-b9c8-f07e7256a189/scratchpad/"
L = lambda n: trimesh.load(OUT + "/" + n)
ims = []
for nm, w in (("mis", 460), ("kot", 460), ("lis", 560), ("sowa", 460), ("aniol", 640)):
    m = L(f"{nm}_calosc.stl")
    ims.append(render([m], 0, 6, w, 860, ext=5.4, center=(0, 76)))
    ims.append(render([m], 60, 6, w, 860, ext=5.4, center=(0, 76)))
tw = sum(i.width for i in ims)
o = Image.new("RGB", (tw, 860), (255, 255, 255)); x = 0
for i in ims:
    o.paste(i, (x, 0)); x += i.width
o.save(S + "A1.png"); print(o.size)
