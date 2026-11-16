"""TACA: żebrowana taca owalna na renifery żebrowane i drobne elementy (240 x 56 x 30 mm, 3 szt. na stole P1S 256 x 256).
Obrys = superelipsa (wykładnik EXP: 2 = elipsa, 4+ = prawie prostokąt z zaokrąglonymi narożnikami); zewnętrzna ścianka ma pionowe żebra linii
(amplituda ±RIB_AMP = 0,8 mm, rozstaw ok. 3,4 mm wzdłuż obwodu, grzbiet dokładnie na końcach osi, więc wymiary 240 x 56 są mierzone po grzbietach),
wnętrze GŁADKIE (łatwo odkurzyć i wytrzeć, renifery stoją prosto). Całość to wyciągnięcie obrysu w pionie: nic nie wisi, bez podpór.
Druk: dnem do stołu, 3 szt. obok siebie (Y: 3 x 56 + 2 x 8 mm), PETG; dla pewnej przyczepności brim 5 mm (opcjonalnie).
  python3 taca.py                       -> out/taca.stl + out/taca.png (podgląd z reniferami dla skali)
  python3 taca.py --wid 55 --h 30       inne wymiary; --exp 3.2 pełniejsze końce; --name taca_55
Kontrole (kod wyjścia 1 przy błędzie): wymiary po grzbietach, szczelność, 1 składowa, nawis > 55° = 0, ścianka w dolinie żebra >= 0,8 mm,
mieści się N reniferów kręgla (podstawa Ø33, brzuch Ø53 na rancie) z luzem >= 0,5 mm i 3 sztuki na stole."""
import os, sys, math, time, argparse
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import RIB_AMP, RIB_PITCH

# ---- parametry (jedna definicja; Python = źródło prawdy) ----
LENGTH, WIDTH, HEIGHT = 240.0, 57.0, 30.0     # wymiary zewnętrzne po grzbietach żeber [mm]
FLOOR = 2.4                                   # grubość dna [mm]
WALL = 2.0                                    # ścianka od linii środkowej żeber do wnętrza; w dolinie żebra WALL - RIB_AMP = 1,2 mm
EXP = 3.6                                     # wykładnik superelipsy (2 = elipsa; wyższy = pełniejsze końce)
FOOT = ((0.2, 0.30), (0.4, 0.15))             # fazka dolnej krawędzi: (wysokość schodka do [mm], cofnięcie obrysu [mm]); 2 schodki (nic nie wisi)
K_PTS = 20                                    # punktów na jedno żebro
PETG = 1.27                                   # g/cm3
PITCH = 60.0                                  # rozstaw reniferów w rzędzie [mm] (brzuch Ø54,6 + 5 mm)
BED = (256.0, 256.0)                          # stół Bambu Lab P1S [mm]
BED_GAP = 8.0                                 # odstęp między tacami na stole [mm]
# renifer kręgiel (renifer_kregiel.py): promień korpusu od podstawy (z od stołu) i żebra
REINDEER = dict(baseR=16.5, bellyR=26.4, bellyZ=(45.0, 50.0), total_w=54.6, total_h=162.4)
RDZ = [(0, 16.5), (5, 17.6), (10, 18.9), (15, 20.3), (20, 21.7), (25, 23.0), (30, 24.2), (35, 25.2), (40, 26.0), (45, 26.4)]   # r(z) korpusu kręgla (shapes.bunny_profile)


def reindeer_r(z):
    """promień korpusu renifera kręgla na wysokości z od jego podstawy (bez żeber), z RK.BODY: tablica próbek co 5 mm"""
    zs, rs = zip(*RDZ)
    return float(np.interp(z, zs, rs))


# ---------------------------------------------------------------------------------------------- obrys
def superellipse(a, b, n, M=40000):
    t = np.linspace(0, 2 * np.pi, M, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    return np.stack([a * np.sign(c) * np.abs(c) ** (2 / n), b * np.sign(s) * np.abs(s) ** (2 / n)], 1)


def ribbed_outline(length, width, n=EXP, amp=RIB_AMP, pitch=RIB_PITCH):
    """(obrys żebrowany [Nx2], linia środkowa [Mx2], N żeber): linia środkowa = superelipsa o półosiach (L/2 - amp, W/2 - amp);
    żebra = przesunięcie po normalnej o amp·rib(s), rib = sign(cos)|cos|^0,8 (profil linii), N podzielne przez 4 → grzbiet na końcach obu osi"""
    a, b = length / 2 - amp, width / 2 - amp
    fine = superellipse(a, b, n)
    seg = np.linalg.norm(np.roll(fine, -1, 0) - fine, axis=1)
    s_f = np.concatenate([[0], np.cumsum(seg)]); Ltot = s_f[-1]
    N = 4 * max(1, int(round(Ltot / (4 * pitch))))
    M = N * K_PTS
    s_t = np.linspace(0, Ltot, M, endpoint=False)
    closed = np.vstack([fine, fine[:1]])
    P = np.stack([np.interp(s_t, s_f, closed[:, 0]), np.interp(s_t, s_f, closed[:, 1])], 1)
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    Nrm = np.stack([T[:, 1], -T[:, 0]], 1)                              # na zewnątrz (obieg przeciwny do ruchu wskazówek)
    th = 2 * np.pi * s_t / Ltot
    c = np.cos(N * th)
    off = amp * np.sign(c) * np.abs(c) ** 0.8
    return P + Nrm * off[:, None], P, N


def build_outlines(length, width, n=EXP, wall=WALL):
    out, mid, N = ribbed_outline(length, width, n)
    S_out = Polygon(out).buffer(0)
    S_in = Polygon(mid).buffer(-wall, join_style=1, quad_segs=16).simplify(0.01)
    return S_out, S_in, Polygon(mid), N


# ---------------------------------------------------------------------------------------------- bryła
def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, z1 - z0)
    m.apply_translation([0, 0, z0])
    return m


