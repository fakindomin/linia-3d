import sys, pickle
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *
from render import render, grid, section_img
P = pickle.load(open(OUT + "/_lp_frames.pkl", "rb")); FRb, FRe = P["FRb"], P["FRe"]
E = pickle.load(open(OUT + "/_lp_egg.pkl", "rb"))
L = lambda n: trimesh.load(OUT + f"/{n}.stl")
G = lambda nm, FR, s: to_global(L(f"lp_{nm}"), FR[s])
kr, re_, body_s = L("lp_krolik_calosc"), L("lp_renifer_calosc"), L("lp_korpus_bazowy")
cup, cap, cap_e, cap_l = E["cup"], E["cap_sock"], E["cap_ears"], E["cap_long"]
FV = lambda ms: [flat_view(m) for m in ms]
R1 = lambda ms, yaw=25: render(FV(ms), yaw, 8, 380, 800, ext=800 / 165, center=(0, 75), dens=9)
row1 = [R1([kr]), R1([re_]), R1([body_s] + [G("ucho_prawe", FRb, 1), G("ucho_lewe", FRb, -1)]),
        R1([body_s] + [G("ucho_dlugie_prawe", FRb, 1), G("ucho_dlugie_lewe", FRb, -1)]),
        R1([body_s] + [G("poroze_prawe", FRb, 1), G("poroze_lewe", FRb, -1)])]
R2 = lambda ms, yaw=25: render(FV(ms), yaw, 8, 380, 800, ext=800 / 165, center=(0, 62), dens=9)
ear_e = [G("ucho_prawe", FRe, 1), G("ucho_lewe", FRe, -1)]
ant_e = [G("poroze_prawe", FRe, 1), G("poroze_lewe", FRe, -1)]
row2 = [R2([cup, cap_e]), R2([cup, cap_l]), R2([cup, cap] + ear_e), R2([cup, cap] + ant_e)]
# przekroj y = 0 z jajkiem 44 x 68
zz = np.linspace(FLOOR, FLOOR + 68, 200); t = np.clip(np.abs(zz - (FLOOR + 34)) / 34, 0, 1)
rr = 22 * np.clip(1 - t ** 2.3, 0, None) ** (1 / 2.3)
egg_poly = [(r, z) for r, z in zip(rr, zz)] + [(-r, z) for r, z in zip(rr[::-1], zz[::-1])]
row2.append(section_img([cup, cap], 380, 800, 800 / 165, (0, 62), extra_polys=[egg_poly]))
# czesci lezace (druk na plecach), widok z gory - osobny szeroki panel
def top(ms, W, H, sc):
    out, off = [], 0.0
    for m in ms:
        g = flat_view(m)
        g.apply_translation([off - m.bounds[0][0], 0, 0]); off += m.extents[0] + 6
        out.append(g)
    allv = np.vstack([g.vertices for g in out]); cx = (allv[:, 0].min() + allv[:, 0].max()) / 2
    return render(out, 0, 90, W, H, ext=sc, center=(cx, 20), dens=16)
pa = top([L("lp_ucho_prawe"), L("lp_ucho_dlugie_prawe"), L("lp_poroze_prawe"), L("lp_poroze_lewe")], 1960 - 30, 520, 9.0)
from PIL import Image
a, b = grid(row1, 5), grid(row2, 5)
w = max(a.width, b.width)
out = Image.new("RGB", (w, a.height + b.height + pa.height), (255, 255, 255))
out.paste(a, (0, 0)); out.paste(b, (0, a.height)); out.paste(pa, (15, a.height + b.height))
out.save(OUT + "/podglad_lowpoly.png"); print(out.size)
