"""Jajko niespodzianka RENIFER: miseczka + czapka z wybranym zamkiem (nr 3, luz 0,20 mm), poroze 3-poziomowe i boczne uszy-liscie
z duzego modelu (renifer_kregiel.py) przytopione do czapki; ucho lezy 1 mm PRZED porozem (leafGap).
  miseczka: jajko do szwu ZS = 34, kolnierz 1,5 x 8 mm z wypustka 0,25 mm; dno plaskie (z = 0), wneka jak w build_egg.py (pod jajko 44 x 68);
  czapka:   od szwu (+0,1 mm luzu osiowego) do wierzchu, otwor w dol z rowkiem na wypustke, stozkowy sufit 52 st. (plaski sufit r = 5 na z = 76),
            poroze (ramka jak w duzym modelu: earX = 11,5, odchylenie 12 st.) i uszy-liscie (kat 50 st. od pionu, pozycja jak 'polar 46 st.' glowy).
Zamek liczony dokladnie (obrot profilu + manifold) tak jak w jajko_zamek_wycinek.py; obrys z zebrami z siatki (shapes.egg_F), poroze i uszy z parts.py.
  python3 jajko_renifer.py   -> out/jajko_renifer_miseczka.stl, out/jajko_renifer_czapka.stl (pozycje drukowane) + out/jajko_renifer.png"""
import os, sys, math, time
import numpy as np
import trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import make_grid, mesh_from_F, decimate
from shapes import egg_F, egg_R, R_CAV, RMAX, ZS, ZM, H_EGG, FLOOR, WALL_CUP, WALL_CAP_MIN, CEIL_Z, Y0, EGG_H, EGG_D
from parts import mount_frame, part_fn, antler_geom
from jajko_zamek_proba import LIP_H, BEAD_H, BEAD_Z, GROOVE_D, GAP_Z, BORE_DEPTH, R_LIP, CLEAR_WYBRANY
from jajko_zamek_wycinek import revolve, lip_solid
import renifer_kregiel as RK
from build_figurki import add_local

VOX = 0.25                       # siatka obrysu (zebra) i przytopionych elementow; zamek jest dokladny
CONE = 1.3                       # |dr/dz| stozka sufitu czapki (STANDARD: 52 st. od pionu)
R_TOP = 5.0                      # promien plaskiego sufitu
Z_A = CEIL_Z - (R_CAV - R_TOP) / CONE
ZR = ZS + GAP_Z                  # brzeg czapki
PLA = 1.24
LEAF_ANG = 15.0                  # uszy prawie pionowo: lekki kat 15 st. od pionu na zewnatrz (w duzym modelu leafAng = 50 st.)
LEAF_IN = 2.0                    # uszy o tyle mm blizej siebie niz w duzym modelu (miejsce osadzenia zatwierdzone; przy kacie 15 st. ucho zachodzi na poroze w widoku z przodu w 87%, przy LEAF_IN = -1: 47%)
P = RK.params()                # poroze ANT_K (3 poziomy) i uszy LEAF z duzego modelu


# ---------------------------------------------------------------------------------------------- ramki poroza i uszu na czapce
def z_at_R(rho):
    """z, na ktorym nominalny promien jajka = rho (gorna polowa)"""
    lo, hi = ZM, H_EGG
    for _ in range(60):
        mid = (lo + hi) / 2
        if float(egg_R(mid)) > rho: lo = mid
        else: hi = mid
    return (lo + hi) / 2


def ant_frame(s):
    """poroze: P0 na czapce w x = +-earX, y = Y0 (jak w duzym modelu), odchylenie na zewnatrz earTilt"""
    rho0 = math.hypot(P["earX"], Y0)
    return mount_frame(s, np.array([s * P["earX"], Y0, z_at_R(rho0)]), math.radians(P["earTilt"]), math.radians(P["earPitch"]))


