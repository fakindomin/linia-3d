"""Krolik 'knitted' z WGRANEGO pliku STL (siedzacy krolik w dzianinie): TA SAMA BRYLA, ale faktura oczek z knit.py zamiast oryginalnej siatki.
Oczy: OSOBNE czesci wciskane (kula + czop), w glowie gniazdo (kieszen pod kule + otwor pod czop, luz --gap na strone) -> dwa pliki STL.
Plik wejsciowy NIE jest czescia repo (cudzy model; sprawdz licencje, jesli miales wydruki sprzedawac): skrypt bierze go jako argument.
Kroki: korpus (najwieksza bryla, uproszczona do ~250 tys. tr.) + plaskie wkladki podeszew (wypelniaja kieszenie pod stopami) -> PLASTRY z = const
(przekroje siatki, wypelnienie parzystosciowe; zamiast trimesh.voxelized, ktore przy skoku 0,2 zjadalo >6 GB RAM) -> pole odleglosci F -> wygladzenie
(gaussian sigma ~0,7 mm zeruje oryginalne oczka) -> plaskie dno -> knit.knit_F (wlasne oczka) -> gniazda oczu -> marching cubes.
Kontrola ksztaltu: odleglosc oryginalnej powierzchni (200 tys. punktow) od nowej (percentyle), wymiary, objetosc; nawisy wg slicera (informacyjnie: ksztalt nie jest zmieniany).
  python3 krolik_knit.py /sciezka/Knitted__Easter_Bunny.stl     -> out/krolik_knit.stl (korpus z gniazdami), out/krolik_knit_oczy.stl (2 oczy do druku) + .png
  python3 krolik_knit.py plik.stl --stitch 3.2 --row 2.6 --amp 0.4 --name krolik_knit_gruby.stl   (grubsze oczka)
  python3 krolik_knit.py plik.stl --peg 2.2 --peglen 2.5 --gap 0.10                              (czop oka: srednica, dlugosc; luz gniazda na strone)"""
import sys, os, time, argparse, resource
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trimesh
from trimesh import intersections
from scipy import ndimage as ndi
from skimage import measure
from lib import mesh_from_F, decimate, save, OUT
import nawisy
import knit

DEFAULT_IN = "/mnt/user-data/uploads/Knitted__Easter_Bunny.stl"


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6      # szczyt RSS [GB]


def load_parts(path):
    """korpus, oczy (srodek, promien), wkladki podeszew; wszystko przesuniete: srodek obrysu korpusu w xy = 0, dno korpusu z = 0"""
    m = trimesh.load(path)
    parts = m.split(only_watertight=False)
    main = max(parts, key=lambda p: len(p.faces))
    shift = -np.array([(main.bounds[0][0] + main.bounds[1][0]) / 2, (main.bounds[0][1] + main.bounds[1][1]) / 2, main.bounds[0][2]])
    eyes, plates = [], []
    for p in parts:
        if p is main or len(p.faces) < 20:
            continue
        e = p.extents
        if e.max() < 6.0 and e.min() > 2.5 and len(p.faces) >= 100:
            eyes.append((p.bounds.mean(0) + shift, float(e.mean() / 2)))
        elif e[2] < 2.0:
            plates.append(p)
    main.apply_translation(shift)
    for p in plates:
        p.apply_translation(shift)
    return main, eyes, plates


