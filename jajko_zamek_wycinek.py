"""Jajko niespodzianka: WYCINEK DO TESTU ZAMKA (miseczka + 3 czapki), prawdziwy obrys jajka 44 x 68 z zebrami wokol szwu.
W odroznieniu od jajko_zamek_proba.py (wolne pierscienie) elementy sa zamkniete jak w jajku, wiec maja jego sztywnosc:
  miseczka: dol ucięty 10 mm pod szwem i zamkniety dnem 2,5 mm; kolnierz 1,5 x 8 mm z wypustka-zatrzaskiem jak w probie;
  czapka 1-3: szew + 11 mm cylindra, potem stozkowy sufit 52 st. (jak w czapce, do r = 5, plaski sufit) i stozkowy 'kapelusz' o sciance 2,6 mm; otwor w dol;
              luz promieniowy 0,10 / 0,15 / 0,20 mm (numer = liczba dolkow na wierzchu), rowek na wypustke, luz osiowy 0,1 mm.
Wspolrzedne jak w jajku (szew ZS = 34); wynik: elementy na plycie, kazdy w pozycji drukowanej (miseczka dnem do stolu, czapka otworem do stolu).
  python3 jajko_zamek_wycinek.py     -> out/jajko_zamek_wycinek.stl (+ out/jajko_zamek_wycinek.png: przekroj zlozonej pary)"""
import os, sys, math
import numpy as np
import trimesh
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import make_grid, mesh_from_F, decimate
from shapes import egg_F, R_CAV, RMAX, ZS
from jajko_zamek_proba import LIP_WALL, LIP_H, BEAD_H, BEAD_Z, GROOVE_D, GAP_Z, CLEARS, BORE_DEPTH, R_LIP

VOX = 0.25                       # siatka obrysu (zebra); zamek jest liczony dokladnie (obrot profilu), nie z siatki
ZB, FLOOR_T = ZS - 10.0, 2.5     # dol wycinka miseczki i grubosc dna
CONE = 1.3                       # |dr/dz| stozka sufitu czapki (52 st. od pionu, STANDARD)
R_TOP, WALL_OFF = 5.0, 4.2       # plaski sufit r = 5; sciana kapelusza 4,2 mm w poziomie = 2,6 mm prostopadle
ZR = ZS + GAP_Z                  # brzeg czapki
Z_A = ZR + 11.0                  # tu zaczyna sie stozek sufitu
Z_C = Z_A + (R_CAV - R_TOP) / CONE
Z_TOP = Z_C + 2.6                # wierzch kapelusza (plaski sufit + 2,6 mm)
PLA = 1.24                       # g/cm3


def revolve(pts, sections=180):                               # cięciwa 2 st.: odchylka 0,004 mm na r = 25
    m = trimesh.creation.revolve(np.array(pts + pts[:1], float), sections=sections)
    m.update_faces(m.nondegenerate_faces()); m.merge_vertices(); m.remove_unreferenced_vertices()
    if m.volume < 0: m.invert()
    return m


def lip_solid():
    zb, zt = ZS + BEAD_Z, ZS + LIP_H
    return revolve([(R_CAV - 2.0, ZS - 0.6), (R_LIP, ZS - 0.6), (R_LIP, zb - 1.0), (R_LIP + BEAD_H, zb - 0.4), (R_LIP + BEAD_H, zb + 0.4),
                    (R_LIP, zb + 1.0), (R_LIP, zt - 0.5), (R_LIP - 0.5, zt), (R_CAV - 2.0, zt)])


def cup():
    axes, (X, Y, Z) = make_grid(-(RMAX + 3), RMAX + 3, -(RMAX + 3), RMAX + 3, ZB - 2.5 * VOX, ZS + 2.5 * VOX, VOX)
    F = np.minimum(np.minimum(egg_F(X, Y, Z), Z - ZB), ZS - Z)
    body = decimate(mesh_from_F(F, axes, VOX), 60000, label='miseczka-obrys')
    solid = trimesh.boolean.union([body, lip_solid()], engine="manifold")
    zf, zt = ZB + FLOOR_T, ZS + LIP_H + 1.0
    cav = revolve([(0.0, zf), (R_CAV, zf), (R_CAV, zt), (0.0, zt)])
    return trimesh.boolean.difference([solid, cav], engine="manifold")


