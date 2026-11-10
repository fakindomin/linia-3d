"""NIEAKTUALNE: zastąpione przez czubek_choinkowy.py (zostawione dla historii, nie jest już w build_all.sh).
Gwiazda na czubek choinki: gwiazda pięcioramienna (foremka ma ten sam kształt), grubość 9 mm, na obu płaszczyznach pionowe żebra (jak w linii),
zaokrąglone krawędzie, TULEJA na czubek choinki pod spodem. Druk STOJĄCY (tuleja na stole), bez podpór:
  - gwiazda foremkowa (regularna: wewnętrzny/zewnętrzny = 0,382) ma dolne krawędzie ramion 36° od poziomu = 54° od pionu (STANDARD: <= 55°),
    płaszczyzny gwiazdy i żebra są pionowe; ramiona dolne i tuleja stoją na stole (ramiona spłaszczone o 0,8 mm),
  - w tulei wnęka o średnicy czubka + 0,6 mm (TOP_D, domyślnie 18 mm), głębokość 26 mm, strop stożkowy 52° do płaskiego sufitu r = 5 (10 mm),
  - tuleja ma ścianę min. 1,9 mm w dolinie żebra; nad wnęką zwęża się stożkiem do płyty gwiazdy.
  python3 gwiazda_choinkowa.py [TOP_D]   -> out/gwiazda_choinkowa.stl   (TOP_D = średnica czubka choinki w mm; od 12 do 26)"""
import os, sys, math, time
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely import affinity
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import make_grid, mesh_from_F, decimate, save, RIB_AMP, RIB_PITCH
import choinka_miska as CM
import nawisy

R_STAR = 44.0                    # promień zewnętrzny gwiazdy (po zaokrągleniu czubków ok. 40,6) [mm]
RATIO = 0.382                    # wewnętrzny / zewnętrzny: gwiazda regularna (ramiona dolne 54° od pionu)
T = 9.0                          # grubość płyty (bez żeber) [mm]
R_CONV, R_REFL = 1.5, 2.0        # zaokrąglenia obrysu: czubki / kąty [mm]
R_EDGE = 1.5                     # zaokrąglenie krawędzi płyty [mm]
TOP_D = float(sys.argv[1]) if len(sys.argv) > 1 else 18.0     # średnica czubka choinki [mm]
CLEAR = 0.3                      # luz na stronę [mm]
WALL_T = 2.7                     # ścianka tulei (przed żebrami) [mm]
DEPTH = 26.0                     # głębokość wnęki do początku stożka [mm]
CONE = 1.3                       # |dr/dz| stropu wnęki (52° od pionu, STANDARD)
R_FLAT = 5.0                     # promień płaskiego sufitu [mm]
ROOF = 3.0                       # grubość stropu nad płaskim sufitem [mm]
FOOT = 0.8                       # spłaszczenie dolnych ramion do stołu [mm]
VOX = 0.25
PETG = 1.27


def star_poly():
    pts = [((1.0 if k % 2 == 0 else RATIO) * R_STAR * math.cos(math.radians(90 + 36 * k)),
            (1.0 if k % 2 == 0 else RATIO) * R_STAR * math.sin(math.radians(90 + 36 * k))) for k in range(10)]
    return CM.round_poly(Polygon(pts), R_CONV, R_REFL)


def rib_x(x):
    c = np.cos(2 * math.pi * x / RIB_PITCH)
    return np.sign(c) * np.abs(c) ** 0.8


