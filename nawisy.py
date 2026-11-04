"""Nawisy pod druk bez podpor: (1) obciecie pola F od dolu (carve: nic nie wisi w powietrzu), (2) pomiar jak slicer (warstwa po warstwie).
Slicer (Bambu / Orca / Prusa) uznaje za nawis te czesc warstwy, ktora wystaje poza warstwe nizej o wiecej niz h / tg(prog) (prog = kat zbocza od POZIOMU,
w projekcie Dominika support_threshold_angle = 25 st.); wyspa bez niczego pod spodem = 'floating region'.
  carve(F, vox, z, ang)       -> F' (ten sam typ): kazda warstwa wystaje poza warstwe nizej najwyzej o vox*tg(ang); zbocza w dol >= (90 - ang) st. od poziomu, brak lokalnych minimow
  slicer_overhang(m, h, thr)  -> dict: pole nawisu [mm2], pole wysp w powietrzu [mm2], najszersze niepodparte miejsce [mm], z"""
import math
import numpy as np
from scipy import ndimage as ndi


def carve(F, vox, z_axis, ang=55.0, k=0.35, zmin=0.0, verbose=True):
    """Idac warstwami OD DOLU kazda warstwa moze wystawac poza warstwe nizej najwyzej o delta = vox * tg(ang) (ang = kat zbocza od PIONU,
    55 st. -> zbocza w dol >= 35 st. od poziomu): F'[k] = min(F[k], dystans2D(F'[k-1]) + delta). Obcina wszystko, co wisi w powietrzu: srodek brzucha nizej niz boki
    (kil, kropla), koniec pyska nizej niz reszta, kazdy lokalny minimum powierzchni dolnej poza stolem. Pierwsza warstwa (stol) bez zmian."""
    import skfmm
    delta = vox * math.tan(math.radians(ang))
    G = F.copy()
    n = G.shape[2]
    first = None
    removed = 0
    for kz in range(n):
        if z_axis[kz] < zmin or not (G[:, :, kz] > 0).any():
            continue
        if first is None:
            first = kz
            continue
        prev = G[:, :, kz - 1]
        if not (prev > 0).any():
            continue
        D = skfmm.distance(prev, dx=vox)                       # > 0 wewnatrz warstwy nizej
        A = (D + delta).astype(np.float32)                     # dozwolony obszar: warstwa nizej powiekszona o delta
        cur = G[:, :, kz]
        out = np.minimum(cur, A) if k <= 0 else (np.minimum(cur, A) - np.maximum(k - np.abs(cur - A), 0.0) ** 2 / (4.0 * k)).astype(np.float32)
        removed += int(((cur > 0) & ~(out > 0)).sum())
        G[:, :, kz] = out
    if verbose:
        print(f"  obciecie nawisow: usunieto {removed * vox ** 3:.0f} mm3 ({removed} wokseli), zbocza w dol >= {90 - ang:.0f} st. od poziomu")
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
    Zwraca dict(area, floating, width, z): pole nawisu, pole PRAWDZIWYCH wysp (skladowa warstwy bez zadnego styku z warstwa nizej, od z > 0,3 mm), najszersze niepodparte miejsce, jego z"""
    L = _layers(m, h)
    d = h / math.tan(math.radians(thr))
    tot = fl = wmax = zmax = 0.0
    for (z1, a), (_, b) in zip(L[1:], L[:-1]):
        if a is None or b is None or z1 < 0.45:                  # pierwsze warstwy leza na stole (fazka krawedzi stop), nie sa nawisem
            continue
        U = a.difference(b.buffer(d)).buffer(-0.04).buffer(0.04)
        if U.is_empty:
            continue
        if z1 > 0.3:                                              # prawdziwa wyspa = skladowa warstwy, ktora nie dotyka warstwy nizej (lokalne minimum powierzchni dolnej)
            for c in (list(a.geoms) if hasattr(a, "geoms") else [a]):
                if c.area >= min_area and not c.intersects(b):
                    fl += c.area
        for g in (list(U.geoms) if hasattr(U, "geoms") else [U]):
            if g.area < min_area:
                continue
            tot += g.area
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
