"""Pojemnik na jajko niespodzianke (44 x 68 mm): miseczka + czapka z gniazdami + czapka z uszami (przytopionymi)."""
import sys, time, math
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from parts import *
from shapes import *
from build_figurki import FRe, L_VIS, ear_flat, add_local
from standard import LP_SLOPE                       # STANDARD v1.0: jedno nachylenie sufitow wnek dla obu stylow

VOX = 0.35
T0 = time.time()
CONE_DR_DZ = LP_SLOPE                               # nachylenie stozka sufitu |dr/dz| = 1,30 (52 st. od pionu; zapas 3 st. na szum voxeli)
R_TOP = 5.0                                         # promien plaskiego sufitu
Z_A = CEIL_Z - (R_CAV - R_TOP) / CONE_DR_DZ         # tu zaczyna sie stozek
ZL = ZS + LIP_H


def cav_cup_r(z):
    r = np.minimum(egg_R(z) - WALL_CUP, R_CAV)
    return np.where((z >= FLOOR) & (z <= ZS + LIP_H + 0.01), r, -1.0)


def cav_cap_r(z):
    cone = R_CAV - np.clip(z - Z_A, 0, None) * CONE_DR_DZ
    body = np.minimum(np.minimum(R_CAV, egg_R(z) - WALL_CAP_MIN), cone)
    body = np.where((z >= ZL) & (z < CEIL_Z), body, -1.0)
    bore = np.where((z >= Z_CAP0) & (z <= ZL + 0.5), R_BORE, -1.0)
    return np.maximum(body, bore)


def fields(ears, ztop=None):
    ztop = ztop or ((H_EGG + 31.0) if ears else H_EGG + 2.5)
    axes, (X, Y, Z) = make_grid(-(RMAX + 3), RMAX + 3, -(RMAX + 3), RMAX + 3, -2.5 * VOX, ztop, VOX)
    rho = np.sqrt(X ** 2 + Y ** 2)
    Zz = Z * np.ones_like(rho)
    Fout = egg_F(X, Y, Z)
    Fcup_out = np.where(Z <= ZS, Fout, (R_LIP - rho).astype(np.float32))
    Fcav_cup = (cav_cup_r(Z) - rho).astype(np.float32)
    Fcup = np.minimum(np.minimum(Fcup_out, -Fcav_cup), np.minimum(Z, (ZS + LIP_H) - Z)).astype(np.float32)
    Fcav_cap = (cav_cap_r(Z) - rho).astype(np.float32)
    Fcap = np.minimum(np.minimum(Fout, -Fcav_cap), Z - Z_CAP0).astype(np.float32)
    sock = None
    for s in (+1, -1):
        a, b, c = FRe[s].to_local(X, Y, Z)
        sk = socket_F(a, b, c)
        sock = sk if sock is None else np.maximum(sock, sk)
    return axes, (X, Y, Z), Fcup, Fcap, Fcav_cup, Fcav_cap, sock