def raster_layer(seg, x0, y0, vox, nx, ny):
    """wypelnienie parzystosciowe jednego plastra: seg (n,2,3) odcinki przekroju -> bool (nx, ny); srodek piksela (i, j) = (x0 + i vox, y0 + j vox)"""
    ax, ay, bx, by = seg[:, 0, 0], seg[:, 0, 1], seg[:, 1, 0], seg[:, 1, 1]
    ya, yb = (ay - y0) / vox, (by - y0) / vox
    j0 = np.ceil(np.minimum(ya, yb)).astype(np.int64)
    j1 = np.ceil(np.maximum(ya, yb)).astype(np.int64) - 1       # wiersz j przecina odcinek, gdy min <= j < max
    cnt = np.clip(j1 - j0 + 1, 0, None)
    tot = int(cnt.sum())
    if tot == 0:
        return np.zeros((nx, ny), bool)
    sid = np.repeat(np.arange(len(seg)), cnt)
    j = j0[sid] + np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    t = (j - ya[sid]) / (yb[sid] - ya[sid])
    i = np.ceil(((ax[sid] + t * (bx[sid] - ax[sid])) - x0) / vox).astype(np.int64)   # pierwszy piksel o srodku za krawedzia
    ok = (j >= 0) & (j < ny)
    j, i = j[ok], np.clip(i[ok], 0, nx)
    tog = np.bincount(j * (nx + 1) + i, minlength=ny * (nx + 1)).reshape(ny, nx + 1)
    return ((np.cumsum(tog[:, :nx], axis=1) & 1) > 0).T


def voxelize_slices(parts, x0, y0, z0, vox, shape, eps=0.0137):
    """obrys z plastrow z = z0 + k vox + eps; kazda czesc osobno (suma, nie XOR - wkladki zachodza na korpus)"""
    nx, ny, nz = shape
    occ = np.zeros(shape, bool)
    for m in parts:
        v = np.asarray(m.vertices)[:, 2][np.asarray(m.faces)]
        flo, fhi = v.min(1), v.max(1)
        for k in range(nz):
            z = z0 + k * vox + eps
            if z < m.bounds[0][2] or z > m.bounds[1][2]:
                continue
            idx = np.nonzero((flo <= z) & (fhi >= z))[0]
            if len(idx) == 0:
                continue
            seg = intersections.mesh_plane(m, [0, 0, 1], [0, 0, z], local_faces=idx)
            if len(seg):
                occ[:, :, k] |= raster_layer(np.asarray(seg), x0, y0, vox, nx, ny)
    return occ


def smooth_sdf(parts, vox, sigma, pad=6.0, pad_top=5.0, pad_bot=5.0):
    """plastry -> F (dodatnie w srodku, mm); zwraca osie i F; dno: warstwa z = 0 powielona w dol, potem plaszczyzna z = 0"""
    b = np.array([p.bounds for p in parts])
    lo, hi = b[:, 0].min(0), b[:, 1].max(0)
    x0, y0 = np.floor((lo[0] - pad) / vox) * vox, np.floor((lo[1] - pad) / vox) * vox
    z0 = -np.ceil(pad_bot / vox) * vox                               # z = 0 lezy na wezle siatki
    nx, ny = int(np.ceil((hi[0] + pad - x0) / vox)) + 1, int(np.ceil((hi[1] + pad - y0) / vox)) + 1
    nz = int(np.ceil((hi[2] + pad_top - z0) / vox)) + 1
    axes = [(x0 + vox * np.arange(nx)).astype(np.float32), (y0 + vox * np.arange(ny)).astype(np.float32), (z0 + vox * np.arange(nz)).astype(np.float32)]
    print(f"siatka {nx} x {ny} x {nz} = {nx * ny * nz / 1e6:.1f} mln wokseli", flush=True)
    occ = voxelize_slices(parts, x0, y0, z0, vox, (nx, ny, nz))
    k0 = int(round(-z0 / vox))
    occ[:, :, :k0] = occ[:, :, k0:k0 + 1]
    print(f"plastry gotowe, RSS {rss():.1f} GB", flush=True)
    F = ndi.distance_transform_edt(occ).astype(np.float32)
    F -= 0.5
    dout = ndi.distance_transform_edt(~occ).astype(np.float32)
    F = np.where(occ, F, 0.5 - dout).astype(np.float32) * np.float32(vox)
    del dout
    F = ndi.gaussian_filter(F, sigma / vox).astype(np.float32)
    F = np.minimum(F, axes[2][None, None, :])                        # plaskie dno w z = 0
    return axes, F.astype(np.float32), occ


