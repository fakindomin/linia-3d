import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matrioszka import *
from parts import surf_tree
from render import render, section_img
from PIL import Image, ImageDraw
LD = lambda n: trimesh.load(OUT + "/" + n + ".stl")
Lg = egg_L(); sM = solve_scale(Lg, make_M, 0.8); Mg = make_M(sM); sS = solve_scale(Mg, make_S, 0.8); Sg = make_S(sS)
def place(cup, cap, e, z0):
    c1 = cup.copy(); c1.apply_translation([0, 0, z0])
    c2 = cap.copy(); c2.apply_translation([0, 0, z0 + e.Z_CAP0])
    return c1, c2
L1, L2 = LD("jajko_miseczka"), LD("jajko_czapka_gniazda"); L2.apply_translation([0, 0, Lg.Z_CAP0])
z_M = Lg.floor + 0.8
M1, M2 = place(LD("jajko_M_miseczka"), LD("jajko_M_czapka"), Mg, z_M)
z_S = z_M + Mg.floor + 0.8
S1, S2 = place(LD("jajko_S_miseczka"), LD("jajko_S_czapka"), Sg, z_S)
def check(label, guest, host_meshes, hostg, off=0.0):
    tree = surf_tree(trimesh.util.concatenate(host_meshes), 900000)
    V = np.vstack([g.vertices for g in guest])
    d, _ = tree.query(V)
    rho = np.hypot(V[:, 0], V[:, 1])
    zz = V[:, 2] - off
    rh = np.where(zz < hostg.ZL, hostg.cup_r(zz), hostg.cap_body_r(zz))
    outside = int(((rho > rh + 0.01) | (zz < hostg.floor) | (zz > hostg.CEIL)).sum())
    print(f"  {label}: min. odl. do scianek {d.min():.2f} mm | wierzcholki poza wneka {outside} | wys. goscia {V[:,2].max()-V[:,2].min():.1f}, szczyt z={zz.max():.1f} (sufit {hostg.CEIL:.1f})")
print("== zagniezdzenie ==")
check("M w L", [M1, M2], [L1, L2], Lg)
check("S w M", [S1, S2], [M1, M2], Mg, z_M)
# wlasne pasowanie czapka-miseczka (kolnierz): odleglosc bore-lip
for nm, e, c1, c2 in (("L", Lg, L1, L2), ("M", Mg, M1, M2), ("S", Sg, S1, S2)):
    zc = c1.vertices[:, 2]
    t = surf_tree(c1, 600000)
    V2 = c2.vertices
    rho2 = np.hypot(V2[:, 0], V2[:, 1])
    z0 = c1.bounds[0][2]
    sel = (rho2 < e.R_BORE + 0.05) & (V2[:, 2] > z0 + e.ZS) & (V2[:, 2] < z0 + e.ZL + 0.3)
    d, _ = t.query(V2[sel])
    print(f"  {nm}: kolnierz-czapka min. odl. {d.min():.2f} mm (nominalnie {0.25})")
SC = 880 / 100.0
im = [section_img([L1, L2, M1, M2, S1, S2], 440, 880, SC, (0, 45), colors=[(40,40,40),(40,40,40),(160,60,40),(160,60,40),(40,80,160),(40,80,160)]),
      render([L1, L2], 0, 8, 440, 880, ext=SC, center=(0, 45)),
      render([M1, M2], 0, 8, 440, 880, ext=SC, center=(0, 36)),
      render([S1, S2], 0, 8, 440, 880, ext=SC, center=(0, 28))]
o = Image.new("RGB", (440 * 4, 880), "white")
for i, t in enumerate(im): o.paste(t, (i * 440, 0))
o.save(OUT + "/_prev_B3.png"); print(o.size)