def leaf_frame(s):
    """ucho-lisc: punkt na powierzchni jajka w odleglosci od osi rr = R_glowy sin(leafPos) (jak 'polar 46 st.' glowy), w plaszczyznie srodka ucha
    yc = Y0 + 2,5 - earT - leafGap - leafT/2 (tylna scianka ucha 'leafGap' = 1 mm przed przednia scianka poroza)"""
    T = P["leafT"]
    rr = P["headR"] * math.sin(math.radians(P["leafPos"])) - LEAF_IN
    yc = Y0 + 2.5 - P["earT"] - P["leafGap"] - T / 2.0
    z = z_at_R(rr)
    P0 = np.array([s * math.sqrt(max(rr * rr - yc * yc, 0.0)), yc + T / 2.0 - 2.5, z])
    return mount_frame(s, P0, math.radians(LEAF_ANG), 0.0)


def frame_box(fr, ar, br, cr):
    pts = np.array([fr.O + a * fr.A + b * fr.B + c * fr.C for a in ar for b in br for c in cr])
    return pts.min(0), pts.max(0)


# ---------------------------------------------------------------------------------------------- miseczka
def cav_cup_r(z):
    return np.minimum(egg_R(z) - WALL_CUP, R_CAV)


def cup():
    axes, (X, Y, Z) = make_grid(-(RMAX + 3), RMAX + 3, -(RMAX + 3), RMAX + 3, -2.5 * VOX, ZS + 2.5 * VOX, VOX)
    F = np.minimum(np.minimum(egg_F(X, Y, Z), Z), ZS - Z)
    body = decimate(mesh_from_F(F, axes, VOX), 120000, label="miseczka-obrys")
    solid = trimesh.boolean.union([body, lip_solid()], engine="manifold")
    zt = ZS + LIP_H + 1.0
    zs = np.arange(FLOOR, zt, 0.25)
    pts = [(0.0, FLOOR)] + [(float(cav_cup_r(z)), float(z)) for z in zs] + [(R_CAV, zt), (0.0, zt)]
    return trimesh.boolean.difference([solid, revolve(pts)], engine="manifold")


# ---------------------------------------------------------------------------------------------- czapka
def cap_outer():
    G = antler_geom(P["antLv"], P["antSp"], P["antTine"], P["antAng"], P["antS"])
    A = P["leafW"] / 2 + 2
    lo = np.array([-(RMAX + 3), -(RMAX + 3), 0.0]); hi = np.array([RMAX + 3, RMAX + 3, H_EGG + 2.5])
    for s in (+1, -1):
        for fr, ar, L in ((ant_frame(s), RK.ant_ar(s, P), G["Lc"]), (leaf_frame(s), (-A, A), P["leafL"])):
            l, h = frame_box(fr, ar, (-9, L + 3), (-1, 8))
            lo, hi = np.minimum(lo, l - 2), np.maximum(hi, h + 2)
    axes, (X, Y, Z) = make_grid(lo[0], hi[0], lo[1], hi[1], ZR - 2.5 * VOX, hi[2], VOX)
    F = np.minimum(egg_F(X, Y, Z), Z - ZR)
    for s in (+1, -1):
        fn = part_fn(RK.ant_part(s < 0, P), None, peg=False, plate_b0=-4.5)
        F = add_local(F, axes, ant_frame(s), fn, a_rng=RK.ant_ar(s, P), b_rng=(-9, G["Lc"] + 3), c_rng=(-1, 8))
        fn = part_fn(RK.leaf_part(P), None, peg=False, plate_b0=-4.5)
        F = add_local(F, axes, leaf_frame(s), fn, a_rng=(-A, A), b_rng=(-9, P["leafL"] + 3), c_rng=(-1, 8))
    m = mesh_from_F(F, axes, VOX)
    return decimate(m, 300000, label="czapka-obrys+poroze+uszy")