def eye_fields(dx, dy, dz, n, r, rp, L, flat, gap, ch=0.4):
    """pola (dodatnie w srodku) oka i gniazda w ukladzie glowy; (dx, dy, dz) = punkt - srodek oka (broadcast), n = normalna zewnetrzna (przod oka).
    oko = kula r splaszczona z przodu o flat + czop rp od srodka w glab o r + L (fazka ch na koncu);
    gniazdo = kieszen na kule (r + gap) + otwor na czop (rp + gap) glebokosci r + L + 0,3"""
    nn = dx * n[0] + dy * n[1] + dz * n[2]
    r2 = dx * dx + dy * dy + dz * dz
    rho = np.sqrt(np.maximum(r2 - nn * nn, 0.0))
    a = -nn                                                          # glebokosc w glab glowy od srodka oka
    rr = np.sqrt(r2)
    sph = np.minimum(r - rr, (r - flat) - nn)
    u, w = rp - rho, (r + L) - a
    peg = np.minimum(np.minimum(np.minimum(u, w), (u + w - ch) / np.sqrt(2.0)), a + 0.5)
    eye = np.maximum(sph, peg)
    uh, wh = rp + gap - rho, (r + L + 0.3) - a
    hole = np.minimum(np.minimum(uh, wh), a + 1.0)
    sock = np.maximum((r + gap) - rr, hole)
    return eye, sock


def window(F, axes, vox, c, R):
    sl = []
    for i in range(3):
        a = max(0, int(np.floor((c[i] - R - axes[i][0]) / vox)))
        b = min(len(axes[i]), int(np.ceil((c[i] + R - axes[i][0]) / vox)) + 1)
        sl.append(slice(a, b))
    return tuple(sl)


def eye_normal(F, axes, vox, c, h=1.2):
    """normalna zewnetrzna = -grad F gladkiego pola w srodku oka; zwraca (n, F(c)) - F(c) > 0 = srodek oka jest wewnatrz bryly"""
    def f(p):
        return float(ndi.map_coordinates(F, [[(p[i] - axes[i][0]) / vox] for i in range(3)], order=1)[0])
    g = np.array([f(c + h * e) - f(c - h * e) for e in np.eye(3)])
    return -g / (np.linalg.norm(g) + 1e-12), f(c)


def eye_mesh(c, n, r, rp, L, flat, gap, vox=0.06):
    """siatka oka w ukladzie glowy (marching cubes z pola analitycznego w lokalnym oknie)"""
    R = r + L + 1.0
    ax = [np.arange(-R, R + vox, vox).astype(np.float32) for _ in range(3)]
    dx, dy, dz = ax[0][:, None, None], ax[1][None, :, None], ax[2][None, None, :]
    eye, _ = eye_fields(dx, dy, dz, n, r, rp, L, flat, gap)
    v, f, _, _ = measure.marching_cubes(np.broadcast_to(eye, (len(ax[0]),) * 3).astype(np.float32), level=0.01, spacing=(vox,) * 3, gradient_direction="ascent")   # 0,01 mm w glab: poziom 0 daje krawedzie nieszczelne (pole = max kuli i czopa)
    v = v + np.array([ax[0][0], ax[1][0], ax[2][0]]) + c
    m = trimesh.Trimesh(v, f, process=True)
    m.merge_vertices()
    return m


def print_pose(m, c, n, spacing_x):
    """oko do druku: przod (splaszczenie) na stole, czop w gore; zwraca kopie przesunieta na z = 0 i x = spacing_x"""
    T = trimesh.geometry.align_vectors(n, [0.0, 0.0, -1.0])
    q = m.copy()
    q.apply_translation(-c)
    q.apply_transform(T)
    q.apply_translation([spacing_x - q.bounds[:, 0].mean(), -q.bounds[:, 1].mean(), -q.bounds[0][2]])
    return q


