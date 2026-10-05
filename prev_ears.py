import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ears_A import *
from render import render, grid
from PIL import ImageDraw
body = trimesh.load(OUT + "/korpus_bazowy.stl")
ims = []; labs = []
for nm in ("mis", "kot", "lis", "sowa"):
    ps = [body]
    for s, sn in ((+1, "prawe"), (-1, "lewe")):
        m = trimesh.load(OUT + f"/ucho_{nm}_{sn}.stl")
        ps.append(to_global(m, FRb[s]))
    ims.append(render(ps, 0, 8, 420, 480, ext=10.0, center=(0, 124)))
    ims.append(render(ps, 55, 8, 420, 480, ext=10.0, center=(0, 124)))
g = grid(ims, 4)
g.save("/tmp/claude-0/-home-claude/db1eb572-0fd4-5725-b9c8-f07e7256a189/scratchpad/ears_prev.png")
print(g.size)
