"""Jajko niespodzianka: PROBKA LACZENIA dwoch elementow (miseczka + czapka) na sztywny zatrzask.
Pierscienie w skali 1:1 na prawdziwej srednicy szwu jajka 44 x 68 (shapes.R_CAV = 24, RMAX = 28), drukowane tak jak finalne czesci:
  dolny   = pierscien z kolnierzem (wargą) i zatrzaskiem-wypustka na zewnatrz, kolnierzem do gory;
  gorny 1-3 = pierscien z otworem w dol (otworem na stole) i rowkiem na wypustke; trzy luzy promieniowe (1 = najciasniejszy, 3 = najluzniejszy);
              numer = liczba naciec na gornej krawedzi.
Zamyka sie na sztywno: luz osiowy tylko 0,1 mm (czapka siada na ramieniu), wypustka 0,25 mm zatrzaskuje sie w rowku (klik), brak luzu na boki.
  python3 jajko_zamek_proba.py     -> out/jajko_zamek_proba.stl (4 elementy na jednej plycie) + out/jajko_zamek_proba.png (przekroj + uklad)
Parametry na gorze pliku; po probie wybrany luz idzie do shapes.py (LIP_WALL, LIP_H, CLEAR_R, CLEAR_Z) i do build_egg.py."""
import os, sys, math
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely import affinity
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from shapes import R_CAV, RMAX                    # 24,0 i 28,0 mm: wnetrze i najszersze miejsce jajka (tam jest szew)

LIP_WALL, LIP_H = 1.5, 8.0                        # kolnierz: grubosc scianki (dotad 1,2) i wysokosc (dotad 7,0)
BASE_H = 4.0                                      # wysokosc czesci ponizej szwu (ramie, na ktorym siada czapka)
BEAD_H, BEAD_Z = 0.25, 4.5                        # wypustka-zatrzask: wysokosc na zewnatrz; polozenie srodka nad ramieniem
GROOVE_D = 0.30                                   # glebokosc rowka w czapce ponad otwor (rowek ma 0,05 zapasu wzgledem wypustki)
GAP_Z = 0.10                                      # luz osiowy czapka-ramie (dotad 0,2)
CLEARS = (0.10, 0.15, 0.20)                       # luz promieniowy otworu czapki: wersje 1, 2, 3 (dotad 0,25 = luzno)
H_CAP = 12.0                                      # wysokosc probnego pierscienia czapki
BORE_DEPTH = 8.6                                  # gleb. otworu na kolnierz (kolnierz 8,0 + luz 0,1 + zapas)
R_LIP = R_CAV + LIP_WALL


def cup_profile():
    zt = BASE_H + LIP_H; zb = BASE_H + BEAD_Z
    pts = [(R_CAV, 0), (RMAX - 0.4, 0), (RMAX, 0.4), (RMAX, BASE_H), (R_LIP, BASE_H),
           (R_LIP, zb - 1.0), (R_LIP + BEAD_H, zb - 0.4), (R_LIP + BEAD_H, zb + 0.4), (R_LIP, zb + 1.0),
           (R_LIP, zt - 0.5), (R_LIP - 0.5, zt), (R_CAV, zt)]
    return np.array(pts, float)


def cap_profile(c):
    rb = R_LIP + c; zg = BEAD_Z - GAP_Z
    zc = BORE_DEPTH + (rb - R_CAV)                # sufit otworu: stozek 45 st. od otworu do R_CAV
    pts = [(rb + 0.5, 0), (RMAX - 0.4, 0), (RMAX, 0.4), (RMAX, H_CAP), (R_CAV, H_CAP), (R_CAV, zc), (rb, BORE_DEPTH),
           (rb, zg + 1.1), (rb + GROOVE_D, zg + 0.5), (rb + GROOVE_D, zg - 0.5), (rb, zg - 1.1), (rb, 0.5)]
    return np.array(pts, float)


def revolve(pts, sections=360):
    m = trimesh.creation.revolve(np.vstack([pts, pts[:1]]), sections=sections)
    m.merge_vertices()
    if m.volume < 0: m.invert()
    return m