def clean_slivers(m, min_area=1e-6, label=""):
    """usuwa zdegenerowane trojkaty (powstaja przy ciecach): sciaga najkrotsza krawedz takiego trojkata (scalenie wierzcholkow), potem usuwa
    trojkaty o powtorzonych wierzcholkach; wynik musi byc szczelny i miec te sama objetosc (+-0,01 mm3)"""
    f = m.faces.copy(); V = m.vertices
    for _ in range(5):
        a = 0.5 * np.linalg.norm(np.cross(V[f[:, 1]] - V[f[:, 0]], V[f[:, 2]] - V[f[:, 0]]), axis=1)
        bad = np.where(a < min_area)[0]
        if len(bad) == 0:
            break
        for i in bad:
            t = f[i]
            if len(set(t)) < 3:
                continue
            e = [(np.linalg.norm(V[t[k]] - V[t[(k + 1) % 3]]), t[k], t[(k + 1) % 3]) for k in range(3)]
            _, p, q = min(e)
            f[f == q] = p
        f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])]
    out = trimesh.Trimesh(V, f, process=False)
    out.remove_unreferenced_vertices()
    dv = abs(out.volume - m.volume)
    print(f"  {label}: usunieto {len(m.faces) - len(out.faces)} zdegenerowanych trojkatow, szczelny {out.is_watertight}, zmiana objetosci {dv:.4f} mm3")
    return out if (out.is_watertight and dv < 0.05) else m


def cap(outer, c=CLEAR_WYBRANY):
    rb = R_LIP + c; zg = ZR + BEAD_Z - GAP_Z
    zc1 = ZR + BORE_DEPTH + (rb - R_CAV)
    pts = [(0.0, ZR - 1.0), (rb + 0.5, ZR - 1.0), (rb + 0.5, ZR), (rb, ZR + 0.5), (rb, zg - 1.1), (rb + GROOVE_D, zg - 0.5),
           (rb + GROOVE_D, zg + 0.5), (rb, zg + 1.1), (rb, ZR + BORE_DEPTH), (R_CAV, zc1)]
    for z in np.arange(zc1 + 0.25, CEIL_Z, 0.25):
        pts.append((float(min(R_CAV, egg_R(z) - WALL_CAP_MIN, R_CAV - max(z - Z_A, 0.0) * CONE)), float(z)))
    pts += [(R_TOP, CEIL_Z), (0.0, CEIL_Z)]
    return trimesh.boolean.difference([outer, revolve(pts)], engine="manifold"), pts


