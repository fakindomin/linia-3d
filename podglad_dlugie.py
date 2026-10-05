import sys, numpy as np, trimesh
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import render, grid
from PIL import ImageDraw
from lib import OUT
Z0 = 34.2
def ld(n, dz=0.0):
    m = trimesh.load(f"{OUT}/{n}.stl"); m.apply_translation([0, 0, dz]); return m
cup = ld("jajko_miseczka")
short = ld("jajko_czapka_uszy", Z0)
long_ = ld("jajko_czapka_uszy_dlugie", Z0)
# wzor
top = trimesh.load("/home/claude/ref/obj_1_MiniEggEarsEggTopHalf.stl")
bot = trimesh.load("/home/claude/ref/obj_3_MiniEggEarsBottomHalf.stl")
c_t = (top.bounds[0][:2] + top.bounds[1][:2]) / 2; c_b = (bot.bounds[0][:2] + bot.bounds[1][:2]) / 2
top.apply_translation([-c_t[0], -c_t[1], 33.0]); bot.apply_translation([-c_b[0], -c_b[1], 0])
ext = 880 / 140
res = []
for yaw in (0, 90):
    res.append(render([bot, top], yaw, 6, 440, 880, ext=ext, center=(0, 66), colors=[(150, 165, 185)] * 2))
res[0].save("/tmp/claude-0/-home-claude/db1eb572-0fd4-5725-b9c8-f07e7256a189/scratchpad/ref_yaw.png")
res[1].save("/tmp/claude-0/-home-claude/db1eb572-0fd4-5725-b9c8-f07e7256a189/scratchpad/ref_yaw90.png")

cols = [(205, 195, 180)] * 2
im_ref = res[0]
im_s = render([cup, short], 0, 6, 440, 880, ext=ext, center=(0, 66), colors=cols)
im_l = render([cup, long_], 0, 6, 440, 880, ext=ext, center=(0, 66), colors=cols)
im_l90 = render([cup, long_], 90, 6, 440, 880, ext=ext, center=(0, 66), colors=cols)
labs = ["wzor: calosc 128.9 mm (uszy 46.9)",
        "krotkie uszy: calosc 118.0 mm (uszy 28.3)",
        "dlugie uszy: calosc 128.7 mm (uszy 39)",
        "dlugie uszy, z boku"]
g = grid([im_ref, im_s, im_l, im_l90], 4, labels=labs)
# linie poziome: wierzch wzoru 128.9 oraz wierzchy krotkich/dlugich
d = ImageDraw.Draw(g)
pad = 10
def yline(z, col):
    y = pad + 880/2 - (z - 66) * ext
    d.line([(0, y), (g.width, y)], fill=col, width=1)
yline(128.9, (200, 60, 60)); yline(118.0, (60, 120, 200))
g.save(OUT + "/podglad_uszy_dlugie.png")
print(g.size)