def notches(m, k):
    """k naciec (radialne szczeliny 1,2 x 1,2 mm na gornej krawedzi) = numer wersji"""
    cuts = []
    for i in range(k):
        a = math.radians((i - (k - 1) / 2.0) * 9.0)
        b = trimesh.creation.box([3.2, 1.2, 1.2])
        b.apply_translation([RMAX - 0.8, 0, H_CAP - 0.6])
        b.apply_transform(trimesh.transformations.rotation_matrix(a, [0, 0, 1]))
        cuts.append(b)
    return trimesh.boolean.difference([m] + cuts, engine="manifold")


def closure_check():
    """przekroj (r,z): w pozycji zamknietej nic sie nie nakłada; przy wkladaniu liczy glebokosc wcisku wypustki"""
    cup = Polygon(cup_profile()); out = []
    for c in CLEARS:
        cap = Polygon(cap_profile(c))
        seat = affinity.translate(cap, 0, BASE_H + GAP_Z)
        ov = cup.intersection(seat).area
        worst = 0.0
        for dz in np.arange(BASE_H + GAP_Z, BASE_H + LIP_H + 2, 0.05):    # czapka zjezdza z gory w dol az do siadu
            i = cup.intersection(affinity.translate(cap, 0, dz))
            if not i.is_empty and i.area > 1e-6:
                b = i.bounds; worst = max(worst, b[2] - b[0])
        out.append((c, ov, worst))
    return out


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    cup = revolve(cup_profile())
    caps = [notches(revolve(cap_profile(c)), i + 1) for i, c in enumerate(CLEARS)]
    pos = [(-31.0, -31.0), (31.0, -31.0), (-31.0, 31.0), (31.0, 31.0)]
    parts = []
    for m, (x, y) in zip([cup] + caps, pos):
        m = m.copy(); m.apply_translation([x, y, 0]); parts.append(m)
    plate = trimesh.util.concatenate(parts)
    out = os.path.join(HERE, "out", "jajko_zamek_proba.stl"); plate.export(out)
    print(f"{out}: {len(plate.faces)} trojkatow, wymiary {plate.extents.round(1)}, objetosc {plate.volume/1000:.1f} cm3")
    for name, m in (("dolny", cup),) + tuple((f"gorny {i+1} (luz {c})", m) for i, (c, m) in enumerate(zip(CLEARS, caps))):
        print(f"  {name}: szczelny {m.is_watertight}, objetosc {m.volume/1000:.2f} cm3, wymiary {m.extents.round(1)}")
    for c, ov, worst in closure_check():
        print(f"  luz {c:.2f}: nakladanie w pozycji zamknietej {ov:.4f} mm2 (musi byc 0), max wcisk przy wkladaniu {worst:.2f} mm (wypustka {BEAD_H} - luz = {BEAD_H - c:.2f})")
    # rysunek: przekroje zamknietych par + uklad plyty
    fig, ax = plt.subplots(1, 4, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1, 1, 1, 1.2]})
    cupP = cup_profile()
    for a, c, i in zip(ax[:3], CLEARS, range(3)):
        a.add_patch(MPoly(cupP, closed=True, fc="#9cb6d4", ec="#1d3f6e", lw=1.0))
        a.add_patch(MPoly(cap_profile(c) + [0, BASE_H + GAP_Z], closed=True, fc="#e8c9a0", ec="#7a4a12", lw=1.0))
        a.set_xlim(22.5, 28.8); a.set_ylim(0, 17); a.set_aspect("equal"); a.grid(alpha=.3)
        a.set_title(f"wersja {i+1}: luz {c:.2f} mm (wcisk {BEAD_H - c:.2f})\nniebieski = dolny, bezowy = gorny", fontsize=9)
    a = ax[3]
    a.set_title("uklad na plycie (z gory), nacięcia = numer wersji", fontsize=9)
    for (x, y), lab in zip(pos, ["dolny", "1", "2", "3"]):
        a.add_patch(plt.Circle((x, y), RMAX, fc="#cfd8e3" if lab == "dolny" else "#ecdcc4", ec="k", lw=.8))
        a.add_patch(plt.Circle((x, y), R_CAV, fc="w", ec="k", lw=.5)); a.text(x, y, lab, ha="center", va="center", fontsize=12)
    a.set_xlim(-62, 62); a.set_ylim(-62, 62); a.set_aspect("equal")
    plt.tight_layout(); plt.savefig(os.path.join(HERE, "out", "jajko_zamek_proba.png"), dpi=75)


if __name__ == "__main__":
    main()
