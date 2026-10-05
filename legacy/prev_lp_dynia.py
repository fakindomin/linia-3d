import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from render import render, grid
D = pickle.load(open(OUT + "/_lp_dynia.pkl", "rb")); FR = D["FR_STEM"]
L = lambda n: trimesh.load(OUT + f"/{n}.stl")
sm, lb, sp = L("lp_dynia_korpus"), L("lp_dynia_korpus_platy"), L("lp_dynia_ogonek")
stg = to_global(D["stem_local"], FR)
FV = lambda ms: [flat_view(m) for m in ms]
sc = 640 / 118
ims = [render(FV([sm, stg]), 20, 18, 700, 640, ext=sc, center=(0, 40), dens=9),
       render(FV([lb, stg]), 20, 18, 700, 640, ext=sc, center=(0, 40), dens=9),
       render(FV([lb, stg]), 0, 60, 700, 640, ext=sc, center=(0, 20), dens=9),
       render(FV([sp]), 0, 12, 360, 640, ext=640 / 40, center=(0, 14), dens=14)]
grid(ims, 4).save(OUT + "/podglad_dynia_lowpoly.png")