# ---------------------------------------------------------------------------------------------- kontrole i podglad
def kontrole(c0, c1):
    inter = trimesh.boolean.intersection([c0, c1], engine="manifold")
    vol = 0.0 if inter is None or len(inter.faces) == 0 else inter.volume
    idx = np.random.default_rng(1).choice(len(c1.vertices), 8000, replace=False)
    d = trimesh.proximity.closest_point(c0, c1.vertices[idx])[1]
    print(f"  zlozone: wspolna objetosc miseczka/czapka {vol:.4f} mm3 (musi byc 0), min. odleglosc {d.min():.3f} mm")
    # jajko niespodzianka 44 x 68 w zlozonej wnece (jak build_egg.py)
    pts_cap = cap_pts_cache
    zz = np.linspace(FLOOR, FLOOR + EGG_H, 400)
    t = np.clip(np.abs(zz - (FLOOR + EGG_H / 2)) / (EGG_H / 2), 0, 1)
    re = (EGG_D / 2) * np.clip(1 - t ** 2.3, 0, None) ** (1 / 2.3)
    cavr = np.interp(zz, [p[1] for p in pts_cap], [p[0] for p in pts_cap], left=-1, right=-1)
    cavr = np.where(zz <= ZS + LIP_H, cav_cup_r(zz), np.maximum(cavr, 0.0))
    print(f"  min. luz jajka 44 x 68 do scian wneki: {(cavr - re).min():.2f} mm; luz nad jajkiem do sufitu: {CEIL_Z - (FLOOR + EGG_H):.1f} mm")
    # odstep ucho-poroze: oba elementy jako osobne bryly (prawa strona), najmniejsza odleglosc miedzy ich powierzchniami
    G = antler_geom(P["antLv"], P["antSp"], P["antTine"], P["antAng"], P["antS"])
    A = P["leafW"] / 2 + 2
    axes, (X, Y, Z) = make_grid(-12.0, 34.0, -12.0, 8.0, 66.0, 132.0, 0.2)
    Fa = np.full(np.broadcast(X, Y, Z).shape, -1.0, np.float32); Fe = Fa.copy()
    Fa = add_local(Fa, axes, ant_frame(+1), part_fn(RK.ant_part(False, P), None, peg=False, plate_b0=-4.5), a_rng=RK.ant_ar(+1, P), b_rng=(-9, G["Lc"] + 3), c_rng=(-1, 8))
    Fe = add_local(Fe, axes, leaf_frame(+1), part_fn(RK.leaf_part(P), None, peg=False, plate_b0=-4.5), a_rng=(-A, A), b_rng=(-9, P["leafL"] + 3), c_rng=(-1, 8))
    ma, me = mesh_from_F(Fa, axes, 0.2), mesh_from_F(Fe, axes, 0.2)
    sub = me.vertices[np.random.default_rng(2).choice(len(me.vertices), min(4000, len(me.vertices)), replace=False)]
    d = trimesh.proximity.closest_point(ma, sub)[1]
    print(f"  ucho-poroze (prawa strona): najmniejszy odstep miedzy bryłami {d.min():.2f} mm (zalozone {P['leafGap']}); ucho y {me.bounds[:, 1].round(2)}, poroze y {ma.bounds[:, 1].round(2)}")
    print(f"  szczyt poroza z = {c1.bounds[1][2]:.1f} mm, najdalszy punkt uch/poroza |x| = {np.abs(c1.bounds[:, 0]).max():.1f} mm")


def podglad(c0, c1):
    from render import render, grid, section_img
    ext = 880 / 135.0; ctr = (0, 62)
    imgs = [render([c0, c1], yaw, 6, 440, 880, ext=ext, center=ctr) for yaw in (0, 40, 90)]
    imgs.append(section_img([c0, c1], 440, 880, ext, ctr))
    grid(imgs, 4).save(os.path.join(HERE, "out", "jajko_renifer.png"))


cap_pts_cache = None


def main():
    global cap_pts_cache
    t0 = time.time()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    print(f"zamek nr 3: luz promieniowy {CLEAR_WYBRANY} mm; poroze {P['antLv']} poziomy (antW {P['antW']}), uszy {P['leafL']} x {P['leafW']} mm, odstep ucho-poroze {P['leafGap']} mm")
    for s in (+1,):
        print(f"  poroze P0 {ant_frame(s).O.round(2)}, ucho P0 {leaf_frame(s).O.round(2)}")
    c0 = cup(); print(f"  miseczka gotowa ({time.time() - t0:.0f} s)")
    co = cap_outer(); print(f"  obrys czapki gotowy ({time.time() - t0:.0f} s)")
    c1, cap_pts_cache = cap(co); print(f"  czapka gotowa ({time.time() - t0:.0f} s)")
    c0 = clean_slivers(c0, label="miseczka"); c1 = clean_slivers(c1, label="czapka")
    kontrole(c0, c1)
    podglad(c0, c1)
    for nm, m, z0 in (("miseczka", c0, 0.0), ("czapka", c1, ZR)):
        m = m.copy(); m.apply_translation([0, 0, -z0])
        out = os.path.join(HERE, "out", f"jajko_renifer_{nm}.stl"); m.export(out)
        print(f"{out}: {len(m.faces):,} tr., szczelny {m.is_watertight}, {m.volume / 1000:.1f} cm3 = {m.volume / 1000 * PLA:.0f} g PLA, wymiary {m.extents.round(1)}")
    print(f"czas {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
