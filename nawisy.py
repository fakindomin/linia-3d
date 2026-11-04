"""Nawisy pod druk bez podpor: (1) naprawa pola F (wypelnienie klinem pod plaskimi stropami), (2) pomiar jak slicer (warstwa po warstwie).
Slicer (Bambu / Orca / Prusa) uznaje za nawis te czesc warstwy, ktora wystaje poza warstwe nizej o wiecej niz h / tg(prog) (prog = kat zbocza od POZIOMU,
w projekcie Dominika support_threshold_angle = 25 st.); wyspa bez niczego pod spodem = 'floating region'.
  repair(F, vox, z0, ang)     -> F' (ten sam typ), po naprawie kazde zbocze skierowane w dol jest >= (90 - ang) st. od poziomu
  slicer_overhang(m, h, thr)  -> dict: pole nawisu [mm2], pole wysp w powietrzu [mm2], najszersze niepodparte miejsce [mm], z"""
import math
import numpy as np
from scipy import ndimage as ndi


def smax(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.maximum(a, b) + h * h * k * 0.25


def repair(F, vox, z_axis, ang=50.0, k=1.0, zmin=0.0, verbose=True):
    """Naprawa nawisow w polu F (dodatnie wewnatrz, siatka vox, os z = ostatni indeks, z_axis = wspolrzedne z wezlow [mm]).
    Idziemy warstwami z gory na dol: warstwa k musi zawierac warstwe k+1 cofnieta o delta = vox * tg(ang) (ang = kat zbocza od PIONU, 50 st. -> zbocza >= 40 st. od poziomu).
    Odleglosc 2D ze znakiem z podpikselowa dokladnoscia (fast marching). Wypelnienie wchodzi do F przez gladkie maksimum (promien ~k mm)."""
    import skfmm
    delta = vox * math.tan(math.radians(ang))
    G = F.copy()
    n = G.shape[2]
    top = n - 1
    while top > 0 and not (G[:, :, top] > 0).any():
        top -= 1
    added = 0
    for kz in range(top - 1, -1, -1):
        if z_axis[kz] < zmin:
            break
        up = G[:, :, kz + 1]
        if not (up > 0).any() or (up > 0).all():
            continue
        # F ma 0 na powierzchni, wiec zamieniamy na pole ze znakiem 'prawie odleglosc' (F jest ~odlegloscia w mm, wiec dla 2D bierzemy skfmm)
        D = skfmm.distance(up, dx=vox)
        C = D - delta
        lo = G[:, :, kz]
        new = smax(lo, C.astype(np.float32), k)
        sel = C > -k                                               # tylko blisko wypelnienia, reszta bez zmian
        out = np.where(sel, new, lo).astype(np.float32)
        added += int(((out > 0) & ~(lo > 0)).sum())
        G[:, :, kz] = out
    if verbose:
        print(f"  naprawa nawisow: dodano {added * vox ** 3:.0f} mm3 ({added} wokseli), zbocza >= {90 - ang:.0f} st. od poziomu")
    return G


def _layers(m, h):
    from shapely.geometry import Polygon
    z0 = m.bounds[0][2]
    hs = z0 + 0.05 + np.arange(0, int((m.extents[2] - 0.1) / h) + 1) * h
    secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=hs)
    L = []
    for z, sc in zip(hs, secs):
        u = None
        if sc is not None:
            for q in sorted([Polygon(p).buffer(0) for p in sc.discrete if len(p) >= 4], key=lambda q: -q.area):
                u = q if u is None else (u.difference(q) if u.contains(q) else u.union(q))
        L.append((z - z0, u))
    return L


def slicer_overhang(m, h=0.2, thr=25.0, min_area=0.3):
    """thr = prog zbocza od POZIOMU [st.]: nawisem jest czesc warstwy poza warstwa nizej powiekszona o h / tg(thr).
    Zwraca dict(area, floating, width, z): pole nawisu, pole wysp bez niczego pod spodem (od z > 0,3 mm), najszersze niepodparte miejsce, jego z"""
    L = _layers(m, h)
    d = h / math.tan(math.radians(thr))
    tot = fl = wmax = zmax = 0.0
    for (z1, a), (_, b) in zip(L[1:], L[:-1]):
        if a is None or b is None:
            continue
        U = a.difference(b.buffer(d)).buffer(-0.04).buffer(0.04)
        if U.is_empty:
            continue
        for g in (list(U.geoms) if hasattr(U, "geoms") else [U]):
            if g.area < min_area:
                continue
            tot += g.area
            if not g.buffer(0.01).intersects(b) and z1 > 0.3:
                fl += g.area
            lo, hi = 0.0, 40.0
            for _ in range(14):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if not g.buffer(-mid).is_empty else (lo, mid)
            if 2 * lo > wmax:
                wmax, zmax = 2 * lo, z1
    return dict(area=tot, floating=fl, width=wmax, z=zmax)


if __name__ == "__main__":
    import sys, trimesh
    for f in sys.argv[1:]:
        m = trimesh.load(f)
        row = []
        for thr in (25, 30, 35, 40):
            r = slicer_overhang(m, 0.2, thr)
            row.append(f"{thr}st: {r['area']:.0f} mm2 (wyspy {r['floating']:.1f}, szer {r['width']:.1f} @z{r['z']:.1f})")
        print(f"{f.split('/')[-1]:28s} " + " | ".join(row))