def build():
    S = star_poly()
    x0, y0, x1, y1 = S.bounds
    z_bot = y0 + FOOT                                         # dolne ramiona i tuleja stoją na stole
    r_h = TOP_D / 2 + CLEAR                                   # promień wnęki
    r_o = r_h + WALL_T                                        # promień tulei (bez żeber)
    z_w = z_bot + DEPTH                                       # koniec cylindra wnęki
    z_c1 = z_w + (r_h - R_FLAT) / CONE                        # koniec stożka stropu = płaski sufit
    z_tt = z_c1 + ROOF                                        # góra walca tulei; wyżej stożek zewnętrzny do płyty
    nR = int(round(2 * math.pi * r_o / RIB_PITCH))
    yh = max(T / 2, r_o) + RIB_AMP + 2.5
    axes, (X, Y, Z) = make_grid(x0 - 3, x1 + 3, -yh, yh, z_bot - 1.0, y1 + 3, VOX)
    xs, zs = axes[0], axes[2]
    Xg, Zg = np.meshgrid(xs, zs, indexing="ij")
    s2 = CM.sdf_poly(S, Xg, Zg, step=0.04)[:, None, :]       # odległość do obrysu gwiazdy (dodatnia w środku), płaszczyzna x-z
    Fy = (T / 2 + RIB_AMP * rib_x(X) - np.abs(Y)).astype(np.float32)          # płyta z żebrami na obu stronach
    F_plate = CM.smin(s2, Fy, CM.k_of(R_EDGE)).astype(np.float32)
    rho = np.sqrt(X ** 2 + Y ** 2).astype(np.float32)
    th = np.arctan2(Y, X)
    cone_o = r_o - CONE * np.clip(Z - z_tt, 0, None)          # nad walcem tulei: stożek zewnętrzny (powierzchnia skierowana w górę)
    fade = np.clip(1.0 - (Z - z_tt) / 4.0, 0.0, 1.0)          # żebra tulei wygaszane nad walcem
    ro_z = cone_o + RIB_AMP * fade * (np.sign(np.cos(nR * th)) * np.abs(np.cos(nR * th)) ** 0.8)
    F_tube = (ro_z - rho).astype(np.float32)
    r_cav = np.where(Z <= z_w, r_h, np.where(Z <= z_c1, r_h - CONE * (Z - z_w), -1.0))
    F_cav = (r_cav - rho).astype(np.float32)
    F = np.minimum(np.maximum(F_plate, F_tube), -F_cav)
    F = np.minimum(F, (Z - z_bot).astype(np.float32)).astype(np.float32)
    m = mesh_from_F(F, axes, VOX)
    m = decimate(m, 250000, label="gwiazda_choinkowa")
    info = dict(z_bot=z_bot, z_tt=z_tt, r_h=r_h, r_o=r_o, nR=nR, z_c1=z_c1, ceil=z_c1 - z_bot)
    return m, info


def main():
    t0 = time.time()
    m, info = build()
    path = save(m, "gwiazda_choinkowa.stl", True, f"druk stojacy (tuleja na stole); tuleja na czubek {TOP_D:g} mm")
    m = trimesh.load(path)
    comps = len(m.split(only_watertight=False))
    print(f"  tuleja: wnęka Ø {2 * info['r_h']:.1f} mm, głęb. do stropu {info['ceil']:.1f} mm (stożek 52° do płaskiego sufitu r = {R_FLAT:g}), tuleja Ø {2 * info['r_o']:.1f} mm, żeber {info['nR']}")
    print(f"  wymiary {m.extents.round(1)} mm, objętość {m.volume / 1000:.1f} cm3 = {m.volume / 1000 * PETG:.0f} g PETG, składowe {comps}")
    ok = m.is_watertight and comps == 1
    for thr in (25.0, 35.0, 45.0):
        r = nawisy.slicer_overhang(m, h=0.2, thr=thr)
        print(f"  nawis wg slicera (próg {thr:.0f}° od poziomu, warstwa 0,2): {r['area']:.1f} mm2, wyspy {r['floating']:.1f} mm2, najszersze niepodparte {r['width']:.1f} mm @ z {r['z']:.1f}")
        if thr == 35.0:
            ok &= r["floating"] < 0.5 and r["width"] <= 12.0
    from lib import splat                                                          # podglad: przod, 3/4, bok (splat; render.py nie radzi sobie z tak duzymi plaskimi trojkatami)
    from render import grid
    grid([splat([m], y, 440, 520, pitch=p, ext_override=95, dot=3).convert("RGB") for y, p in ((0, 6), (40, 14), (90, 6))], 3).save(os.path.join(HERE, "out", "gwiazda_choinkowa.png"))
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