def build(length=LENGTH, width=WIDTH, height=HEIGHT, floor=FLOOR, n=EXP, wall=WALL):
    S_out, S_in, S_mid, N = build_outlines(length, width, n, wall)
    parts, z_prev = [], 0.0
    for z1, inset in FOOT:                                              # dno z fazką: 2 schodki, każdy węższy od wyższego (nie wiszą)
        parts.append(prism(S_out.buffer(-inset, join_style=1, quad_segs=8), z_prev, z1)); z_prev = z1
    parts.append(prism(S_out, z_prev, height))
    body = trimesh.boolean.union(parts, engine="manifold")
    cavity = prism(S_in, floor, height + 1.0)
    m = trimesh.boolean.difference([body, cavity], engine="manifold")
    m.merge_vertices(); m.remove_unreferenced_vertices()
    return m, dict(S_out=S_out, S_in=S_in, S_mid=S_mid, N=N)


# ---------------------------------------------------------------------------------------------- kontrole
def overhang_55(m):
    n = m.face_normals; zc = m.triangles_center[:, 2]
    return float(m.area_faces[(n[:, 2] < -math.sin(math.radians(55))) & (zc > 0.6)].sum())


def reindeer_fit(S_in, floor, height, pitch=None, count=3, clearance_need=0.5):
    """ile luzu (mm) ma renifer kręgiel na rancie ścianki (z = height od stołu tacy): korpus z żebrami do wysokości rantu wpisany w wnętrze tacy.
    Zwraca (luz minimalny dla `count` reniferów rozmieszczonych symetrycznie co `pitch`, pitch)."""
    r_rim = reindeer_r(height - floor) + RIB_AMP
    if pitch is None:
        pitch = PITCH
    xs = (np.arange(count) - (count - 1) / 2) * pitch
    cl = min(S_in.exterior.distance(Point(x, 0)) - r_rim for x in xs if S_in.contains(Point(x, 0)))
    ok = all(S_in.contains(Point(x, 0)) for x in xs)
    return (cl if ok else -1.0), pitch, xs, r_rim


def max_reindeer(S_in, floor, height):
    """największa liczba kręgli w rzędzie (przy rozstawie >= szerokość brzucha + 2 mm), które mieszczą się z luzem >= 0,5 mm"""
    best = 0
    for n in range(1, 7):
        cl, p, xs, r = reindeer_fit(S_in, floor, height, pitch=REINDEER["total_w"] + 2.5, count=n)
        if cl >= 0.5:
            best = n
    return best


def thin_wall(S_out, S_in):
    """minimalna odległość między zewnętrznym (żebrowanym) a wewnętrznym brzegiem [mm] (próbkowanie wnętrza -> zewnętrze)"""
    pts = [Point(x, y) for x, y in np.asarray(S_in.exterior.coords)[::3]]
    return min(S_out.exterior.distance(p) for p in pts)


def bed_layout(length, width, count=3, gap=BED_GAP):
    need_y = count * width + (count - 1) * gap
    return need_y <= BED[1] - 2 * 4.0 and length <= BED[0] - 2 * 4.0, need_y


def preview(S_out, S_in, xs, r_rim, path, title):
    """widok z góry: taca, podstawy reniferów Ø33 (szare), brzuch na rancie (czerwony) i największy brzuch Ø54,6 (niebieski)"""
    fig, a = plt.subplots(1, 1, figsize=(11, 3.2))
    a.fill(*S_out.exterior.xy, fc="#d9c3a1", ec="#6b4a1f", lw=0.6)
    a.fill(*S_in.exterior.xy, fc="#fbf5ea", ec="#6b4a1f", lw=0.6)
    for x in xs:
        a.add_patch(plt.Circle((x, 0), REINDEER["baseR"], fc="#b0b0b0", ec="#444", lw=0.8, alpha=0.9))
        a.add_patch(plt.Circle((x, 0), r_rim, fc="none", ec="#a33", lw=1.0, ls="--"))
        a.add_patch(plt.Circle((x, 0), REINDEER["total_w"] / 2, fc="none", ec="#27a", lw=0.8, ls=":"))
    x0, y0, x1, y1 = S_out.bounds
    a.set_xlim(x0 - 4, x1 + 4); a.set_ylim(y0 - 4, y1 + 4); a.set_aspect("equal"); a.axis("off")
    a.set_title(title + "  |  szary = podstawa renifera Ø33, czerwony = brzuch na rancie, niebieski = brzuch największy Ø54,6", fontsize=8)
    plt.tight_layout(); plt.savefig(path, dpi=80); plt.close(fig)


