"""Lowpoly: korpus bazowy (2 gniazda), uszy krotkie/dlugie, poroza, krolik_calosc, renifer_calosc.
 lp_korpus_bazowy.stl, lp_ucho_prawe/lewe.stl, lp_ucho_dlugie_prawe/lewe.stl, lp_poroze_prawe/lewe.stl, lp_krolik_calosc.stl, lp_renifer_calosc.stl"""
import sys, time, pickle
import numpy as np
sys.path.insert(0, "/home/claude/linia")
from lp_parts import *

T0 = time.time()
TOTAL_H = 150.0
L_LONG = 42.0

body = body_solid()
egg = egg_outer_full()
FRb, FRe = {}, {}
for s in (+1, -1):
    FRb[s], zb = frame_at(s, body)
    FRe[s], ze = frame_at(s, egg)
L_SHORT = (TOTAL_H - zb) / math.cos(TILT)
print(f"P0 korpus z={zb:.3f}, jajko z={ze:.3f}; L krotkie={L_SHORT:.2f}, dlugie={L_LONG:.1f}")
ob, oe = offset(body, GAP_), offset(egg, GAP_)


def trimmed(part_local, s, ext=2.0):
    """czesc w ukladzie lokalnym przycieta (z luzem 0,3) do korpusu i do jajka, z czopem 5x5x8"""
    p = diff(part_local, to_local(ob, FRb[s]), to_local(oe, FRe[s]))
    comps = p.split(only_watertight=False)
    if len(comps) > 1:
        comps.sort(key=lambda c: -abs(c.volume))
        print(f"   (skladowe po przycieciu: {[round(abs(c.volume), 1) for c in comps]})")
        p = comps[0]
    return union(p, peg_solid(ext))


def lam_for_antler():
    lo, hi = 0.9, 1.15
    for _ in range(30):
        mid = (lo + hi) / 2
        top = to_global(antler_solid(mid), FRb[+1]).bounds[1][2]
        lo, hi = (mid, hi) if top < TOTAL_H else (lo, mid)
    return (lo + hi) / 2


LAM = lam_for_antler()
print(f"rozciag poroza lam = {LAM:.4f}")
leaf_s, leaf_l = ear_leaf(L_SHORT, -3.0), ear_leaf(L_LONG, -3.0)
ant_R = antler_solid(LAM)
ant_L = mirror_a(ant_R)

parts = {}
for s, nm in ((+1, "prawe"), (-1, "lewe")):
    parts[f"ucho_{nm}"] = (trimmed(leaf_s, s), s)
    parts[f"ucho_dlugie_{nm}"] = (trimmed(leaf_l, s), s)
parts["poroze_prawe"] = (trimmed(ant_R, +1), +1)
parts["poroze_lewe"] = (trimmed(ant_L, -1), -1)
for nm, (m, s) in parts.items():
    save_lp(m, f"lp_{nm}.stl", upright=False, note="druk na plecach (plaska strona do stolu)")
    a, zr = overhang_report(m, 55.0, 0.3)
    print(f"   nawis >55 st. (druk na plecach): {a:.1f} mm2 {zr}")

# korpus z gniazdami
bm = MF(body)
for s in (+1, -1):
    bm = bm - MF(to_global(socket_solid(), FRb[s]))
body_s = TM(bm)
save_lp(body_s, "lp_korpus_bazowy.stl", upright=True, note="2 gniazda 5,4x5,4x9, pochylone 14 st.")

# calosc: przytopione uszy / poroza (bez przycinania, bez czopa, wejscie 4,5 mm w glowe)
leaf_f = ear_leaf(L_SHORT, -4.5)
ant_Rf = antler_solid(LAM, b0=-4.5)
ant_Lf = mirror_a(ant_Rf)
kr = union(body, *[to_global(leaf_f, FRb[s]) for s in (+1, -1)])
re = union(body, to_global(ant_Rf, FRb[+1]), to_global(ant_Lf, FRb[-1]))
save_lp(kr, "lp_krolik_calosc.stl", upright=True)
save_lp(re, "lp_renifer_calosc.stl", upright=True)

pickle.dump(dict(FRb=FRb, FRe=FRe, L_SHORT=L_SHORT, LAM=LAM, zb=zb, ze=ze), open(OUT + "/_lp_frames.pkl", "wb"))
print(f"czas {time.time() - T0:.0f} s")