if __name__ == "__main__":
    print(f"stozek sufitu od z={Z_A:.1f} (r={R_CAV}) do z={CEIL_Z} (r={R_TOP}); P0 jajka z={egg_P0(1)[2]:.2f}")
    axes, (X, Y, Z), Fcup, Fcap, Fcav_cup, Fcav_cap, sock = fields(False)
    # --- sprawdzenia ---
    ov = int(((Fcup > 0) & (Fcap > 0)).sum())
    print(f"kolizja miseczka/czapka (siatka): {ov} voxeli")
    # jajko (superelipsoida 44x68, wykladnik 2,3) w zlozonym wnetrzu
    zs_ = np.linspace(FLOOR, FLOOR + EGG_H, 400)
    t = np.clip(np.abs(zs_ - (FLOOR + EGG_H / 2)) / (EGG_H / 2), 0, 1)
    re = (EGG_D / 2) * np.clip(1 - t ** 2.3, 0, None) ** (1 / 2.3)
    cav = np.maximum(cav_cup_r(zs_), cav_cap_r(zs_))
    print(f"min. luz jajka do scian: {(cav - re).min():.2f} mm; luz nad jajkiem do sufitu: {CEIL_Z - (FLOOR + EGG_H):.1f} mm")

    Fcap_plain = np.minimum(Fcap, -sock).astype(np.float32)
    # grubosc sciany miedzy gniazdami a wnetrzem czapki
    void_s = (sock > 0) & (Fcap > -1)         # powietrze gniazd
    cav_b = Fcav_cap > 0
    dist_to_cav = ndi.distance_transform_edt(~cav_b) * VOX
    # tylko gniazda w obszarze nad szwem
    mask = (sock > 0) & (Z > ZL)
    print(f"min. sciana gniazdo -> wnetrze czapki: {dist_to_cav[mask].min():.2f} mm")

    cup = mesh_from_F(Fcup, axes, VOX)
    cap_plain = mesh_from_F(Fcap_plain, axes, VOX)
    cup = decimate(cup, 220000, label="miseczka")
    cap_plain = decimate(cap_plain, 220000, label="czapka-gniazda")
    save(cup, "jajko_miseczka.stl", True, "otworem do gory")
    save(cap_plain, "jajko_czapka_gniazda.stl", True, "otworem do dolu (brzeg na stole), gniazda na uszy")
    # czapka z uszami (przytopionymi)
    axes2, (X2, Y2, Z2), _, Fcap2, _, _, sock2 = fields(True)
    F2 = Fcap2.copy()
    for s in (+1, -1):
        fn = part_fn(ear_flat(L_VIS), None, peg=False, plate_b0=-4.5)
        F2 = add_local(F2, axes2, FRe[s], fn)
    cap_ears = decimate(mesh_from_F(F2, axes2, VOX), 220000, label="czapka-uszy")
    save(cap_ears, "jajko_czapka_uszy.stl", True, "otworem do dolu; uszy przytopione")
    # kontrola pasowania wymiennych uszu (z korpusu krolika) na czapce z gniazdami
    tree = surf_tree(cap_plain, 600000)
    shift = cap_plain.bounds[0][2]                       # zapis przesunal czapke do stolu: odtworz pozycje zlozona
    cap_asm = cap_plain.copy()                          # siatka w pozycji zlozonej (save() pracuje na kopii)
    tree = surf_tree(cap_asm, 600000)
    for s, nm in ((+1, "ucho_prawe"), (-1, "ucho_lewe"), (+1, "poroze_prawe"), (-1, "poroze_lewe")):
        em = trimesh.load(OUT + f"/{nm}.stl")
        g = to_global(em, FRe[s])
        dd, _ = tree.query(g.vertices)
        a_, b_, c_ = FRe[s].to_local(*g.vertices.T)
        V = g.vertices
        Fv = egg_F(V[:, 0], V[:, 1], V[:, 2])
        a2, b2, c2 = FRe[s].to_local(V[:, 0], V[:, 1], V[:, 2])
        Fv = np.minimum(Fv, -socket_F(a2, b2, c2))
        print(f"{nm} na jajku: min. odl. podstawa {dd[b_ > 0.4].min():.2f} | czop {dd[b_ < -0.5].min():.2f} mm | "
              f"wierzcholki w czapce {int((Fv > 0.02).sum())} | wierzch z={V[:, 2].max():.1f}")
    # podglady
    from render import render, grid, section_img
    cupa = cup.copy()
    capa = cap_ears.copy()
    capp = cap_asm
    ears = [to_global(trimesh.load(OUT + "/ucho_prawe.stl"), FRe[+1]), to_global(trimesh.load(OUT + "/ucho_lewe.stl"), FRe[-1])]
    ext = 880 / 130
    imgs = [render([cupa, capa], 0, 6, 440, 880, ext=ext, center=(0, 55)),
            render([cupa, capp] + ears, 0, 6, 440, 880, ext=ext, center=(0, 55)),
            render([cupa, capp], 0, 6, 440, 880, ext=ext, center=(0, 55))]
    # przekroj y=0: obrys miseczki i czapki oraz jajko 44 x 68 (czerwone)
    zz = np.linspace(FLOOR, FLOOR + EGG_H, 200)
    tt = np.clip(np.abs(zz - (FLOOR + EGG_H / 2)) / (EGG_H / 2), 0, 1)
    rr = (EGG_D / 2) * np.clip(1 - tt ** 2.3, 0, None) ** (1 / 2.3)
    egg_poly = [(r, z) for r, z in zip(rr, zz)] + [(-r, z) for r, z in zip(rr[::-1], zz[::-1])]
    imgs.append(section_img([cupa, capp], 440, 880, ext, (0, 55), extra_polys=[egg_poly]))
    grid(imgs, 4).save(OUT + "/podglad_jajko.png")
    json.dump(REPORT, open(OUT + "/_raport.json", "w"), indent=1, ensure_ascii=False)
    print(f"czas {time.time() - T0:.0f} s")
