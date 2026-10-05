"""Korpus bazowy + krolik / renifer (calosc i wymienne), uszy, poroza. Wyniki w out/"""
import sys, time, math
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *

VOX = 0.4
TOTAL_H = 150.0
T0 = time.time()

FRb = {s: mount_frame(s, bunny_P0(s)) for s in (+1, -1)}
FRe = {s: mount_frame(s, egg_P0(s)) for s in (+1, -1)}
# STANDARD v1.0: czesc przycieta do KOPERT (idealny profil + pad + luz 0,3), a nie do powierzchni zeber -> ta sama czesc pasuje do zebra i lowpoly
from models import BUNNY, EGG
from standard import rb_trims
TRIMS = {s: rb_trims([(BUNNY, "ear_R" if s > 0 else "ear_L"), (EGG, "ear_R" if s > 0 else "ear_L")]) for s in (+1, -1)}   # krolik/renifer + jajko

L_VIS = (TOTAL_H - bunny_P0(1)[2]) / math.cos(TILT) - 0.22   # korekta zaokraglenia wierzcholka
ear_R = ear_flat(L_VIS)
ant_R = antler_flat(mirror=False)
ant_L = antler_flat(mirror=True)


def gridfield(ztop, xh=21):
    return make_grid(-xh, xh, -21, 21, -1.0, ztop, VOX)


def add_local(Fg, axes, fr, fn, a_rng=(-10, 10), b_rng=(-9, 36), c_rng=(-1, 8)):
    x, y, z = axes
    pts = np.array([fr.O + a * fr.A + b * fr.B + c * fr.C for a in a_rng for b in b_rng for c in c_rng])
    lo, hi = pts.min(0) - 0.5, pts.max(0) + 0.5
    ix = np.where((x >= lo[0]) & (x <= hi[0]))[0]
    iy = np.where((y >= lo[1]) & (y <= hi[1]))[0]
    iz = np.where((z >= lo[2]) & (z <= hi[2]))[0]
    Xs, Ys, Zs = np.meshgrid(x[ix], y[iy], z[iz], indexing="ij")
    a, b, c = fr.to_local(Xs, Ys, Zs)
    sub = np.ix_(ix, iy, iz)
    Fg[sub] = np.maximum(Fg[sub], fn(a, b, c))
    return Fg


def build_body(sockets, fuse=None):
    axes, (X, Y, Z) = gridfield(TOTAL_H + 3.0 if fuse else bunny_P0(1)[2] + 6, 28 if fuse == 'antler' else 21)
    F = bunny_F(X, Y, Z)
    for s in (+1, -1):
        if sockets:
            a, b, c = FRb[s].to_local(X, Y, Z)
            F = np.minimum(F, -socket_F(a, b, c)).astype(np.float32)
    if fuse:
        for s in (+1, -1):
            fp = ear_flat(L_VIS) if fuse == "ear" else antler_flat(mirror=(s < 0))
            fn = part_fn(fp, None, peg=False, plate_b0=-4.5)
            F = add_local(F, axes, FRb[s], fn, a_rng=((-10, 21) if s > 0 else (-21, 10)) if fuse == "antler" else (-10, 10))
    return axes, F


def decimate(m, red=0.0):
    return m


def top_z(parts):
    return max(p.bounds[1][2] for p in parts)


if __name__ == "__main__":
    print(f"P0 krolik z={bunny_P0(1)[2]:.2f}, jajko z={egg_P0(1)[2]:.2f}, L_VIS={L_VIS:.2f}")
    print("== czesci wymienne ==")
    parts = {}
    for s, nm in ((+1, "prawe"), (-1, "lewe")):
        fe = ear_flat(L_VIS)
        parts[f"ucho_{nm}"] = (part_mesh(fe, TRIMS[s], True, (-10, 10), (-9, L_VIS + 3), 0.2), s)
    parts["poroze_prawe"] = (part_mesh(ant_R, TRIMS[+1], True, (-10, 21), (-9, L_VIS + 3), 0.2), +1)
    parts["poroze_lewe"] = (part_mesh(ant_L, TRIMS[-1], True, (-21, 10), (-9, L_VIS + 3), 0.2), -1)
    for nm, (m, s) in parts.items():
        save(m, nm + ".stl", upright=False, note="druk na plecach (plaska strona do stolu)")
    print("== korpus bazowy ==")
    axes, F = build_body(True)
    body = mesh_from_F(F, axes, VOX)
    save(body, "korpus_bazowy.stl", upright=True, note="2 gniazda 5,4x5,4x9, pochylone 14 st.")
    tree = surf_tree(body, 600000)
    print("== pasowanie (korpus bazowy z gniazdami) ==")
    glob = {}
    for nm, (m, s) in parts.items():
        g = to_global(m, FRb[s])
        glob[nm] = g
        d = clearance(g, tree)
        a_, b_, c_ = np.array([FRb[s].to_local(*g.vertices.T)])[0]
        dd, _ = tree.query(g.vertices)
        d_base = float(dd[b_ > 0.4].min()); d_peg = float(dd[b_ < -0.5].min())
        V = g.vertices
        Fv = bunny_F(V[:, 0], V[:, 1], V[:, 2])
        a, b, c = FRb[s].to_local(V[:, 0], V[:, 1], V[:, 2])
        Fv = np.minimum(Fv, -socket_F(a, b, c))
        print(f"{nm}: min. odl. podstawa {d_base:.2f} | czop/gniazdo {d_peg:.2f} mm | wierzcholki w korpusie {int((Fv > 0.02).sum())} | wierzch z={g.bounds[1][2]:.1f}")
    print("== calosc (przytopione) ==")
    for fuse, nm in (("ear", "krolik_calosc.stl"), ("antler", "renifer_calosc.stl")):
        axes, F = build_body(True if False else False, fuse)
        mm = mesh_from_F(F, axes, VOX)
        save(mm, nm, upright=True)
    # podglady
    from render import render, grid
    imgs = []
    krol = trimesh.load(OUT + "/krolik_calosc.stl"); ren = trimesh.load(OUT + "/renifer_calosc.stl")
    imgs += [render([krol], 0, 6, 420, 900, ext=900/170*1.0, center=(0, 75)), render([ren], 0, 6, 420, 900, ext=900/170, center=(0, 75))]
    # zlozone: korpus + wymienne
    for lst in (("ucho_prawe", "ucho_lewe"), ("poroze_prawe", "poroze_lewe")):
        bm = body.copy()
        ps = [bm] + [glob[n] for n in lst]
        imgs.append(render(ps, 0, 6, 420, 900, ext=900/170, center=(0, 75)))
    grid(imgs, 4).save(OUT + "/_prev_figurki.png")
    json.dump(REPORT, open(OUT + "/_raport.json", "w"), indent=1, ensure_ascii=False)
    print(f"czas {time.time() - T0:.0f} s")