def render3d(tray, xs, floor, path):
    """podgląd 3D: taca z reniferami kręglami (jeśli out/renifer_kregiel_calosc.stl istnieje; python3 renifer_kregiel.py)"""
    src = os.path.join(HERE, "out", "renifer_kregiel_calosc.stl")
    if not os.path.exists(src):
        return False
    from lib import decimate
    from render import render
    from PIL import Image
    r = decimate(trimesh.load(src), 70000, label="renifer")
    meshes, cols = [tray], [(214, 196, 160)]
    for x in xs:
        c = r.copy(); c.apply_translation([x, 0, floor - r.bounds[0][2]]); meshes.append(c); cols.append((225, 225, 222))
    ims = [render(meshes, yaw, pitch, 1100, 560, ext=3.0, center=(0, 72), colors=cols) for yaw, pitch in ((0, 8), (30, 24))]
    o = Image.new("RGB", (1100, 1120), "white")
    for i, im in enumerate(ims):
        o.paste(im, (0, i * 560))
    o.save(path)
    return True


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--len", type=float, default=LENGTH); ap.add_argument("--wid", type=float, default=WIDTH); ap.add_argument("--h", type=float, default=HEIGHT)
    ap.add_argument("--floor", type=float, default=FLOOR); ap.add_argument("--wall", type=float, default=WALL); ap.add_argument("--exp", type=float, default=EXP)
    ap.add_argument("--name", default="taca")
    a = ap.parse_args(argv)
    t0 = time.time(); os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    m, g = build(a.len, a.wid, a.h, a.floor, a.exp, a.wall)
    from meshclean import clean_degenerate                              # STANDARD: zwiń mikro-trójkąty przed zapisem
    m, ci = clean_degenerate(m)
    path = os.path.join(HERE, "out", a.name + ".stl"); m.export(path)
    r = trimesh.load(path, process=True)
    comps = len(r.split(only_watertight=False))
    e = r.extents
    oh = overhang_55(r)
    tw = thin_wall(g["S_out"], g["S_in"])
    cl3, p3, xs3, r_rim = reindeer_fit(g["S_in"], a.floor, a.h, count=3)
    nmax = max_reindeer(g["S_in"], a.floor, a.h)
    bed_ok, need_y = bed_layout(e[0], e[1])
    cav_ml = (g["S_in"].area * (a.h - a.floor)) / 1000.0
    checks = [
        ("wymiary po grzbietach", abs(e[0] - a.len) < 0.05 and abs(e[1] - a.wid) < 0.05 and abs(e[2] - a.h) < 0.05),
        ("szczelna, 1 składowa", r.is_watertight and comps == 1 and r.volume > 0),
        ("nawis > 55° = 0", oh < 1.0),
        ("ścianka w dolinie żebra >= 0,8 mm", tw >= 0.8),
        ("3 renifery kręgle z luzem >= 0,5 mm na rancie", cl3 >= 0.5),
        ("3 tace na stole 256 x 256", bed_ok),
    ]
    print(f"{a.name}.stl: {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm | N żeber {g['N']} | tr. {len(r.faces):,} | {r.volume / 1000:.1f} cm3 = {r.volume / 1000 * PETG:.0f} g PETG | wnęka {cav_ml:.0f} ml")
    print(f"  ścianka w dolinie {tw:.2f} mm | korpus kręgla na rancie Ø{2 * r_rim:.1f} (z żebrami), luz do ścianki przy 3 reniferach co {p3:.0f} mm: {cl3:.2f} mm | "
          f"w rzędzie mieści się do {nmax} kręgli (rozstaw >= {REINDEER['total_w'] + 2.5:.0f} mm) | na stole: 3 tace = {need_y:.0f} mm w Y")
    for nme, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {nme}")
    preview(g["S_out"], g["S_in"], xs3, r_rim, os.path.join(HERE, "out", a.name + ".png"), f"{a.name}: {e[0]:.0f} x {e[1]:.0f} x {e[2]:.0f} mm")
    if render3d(r, xs3, a.floor, os.path.join(HERE, "out", a.name + "_3d.png")):
        print(f"  podgląd 3D: out/{a.name}_3d.png")
    ok = all(c[1] for c in checks)
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