def cap_outer():
    axes, (X, Y, Z) = make_grid(-(RMAX + 3), RMAX + 3, -(RMAX + 3), RMAX + 3, ZR - 2.5 * VOX, Z_TOP + 2.5 * VOX, VOX)
    rho = np.sqrt(X ** 2 + Y ** 2)
    r_hat = np.where(Z < Z_A, 99.0, R_CAV + WALL_OFF - CONE * (Z - Z_A))        # kapelusz: stozek zewnetrzny rownolegly do sufitu
    F = np.minimum(np.minimum(egg_F(X, Y, Z), (r_hat - rho).astype(np.float32)), np.minimum(Z - ZR, Z_TOP - Z))
    return decimate(mesh_from_F(F, axes, VOX), 60000, label='czapka-obrys')


def cap(outer, c, k):
    rb = R_LIP + c; zg = ZR + BEAD_Z - GAP_Z
    zc1 = ZR + BORE_DEPTH + (rb - R_CAV)
    cav = revolve([(0.0, ZR - 1.0), (rb + 0.5, ZR - 1.0), (rb + 0.5, ZR), (rb, ZR + 0.5), (rb, zg - 1.1), (rb + GROOVE_D, zg - 0.5),
                   (rb + GROOVE_D, zg + 0.5), (rb, zg + 1.1), (rb, ZR + BORE_DEPTH), (R_CAV, zc1), (R_CAV, Z_A), (R_TOP, Z_C), (0.0, Z_C)])
    m = trimesh.boolean.difference([outer, cav], engine="manifold")
    dimples = []
    for i in range(k):                                                          # k dolkow o srednicy 1,4 mm, gl. 1 mm na plaskim wierzchu
        d = trimesh.creation.cylinder(radius=0.7, height=2.0, sections=24)
        d.apply_translation([(i - (k - 1) / 2.0) * 2.6, 0, Z_TOP])
        dimples.append(d)
    return trimesh.boolean.difference([m] + dimples, engine="manifold")


def main():
    c0 = cup(); co = cap_outer()
    caps = [cap(co, c, i + 1) for i, c in enumerate(CLEARS)]
    # kontrola zlozenia (wspolrzedne jajka): wspolna objetosc musi byc 0, najmniejszy luz miedzy elementami
    for c, m in zip(CLEARS, caps):
        inter = trimesh.boolean.intersection([c0, m], engine="manifold")
        vol = 0.0 if inter is None or len(inter.faces) == 0 else inter.volume
        idx = np.random.default_rng(1).choice(len(m.vertices), 6000, replace=False)
        d = trimesh.proximity.closest_point(c0, m.vertices[idx])[1]
        print(f"  luz {c:.2f}: wspolna objetosc w pozycji zamknietej {vol:.4f} mm3 (musi byc 0), min. odleglosc czapka-miseczka {d.min():.3f} mm")
    # przekroj zlozonej pary (wersja 2)
    fig, ax = plt.subplots(1, 1, figsize=(5.4, 6.4))
    for m, col in ((c0, "#9cb6d4"), (caps[1], "#e8c9a0")):
        s = m.section(plane_origin=[0.0137, 0.0137, 0], plane_normal=[0, 1, 0])
        for e in s.discrete:
            ax.add_patch(MPoly(e[:, [0, 2]], closed=True, fc=col, ec="k", lw=.6))
    ax.set_xlim(-31, 31); ax.set_ylim(ZB - 1, Z_TOP + 1); ax.set_aspect("equal"); ax.grid(alpha=.3)
    ax.set_title("wycinek zlozony, przekroj y=0 (wersja 2: luz 0,15 mm)", fontsize=9)
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "out", "jajko_zamek_wycinek.png"), dpi=75)
    # plyta: kazdy element w pozycji drukowanej
    pos = [(-33.0, -33.0), (33.0, -33.0), (-33.0, 33.0), (33.0, 33.0)]
    parts = []
    for m, z0, (x, y) in zip([c0] + caps, [ZB, ZR, ZR, ZR], pos):
        m = m.copy(); m.apply_translation([x, y, -z0]); parts.append(m)
    plate = trimesh.util.concatenate(parts)
    out = os.path.join(HERE, "out", "jajko_zamek_wycinek.stl"); plate.export(out)
    print(f"{out}: {len(plate.faces)} trojkatow, wymiary {plate.extents.round(1)}")
    for nm, m in zip(["miseczka"] + [f"czapka {i+1} (luz {c})" for i, c in enumerate(CLEARS)], parts):
        print(f"  {nm}: szczelny {m.is_watertight}, {m.volume/1000:.1f} cm3 = {m.volume/1000*PLA:.0f} g PLA, wymiary {m.extents.round(1)}")
    print(f"  razem {plate.volume/1000*PLA:.0f} g PLA (bez podpor)")


if __name__ == "__main__":
    main()