def preview(orig, parts, path):
    import render
    from PIL import Image
    imgs = []
    for ms in (orig, parts):
        c = ms[0].bounds.mean(0)
        for y, p in ((0, 5), (-40, 12), (130, 12)):
            imgs.append(render.render(ms, yaw=y, pitch=p, W=800, H=1000, ext=9.5, center=(c[0], 46)))
    W = Image.new("RGB", (2400, 2000), "white")
    for i, im in enumerate(imgs):
        W.paste(im, (800 * (i % 3), 1000 * (i // 3)))
    W.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp", nargs="?", default=DEFAULT_IN)
    ap.add_argument("--vox", type=float, default=0.2)
    ap.add_argument("--sigma", type=float, default=0.7, help="wygladzenie oryginalnych oczek [mm]")
    ap.add_argument("--stitch", type=float, default=2.6, help="szerokosc oczka p [mm]")
    ap.add_argument("--row", type=float, default=2.2, help="wysokosc rzedu q [mm]")
    ap.add_argument("--amp", type=float, default=0.35, help="wysokosc wypuklosci [mm]")
    ap.add_argument("--peg", type=float, default=2.2, help="srednica czopa oka [mm]")
    ap.add_argument("--peglen", type=float, default=2.5, help="dlugosc czopa za kula [mm]")
    ap.add_argument("--gap", type=float, default=0.10, help="luz gniazda oka na strone [mm] (wciskane: 0,05-0,15)")
    ap.add_argument("--flat", type=float, default=-1.0, help="splaszczenie przodu oka [mm] (-1 = auto: r (1 - cos 35 st.) = bez nawisu > 55 st. na stole)")
    ap.add_argument("--target", type=int, default=900000)
    ap.add_argument("--name", default="krolik_knit.stl")
    ap.add_argument("--noview", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    main_m, eyes, plates = load_parts(a.inp)
    print(f"korpus {len(main_m.faces):,} tr., {main_m.extents.round(1)} mm; oczy: {len(eyes)}, wkladki podeszew: {len(plates)}", flush=True)
    import fast_simplification as fs                                # relief i tak wygladzamy, wiec upraszczamy do ok. 250 tys. tr.
    v, f = fs.simplify(np.asarray(main_m.vertices, np.float32), np.asarray(main_m.faces, np.int32), target_reduction=max(0.0, 1.0 - 250000 / len(main_m.faces)))
    body = trimesh.Trimesh(v, f, process=False)
    print(f"do plastrowania: korpus uproszczony do {len(f):,} tr. ({time.time() - t0:.0f} s)", flush=True)
    axes, F, occ = smooth_sdf([body] + plates, a.vox, a.sigma)
    print(f"gladkie F {F.shape} ({time.time() - t0:.0f} s), objetosc wokseli {occ.sum() * a.vox ** 3 / 1000:.1f} cm3, RSS {rss():.1f} GB", flush=True)
    del occ
    # oczy: polozenie i normalna z gladkiego pola przed faktura
    r_eye = float(np.mean([r for _, r in eyes])) if eyes else 0.0
    rp = min(a.peg / 2, 0.55 * r_eye)
    flat = a.flat if a.flat >= 0 else r_eye * (1 - np.cos(np.radians(35.0)))
    info = []
    for c, r in eyes:
        n, fc = eye_normal(F, axes, a.vox, c)
        info.append((c, n))
        print(f"  oko: srodek {np.round(c, 1)}, r {r:.2f} mm, F(srodka) = {fc:+.2f} mm (>0 = w bryle), normalna {np.round(n, 2)}", flush=True)
    F2 = knit.knit_F(F, axes, a.vox, p=a.stitch, q=a.row, A=a.amp, min_len=2.3 * a.stitch)
    del F
    print(f"faktura gotowa, RSS {rss():.1f} GB", flush=True)
    # gniazda oczu (po fakturze: ciecie bryly polem gniazda)
    for c, n in info:
        R = r_eye + a.peglen + 0.3 + rp + a.gap + 2.0
        sl = window(F2, axes, a.vox, c, R)
        gx = axes[0][sl[0]][:, None, None] - c[0]
        gy = axes[1][sl[1]][None, :, None] - c[1]
        gz = axes[2][sl[2]][None, None, :] - c[2]
        _, sock = eye_fields(gx, gy, gz, n, r_eye, rp, a.peglen, flat, a.gap)
        F2[sl] = np.minimum(F2[sl], -np.broadcast_to(sock, F2[sl].shape).astype(np.float32))
    # ksztalt: odleglosc oryginalnej powierzchni korpusu od nowej (poza oknami gniazd)
    pts, _ = trimesh.sample.sample_surface(main_m, 200000)
    idx = np.stack([(pts[:, i] - axes[i][0]) / a.vox for i in range(3)])
    d = np.abs(ndi.map_coordinates(F2, idx, order=1))
    print(f"ksztalt vs oryginal: odleglosc powierzchni sr. {d.mean():.2f} mm, 95% {np.percentile(d, 95):.2f} mm, 99% {np.percentile(d, 99):.2f} mm, maks. {d.max():.2f} mm", flush=True)
    m = mesh_from_F(F2, axes, a.vox)
    del F2
    m = decimate(m, a.target, label=a.name)
    save(m, a.name, True, f"krolik knitted z pliku: oczka {a.stitch} x {a.row} mm, wypuklosc {a.amp} mm, gniazda na wciskane oczy (czop {2 * rp:.1f} mm, luz {a.gap} mm)")
    m = trimesh.load(os.path.join(OUT, a.name))
    print(f"krolik: {m.extents.round(1)} mm (oryginal {main_m.extents.round(1)}) | V {m.volume / 1000:.1f} cm3 | szczelny {m.is_watertight} ({time.time() - t0:.0f} s, RSS {rss():.1f} GB)", flush=True)
    for thr in (25.0, 30.0):
        o = nawisy.slicer_overhang(m, 0.2, thr)
        print(f"  slicer {thr:.0f} st.: nawis {o['area']:.1f} mm2 | wyspy w powietrzu {o['floating']:.2f} mm2 | najszersze {o['width']:.2f} mm (z = {o['z']:.1f})", flush=True)
    # oczy: osobny plik do druku (przodem do stolu, czop w gore) + pozycja zlozona do podgladu
    placed, plate = [], []
    for k, (c, n) in enumerate(info):
        em = eye_mesh(c, n, r_eye, rp, a.peglen, flat, a.gap)
        placed.append(em)
        plate.append(print_pose(em, c, n, (k - (len(info) - 1) / 2) * (2 * r_eye + 6.0)))
    if plate:
        pe = trimesh.util.concatenate(plate)
        name_e = a.name.replace(".stl", "_oczy.stl")
        save(pe, name_e, True, f"oczy do krolika: kula r {r_eye:.2f} mm splaszczona {flat:.2f} mm, czop {2 * rp:.1f} x {a.peglen} mm, do druku przodem do stolu")
        for k, q in enumerate(plate):
            o = nawisy.slicer_overhang(q, 0.2, 30.0)
            print(f"  oko {k + 1}: {q.extents.round(2)} mm, V {q.volume:.1f} mm3, szczelne {q.is_watertight}, nawis (slicer 30 st.) {o['area']:.2f} mm2, wyspy {o['floating']:.2f} mm2", flush=True)
        print(f"  gniazdo: kieszen r {r_eye + a.gap:.2f} mm, otwor O {2 * (rp + a.gap):.2f} mm (czop O {2 * rp:.2f} mm) x {r_eye + a.peglen + 0.3:.1f} mm od srodka oka", flush=True)
    if not a.noview:
        preview([main_m], [m] + placed, os.path.join(OUT, a.name.replace(".stl", ".png")))
        if plate:
            import render
            ce = pe.bounds.mean(0)
            render.render([pe], yaw=0, pitch=18, W=900, H=500, ext=26, center=(ce[0], pe.extents[2] / 2)).save(os.path.join(OUT, name_e.replace(".stl", ".png")))
    return m


if __name__ == "__main__":
    main()
