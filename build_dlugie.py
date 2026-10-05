"""Dlugie uszy (wymienne prawe/lewe + przytopione do czapki jajka). Ten sam czop 5x5x8, ta sama podstawa dopasowana do krolika i jajka."""
import sys, math, time
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *
from build_figurki import FRb, FRe, TRIMS, add_local, L_VIS
import build_egg as EG

T0 = time.time()
L_LONG = 42.0
print(f"dlugosc widoczna: krotkie {L_VIS:.1f} mm, dlugie {L_LONG:.1f} mm")
pz = egg_P0(1)[2]
print(f"czubek ucha na jajku: krotkie ~{pz + L_VIS*math.cos(TILT)+0.22:.1f}, dlugie ~{pz + L_LONG*math.cos(TILT)+0.22:.1f} mm")

parts = {}
for s, nm in ((+1, "prawe"), (-1, "lewe")):
    parts[nm] = part_mesh(ear_flat(L_LONG), TRIMS[s], True, (-10, 10), (-9, L_LONG + 3), 0.2)
    save(parts[nm], f"ucho_dlugie_{nm}.stl", False, "druk na plecach; wersja dluga")

# --- jajko: czapka z dlugimi uszami przytopionymi ---
axes2, (X2, Y2, Z2), _, Fcap2, _, _, _ = EG.fields(True, ztop=pz + L_LONG + 6)
F2 = Fcap2.copy()
for s in (+1, -1):
    F2 = add_local(F2, axes2, FRe[s], part_fn(ear_flat(L_LONG), None, peg=False, plate_b0=-4.5), b_rng=(-9, L_LONG + 3))
cap_l = decimate(mesh_from_F(F2, axes2, EG.VOX), 220000, label="czapka-uszy-dlugie")
save(cap_l, "jajko_czapka_uszy_dlugie.stl", True, "otworem do dolu; dlugie uszy przytopione")
print("wierzch calosci (zlozone):", round(cap_l.bounds[1][2], 1))

# --- pasowanie wymiennych dlugich uszu: korpus krolika i czapka jajka ---
body = trimesh.load(OUT + "/korpus_bazowy.stl")
cap_pl = trimesh.load(OUT + "/jajko_czapka_gniazda.stl"); cap_pl.apply_translation([0, 0, EG.Z_CAP0 + (0.0)])
for label, tgt, FR, F_body in (("korpus krolika/renifera", body, FRb, bunny_F), ("czapka jajka", cap_pl, FRe, egg_F)):
    tree = surf_tree(tgt, 600000)
    for s, nm in ((+1, "prawe"), (-1, "lewe")):
        g = to_global(parts[nm], FR[s])
        dd, _ = tree.query(g.vertices)
        a_, b_, c_ = FR[s].to_local(*g.vertices.T)
        V = g.vertices
        Fv = F_body(V[:, 0], V[:, 1], V[:, 2])
        Fv = np.minimum(Fv, -socket_F(a_, b_, c_))
        print(f"{label}, ucho dlugie {nm}: podstawa {dd[b_ > 0.4].min():.2f} | czop {dd[b_ < -0.5].min():.2f} mm | w bryle {int((Fv > 0.02).sum())} | wierzch z={V[:, 2].max():.1f}")
print(f"czas {time.time() - T0:.0f} s")
