import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from render import render, grid
P = pickle.load(open(OUT + "/_lp_frames.pkl", "rb")); FRb = P["FRb"]
kr = trimesh.load(OUT + "/lp_krolik_calosc.stl"); re_ = trimesh.load(OUT + "/lp_renifer_calosc.stl")
body_s = trimesh.load(OUT + "/lp_korpus_bazowy.stl")
def G(nm, s): return to_global(trimesh.load(OUT + f"/lp_{nm}.stl"), FRb[s])
ear = [G("ucho_prawe", 1), G("ucho_lewe", -1)]
eard = [G("ucho_dlugie_prawe", 1), G("ucho_dlugie_lewe", -1)]
ant = [G("poroze_prawe", 1), G("poroze_lewe", -1)]
ext = 800 / 165
ims = []
for ms in ([kr], [re_], [body_s] + ear, [body_s] + eard, [body_s] + ant):
    ims.append(render([flat_view(m) for m in ms], 25, 8, 380, 800, ext=ext, center=(0, 75)))
grid(ims, 5).save(OUT + "/_lp_prev1.png")
# czesci lezace
imp = []
for nm in ("ucho_prawe", "ucho_dlugie_prawe", "poroze_prawe", "poroze_lewe"):
    m = trimesh.load(OUT + f"/lp_{nm}.stl")
    imp.append(render([flat_view(m)], 0, 55, 380, 520, ext=520/50, center=(0, 3), light=(-0.3, -0.5, 0.8)) if False else None)
