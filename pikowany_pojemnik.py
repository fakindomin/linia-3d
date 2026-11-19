"""Pojemnik PIKOWANY (capitonne, 'jak z materialu'): prostokatny kosz z zaokraglonymi narozami, scianki jak poduszki rozdzielone karbami wzdluz
rombowej siatki, w wezlach siatki guziki (male dolki), zwiniety brzeg u gory, dwa otwory na uchwyt w krotkich scianach (ostroluk, zeby nie bylo nawisu).
Wlasna konstrukcja (nie kopia modelu ze zdjecia). Pole F (dodatnie w srodku, w mm) liczone analitycznie, potem obciecie nawisow (nawisy.carve), marching cubes.
Uklad: z = 0 to stol (dno), otwarte u gory, druk bez podpor, PETG, P1S 256 x 256.
  python3 pikowany_pojemnik.py                          -> out/pojemnik_pikowany.stl (+ .png) 200 x 140 x 100 mm
  python3 pikowany_pojemnik.py --len 230 --wid 150 --h 110 --puff 3.5 --tuft 60 --row 40
Wspolrzedne tekstury: s = dlugosc luku wzdluz obrysu (od srodka prawego boku, przeciwnie do wskazowek), z = wysokosc; siatka: guziki co `tuft` mm w rzedzie, rzedy co `row` mm,
co drugi rzad przesuniety o pol rozstawu; liczba guzikow w rzedzie jest calkowita (siatka zamyka sie wokol obwodu)."""
import sys, os, time, argparse, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trimesh
from lib import make_grid, mesh_from_F, decimate, save, OUT
import nawisy


def smin(a, b, k):
    return np.minimum(a, b) - np.maximum(k - np.abs(a - b), 0.0) ** 2 / (4.0 * k)


def sstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def rr_sdf(x, y, hx, hy, r):
    """odleglosc ze znakiem do prostokata o polowkach hx, hy z zaokraglonymi narozami r (ujemna w srodku)"""
    qx, qy = np.abs(x) - (hx - r), np.abs(y) - (hy - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def perim_s(x, y, ax, by, rc):
    """dlugosc luku wzdluz obrysu (prostokat polowek ax + rc, by + rc, naroza rc), od (ax + rc, 0) przeciwnie do wskazowek; zwraca s (0 .. 4Q) i obwod 4Q"""
    Q = by + rc * math.pi / 2 + ax
    X, Y = np.abs(x), np.abs(y)
    dx, dy = X - ax, Y - by
    phi = np.arctan2(np.maximum(dy, 0.0), np.maximum(dx, 0.0))
    s1 = np.where((dx > 0) & (dy > 0), by + rc * phi, np.where(dx > 0, Y, by + rc * math.pi / 2 + (ax - X)))
    s = np.where(x >= 0, np.where(y >= 0, s1, 4 * Q - s1), np.where(y >= 0, 2 * Q - s1, 2 * Q + s1))
    return s, 4 * Q


def puff_field(s, z, per, Ds, Dz, zr0, B, Dn, rn=4.0, gam=0.6, Ap=0.5, Rp=11.0, Np=8):
    """pole faktury h(s, z): okragle poduszki (0 .. B) w rombach rozdzielonych karbami wzdluz siatki rombowej, w wezlach guziki (dolek -Dn) i drobne faldki
    promieniscie wokol guzika (Np faldow, amplituda Ap, zasieg Rp); p = h / B (0 w karbie, 1 w srodku poduszki)"""
    d1 = math.hypot(Ds / 2, Dz)
    sp = Ds * Dz / d1                                              # odstep rownoleglych linii karbow
    ds_, dz_ = s, z - zr0
    f1 = (((Dz * ds_ - (Ds / 2) * dz_) / d1) / sp) % 1.0           # wspolrzedne w romie: 0..1 (romb = kwadrat jednostkowy f1 x f2, wierzcholki = guziki)
    f2 = (((Dz * ds_ + (Ds / 2) * dz_) / d1) / sp) % 1.0
    p = (np.sin(np.pi * f1) * np.sin(np.pi * f2)) ** gam           # kopula poduszki; gam < 1 = pelniejsza, wezszy karb
    ra = np.floor(dz_ / Dz)                                        # najblizszy guzik: dwa rzedy otaczajace z
    r2 = tx = tz = None
    for rr in (ra, ra + 1):
        off = (rr % 2) * (Ds / 2)
        t = np.round((ds_ - off) / Ds) * Ds + off
        dxs, dzs = ds_ - t, dz_ - rr * Dz
        r_ = np.hypot(dxs, dzs)
        if r2 is None:
            r2, tx, tz = r_, dxs, dzs
        else:
            m = r_ < r2
            r2, tx, tz = np.where(m, r_, r2), np.where(m, dxs, tx), np.where(m, dzs, tz)
    dim = Dn * np.exp(-(r2 / rn) ** 2)
    pleat = Ap * (r2 / (r2 + 2.0)) * np.clip(1.0 - r2 / Rp, 0.0, 1.0) ** 2 * np.cos(Np * np.arctan2(tz, tx))
    return B * p - dim + pleat, p


def build_field(L, W, H, rc, B, Bi, tmin, tf, Dn, Ds_t, Dz, vox, slab=16, verbose=True):
    ax, by = L / 2 - rc, W / 2 - rc
    axes, (X, Y, Z) = make_grid(-L / 2 - 2, L / 2 + 2, -W / 2 - 2, W / 2 + 2, -0.6, H + 2.0, vox)
    nx, ny, nz = (len(a) for a in axes)
    xs, ys = axes[0][:, None], axes[1][None, :]
    u = -rr_sdf(xs, ys, L / 2, W / 2, rc)[:, :, None]              # odleglosc do obrysu zewnetrznego (dodatnia w srodku)
    s, per = perim_s(xs, ys, ax, by, rc)
    s = s[:, :, None]
    N = max(6, int(round(per / Ds_t)))
    Ds = per / N
    zr0 = (H - 10) / 2 - Dz / 2                                    # rzedy guzikow wokol polowy uzytecznej wysokosci
    if verbose:
        print(f"  obwod {per:.0f} mm, {N} guzikow w rzedzie (rozstaw {Ds:.1f} mm), rzedy co {Dz:.0f} mm od z = {zr0:.0f}")
    F = np.empty((nx, ny, nz), np.float32)
    for k0 in range(0, nz, slab):
        z = axes[2][None, None, k0:k0 + slab]
        h, p = puff_field(s, z, per, Ds, Dz, zr0, B, Dn)
        win = sstep(z, 2.0, 10.0) * (1.0 - sstep(z, H - 18.0, H - 8.0))
        rim = sstep(z, H - 20.0, H - 10.0)
        q_o = -B + (1.0 - rim) * win * h + rim * B                              # zewnetrzna powierzchnia: q = odleglosc ze znakiem od obrysu L x W
        q_i = -B - tmin - (1.0 - rim) * Bi * win * p - rim * 2.0                # wewnetrzna (zgrubienie do srodka: poduszki i zwiniety brzeg)
        Fo = u + q_o
        Fi = -u - q_i
        Fs = np.minimum(Fo, np.maximum(Fi, tf - z))               # sciana + dno
        F[:, :, k0:k0 + slab] = Fs
    return axes, F


def handle_cut(F, axes, L, H, vox, a=24.0, zc=None, x0=None):
    """otwory na uchwyt w krotkich scianach: 'domek' z ostroluku (boki 40 st. od poziomu), naroza zaokraglone; nad otworem zostaje zwiniety brzeg"""
    from shapely.geometry import Polygon
    import shapely
    from scipy import ndimage as ndi
    zc = H - 36.0 if zc is None else zc
    x0 = L / 2 - 16.0 if x0 is None else x0
    poly = Polygon([(-a, zc - 10), (a, zc - 10), (a, zc + 2), (0, zc + 2 + a * math.tan(math.radians(42))), (-a, zc + 2)]).buffer(-4).buffer(4)
    y, z = axes[1], axes[2]
    Yg, Zg = np.meshgrid(y, z, indexing="ij")
    inside = shapely.contains_xy(poly, Yg, Zg)
    sd = ((ndi.distance_transform_edt(inside) - ndi.distance_transform_edt(~inside)) * vox).astype(np.float32)        # dodatnie w otworze
    cut = np.minimum(sd[None, :, :], np.abs(axes[0])[:, None, None] - x0)
    return np.minimum(F, -cut).astype(np.float32), poly.bounds


def contact_area(m, z=0.1):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return 0.0
    p2, _ = sec.to_2D()
    return float(sum(p.area for p in p2.polygons_full))


def min_wall(m, z0, z1, step=1.0):
    """najcienszy fragment sciany [mm] na poziomach z0..z1 (tam, gdzie przekroj to jeden pierscien: obrys zewnetrzny - wewnetrzny); zwraca (minimum, z)"""
    best = (1e9, 0.0)
    for z in np.arange(z0, z1, step):
        sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        p2, _ = sec.to_2D()
        for pg in p2.polygons_full:
            if len(pg.interiors) == 1:
                d = pg.exterior.distance(pg.interiors[0])
                if d < best[0]:
                    best = (d, float(z))
    return best


def preview(m, path):
    import render
    from PIL import Image
    c = m.bounds.mean(0)
    sc = 2400 / 3 / (max(m.extents[0], m.extents[1]) * 1.25)
    views = [(20, 28), (-35, 30), (90, 55)]
    imgs = [render.render([m], yaw=y, pitch=p, W=800, H=800, ext=sc, center=(c[0], m.extents[2] / 2 + (8 if p > 40 else 0))) for y, p in views]
    W = Image.new("RGB", (2400, 800), "white")
    for i, im in enumerate(imgs):
        W.paste(im, (800 * i, 0))
    W.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--len", type=float, default=200.0)
    ap.add_argument("--wid", type=float, default=140.0)
    ap.add_argument("--h", type=float, default=100.0)
    ap.add_argument("--rad", type=float, default=28.0, help="promien naroza obrysu [mm]")
    ap.add_argument("--puff", type=float, default=3.0, help="wypuklosc poduszek na zewnatrz [mm]")
    ap.add_argument("--puff_in", type=float, default=1.0, help="wypuklosc poduszek do srodka [mm]")
    ap.add_argument("--wall", type=float, default=2.6, help="najcienszy fragment sciany (w karbach) [mm]")
    ap.add_argument("--dimple", type=float, default=1.2, help="glebokosc guzika [mm] (sciana w guziku = wall - dimple >= 1,3)")
    ap.add_argument("--floor", type=float, default=3.0)
    ap.add_argument("--tuft", type=float, default=52.0, help="rozstaw guzikow w rzedzie [mm]")
    ap.add_argument("--row", type=float, default=36.0, help="odstep rzedow guzikow [mm]")
    ap.add_argument("--vox", type=float, default=0.35)
    ap.add_argument("--target", type=int, default=600000)
    ap.add_argument("--name", default="pojemnik_pikowany.stl")
    ap.add_argument("--nohandle", action="store_true")
    ap.add_argument("--noview", action="store_true")
    a = ap.parse_args()
    assert a.wall - a.dimple >= 1.3, "sciana w guziku cienka niz 1,3 mm (pomiar po siatce schodzi ok. 0,02 mm ponizej)"
    t0 = time.time()
    axes, F = build_field(a.len, a.wid, a.h, a.rad, a.puff, a.puff_in, a.wall, a.floor, a.dimple, a.tuft, a.row, a.vox)
    print(f"pole F {F.shape} ({time.time() - t0:.0f} s)")
    top = (a.h - axes[2])[None, None, :].astype(np.float32)
    F = smin(F, top, 4.0)                                          # zaokraglona gorna krawedz (zwiniety brzeg)
    F = smin(F, axes[2][None, None, :].astype(np.float32), 3.0).astype(np.float32)   # stol: plaskie dno, zaokraglona dolna krawedz
    if not a.nohandle:
        F, hb = handle_cut(F, axes, a.len, a.h, a.vox)
        print(f"  otwory uchwytu: y {hb[0]:.0f}..{hb[2]:.0f}, z {hb[1]:.0f}..{hb[3]:.0f} mm ({time.time() - t0:.0f} s)")
    F = nawisy.carve(F, a.vox, axes[2], ang=55.0, zmin=0.0)
    print(f"  po obcieciu nawisow ({time.time() - t0:.0f} s)")
    m = mesh_from_F(F, axes, a.vox)
    del F
    m = decimate(m, a.target, label=a.name)
    save(m, a.name, True, f"pojemnik pikowany {a.len:.0f}x{a.wid:.0f}x{a.h:.0f}, poduszki {a.puff} mm, bez podpor")
    m = trimesh.load(os.path.join(OUT, a.name))
    print(f"pojemnik: {m.extents.round(1)} mm | V {m.volume / 1000:.1f} cm3 (~{m.volume * 1.27 / 1000:.0f} g PETG @100%) | stopy {contact_area(m):.0f} mm2 ({time.time() - t0:.0f} s)")
    for thr in (25.0, 30.0):
        o = nawisy.slicer_overhang(m, 0.2, thr)
        print(f"  slicer {thr:.0f} st.: nawis {o['area']:.1f} mm2 | wyspy w powietrzu {o['floating']:.2f} mm2 | najszersze {o['width']:.2f} mm (z = {o['z']:.1f})")
    d, zd = min_wall(m, 6.0, a.h - 48.0)
    print(f"  najcienszy fragment sciany (z = 6 .. {a.h - 48:.0f} mm): {d:.2f} mm przy z = {zd:.0f} (cel >= 1,2 mm: 3 linie dyszy 0,4)")
    if not a.noview:
        preview(m, os.path.join(OUT, a.name.replace(".stl", ".png")))
    return m


if __name__ == "__main__":
    main()
