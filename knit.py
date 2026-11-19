"""Faktura dzianiny (oczka 'V', jak lewe oczka na drutach) nalozona na dowolna powierzchnie z pola F (dodatnie w srodku, ~ odleglosc w mm).

Zamiast pionowych zeber (lib.ribbed_F) powierzchnia dostaje RZEDY OCZEK:
  1. srodki oczek: przekroje F = 0 plaszczyznami z = const (rzedy poziome, tam gdzie sciana jest raczej pionowa) i x = const (gora grzbietu, czubek glowy);
     kazda petla przekroju dzielona na calkowita liczbe oczek (wspolny punkt startu -> kolumny oczek ukladaja sie pionowo, jak w dzianinie lewej),
  2. oczko = dwie ukosne nitki '\\/' (odcinki od (+-p/2, +q/2) do (0, -q/2) w ukladzie rzedu), profil nitki h = A (1 - (d/w)^2)^2,
  3. F' = F + m (h - A/2): wypuklosc A (0,5 mm) na plaszczu, bez pogrubiania stopy i bez nawisow na stropach (m = 0 gdy powierzchnia patrzy w dol).
Dane dla dyszy 0,4: nitka >= 1,2 mm szerokosci, wypuklosc <= 0,5 mm, nachylenie boku nitki <= ok. 45 st. od pionu (< 55 st. standardu)."""
import numpy as np
from scipy.spatial import cKDTree
from skimage import measure


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _loops(F, axes, vox, fam, q, p, min_len):
    """srodki oczek z przekrojow: fam = 'z' (plaszczyzny z = const, start w punkcie max x) lub 'x' (plaszczyzny x = const, start w punkcie max z);
    zwraca C (N,3) srodki, T (N,3) styczne (jednostkowe), PW (N,) szerokosc oczka p' = L / n, ROW (N,) numer rzedu, qq = rzeczywisty odstep rzedow"""
    ax = 2 if fam == "z" else 0
    a0 = float(axes[ax][0])
    step = max(2, int(round(q / vox)))                  # rzedy w rownych odstepach, q = step * vox
    qq = step * vox
    n_ax = F.shape[ax]
    j0 = int(np.floor(float(axes[ax][0]) / qq)) - 1
    j1 = int(np.ceil(float(axes[ax][-1]) / qq)) + 1
    C, T, PW, ROW = [], [], [], []
    for j in range(j0, j1 + 1):
        pos = (j + 0.5) * qq
        k = int(round((pos - a0) / vox))
        if k < 1 or k > n_ax - 2:
            continue
        S = F[:, :, k] if fam == "z" else F[k, :, :]
        if S.max() <= 0:
            continue
        pk = a0 + k * vox
        for c in measure.find_contours(S, 0.0):
            if len(c) < 8 or np.hypot(*(c[0] - c[-1])) > 1e-3:
                continue                                 # tylko petle zamkniete
            if fam == "z":
                u = float(axes[0][0]) + c[:, 0] * vox
                v = float(axes[1][0]) + c[:, 1] * vox
                key = u                                  # start: max x (przod)
            else:
                u = float(axes[1][0]) + c[:, 0] * vox
                v = float(axes[2][0]) + c[:, 1] * vox
                key = v                                  # start: max z (gora)
            L = float(np.hypot(np.diff(u), np.diff(v)).sum())
            if L < min_len:
                continue
            area = 0.5 * float(np.sum(u[:-1] * v[1:] - u[1:] * v[:-1]))
            if area < 0:                                 # zawsze przeciwnie do ruchu wskazowek
                u, v, key = u[::-1], v[::-1], key[::-1]
            u, v, key = u[:-1], v[:-1], key[:-1]
            i0 = int(np.argmax(key))
            u, v = np.roll(u, -i0), np.roll(v, -i0)
            u, v = np.append(u, u[0]), np.append(v, v[0])
            s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(u), np.diff(v)))])
            n = max(3, int(round(L / p)))
            st = np.arange(n) * (s[-1] / n)
            uu, vv = np.interp(st, s, u), np.interp(st, s, v)
            e = min(0.6, s[-1] / (4 * n))                # styczna: roznica centralna po dlugosci luku (z zawinieciem)
            u1, v1 = np.interp((st + e) % s[-1], s, u), np.interp((st + e) % s[-1], s, v)
            u2, v2 = np.interp((st - e) % s[-1], s, u), np.interp((st - e) % s[-1], s, v)
            tu, tv = u1 - u2, v1 - v2
            nn = np.hypot(tu, tv) + 1e-12
            tu, tv = tu / nn, tv / nn
            if fam == "z":
                C.append(np.stack([uu, vv, np.full(n, pk)], 1))
                T.append(np.stack([tu, tv, np.zeros(n)], 1))
            else:
                C.append(np.stack([np.full(n, pk), uu, vv], 1))
                T.append(np.stack([np.zeros(n), tu, tv], 1))
            PW.append(np.full(n, s[-1] / n))
            ROW.append(np.full(n, j))
    if not C:
        return None
    return (np.concatenate(C).astype(np.float32), np.concatenate(T).astype(np.float32), np.concatenate(PW).astype(np.float32),
            np.concatenate(ROW), qq)


def _height(P, tree, C, T, PW, vdir, q, A, w, leg=(0.5, 0.5, 0.5), k=8):
    """wysokosc faktury h [0, A] w punktach P (M,3) od k najblizszych oczek"""
    d, ix = tree.query(P, k=k)
    h = np.zeros(len(P), np.float32)
    for j in range(k):
        c = C[ix[:, j]]
        r = P - c
        u = np.abs((r * T[ix[:, j]]).sum(1))              # symetria lewa/prawa nitka
        v = r @ vdir
        pw = PW[ix[:, j]]
        ea = leg[0] * pw                                  # nitka od (0, -leg[1] q) do (leg[0] pw, +leg[2] q)
        eb = (leg[1] + leg[2]) * q
        vb = v + leg[1] * q
        tt = np.clip((u * ea + vb * eb) / (ea * ea + eb * eb), 0.0, 1.0)
        da, db = u - tt * ea, vb - tt * eb
        dd = np.hypot(da, db)
        h = np.maximum(h, (np.clip(1.0 - (dd / w) ** 2, 0.0, 1.0) ** 2).astype(np.float32))
    return h * A


def knit_F(F, axes, vox, p=4.0, q=3.2, A=0.5, wf=0.72, z_floor=1.0, nz_fade=(-0.42, -0.09), band=2.2, nz_x=(0.62, 0.72),
           min_len=7.0, chunk=400000, verbose=True, mask_extra=None, leg=(0.38, 0.62, 0.72), renorm=False):
    """F -> F' z faktura dzianiny. p = szerokosc oczka, q = wysokosc rzedu [mm], A = wysokosc wypuklosci, wf = pol-szerokosc nitki jako ulamek odstepu nitek,
    z_floor = ponizej tej wysokosci (mm) gladko (stopy plasko na stole), nz_fade = (n_z, gdzie amplituda = 0; n_z, gdzie = pelna) dla normalnej zewnetrznej (stropy w dol),
    nz_x = zakres |n_z|, w ktorym rzedy przechodza z poziomych (z) na pionowe (x, czubek glowy i grzbiet); mask_extra(P, n) -> maska 0..1 (opcjonalnie),
    leg = (u_gora/p, v_dol/q, v_gora/q): ksztalt oczka 'V' (czubek na (0, -v_dol q), konce nitek na (+-u_gora p, +v_gora q)),
    renorm = True dla pol, ktore nie sa odlegloscia (np. promien profilu minus rho: |grad F| > 1 na skosach): przesuniecie liczone w prawdziwych mm"""
    import time
    t0 = time.time()
    x, y, z = axes
    idx = np.nonzero(np.abs(F) < band * (1.6 if renorm else 1.0))
    ii, jj, kk = (a.astype(np.int32) for a in idx)
    del idx
    M = len(ii)
    if verbose:
        print(f"  faktura: {M:,} wokseli w pasie |F| < {band} mm ({time.time() - t0:.0f} s)")
    P = np.stack([x[ii], y[jj], z[kk]], 1).astype(np.float32)
    nx, ny, nzv = F.shape                                    # normalna zewnetrzna = -grad F
    i1, i0 = np.minimum(ii + 1, nx - 1), np.maximum(ii - 1, 0)
    j1, j0 = np.minimum(jj + 1, ny - 1), np.maximum(jj - 1, 0)
    k1, k0 = np.minimum(kk + 1, nzv - 1), np.maximum(kk - 1, 0)
    N = np.stack([-(F[i1, jj, kk] - F[i0, jj, kk]), -(F[ii, j1, kk] - F[ii, j0, kk]), -(F[ii, jj, k1] - F[ii, jj, k0])], 1).astype(np.float32)
    gm = np.linalg.norm(N, axis=1) / (2.0 * vox)            # |grad F| (1 dla pola odleglosci)
    N /= (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
    del i1, i0, j1, j0, k1, k0
    Fb = F[ii, jj, kk]
    gm = np.clip(gm, 0.5, 3.0).astype(np.float32) if renorm else np.ones(M, np.float32)
    fam = {}                                                 # srodki oczek z dwoch rodzin rzedow
    for f in ("z", "x"):
        r = _loops(F, axes, vox, f, q, p, min_len)
        if r is None:
            continue
        C, T, PW, ROW, qq = r
        fam[f] = (C, T, PW, cKDTree(C), qq)
        if verbose:
            print(f"  rodzina {f}: {len(C):,} oczek w {len(np.unique(ROW))} rzedach (q = {qq:.2f} mm, p ~ {PW.mean():.2f} mm) ({time.time() - t0:.0f} s)")
    anz = np.abs(N[:, 2])
    wx = _smooth(anz, nz_x[0], nz_x[1])
    wz = 1.0 - wx
    h = np.zeros(M, np.float32)
    for f, vdir in (("z", np.array([0.0, 0.0, 1.0], np.float32)), ("x", np.array([1.0, 0.0, 0.0], np.float32))):
        if f not in fam:
            continue
        C, T, PW, tree, qq = fam[f]
        wf_ = wz if f == "z" else wx
        sel = np.nonzero(wf_ > 0.02)[0]
        w = wf * qq * (p / 2) / np.hypot(p / 2, qq)         # pol-szerokosc nitki ~ ulamek odstepu rownoleglych nitek
        for s in range(0, len(sel), chunk):
            b = sel[s:s + chunk]
            hb = _height(P[b], tree, C, T, PW, vdir, qq, A, w, leg)
            h[b] = np.maximum(h[b], hb * wf_[b])
    m = _smooth(N[:, 2], nz_fade[0], nz_fade[1])             # n_z < -0.42 (zbocza w dol) -> bez faktury
    m = m * _smooth(P[:, 2], z_floor * 0.6, z_floor * 2.0)   # przy stole gladko
    if mask_extra is not None:
        m = m * mask_extra(P, N)
    win = 1.0 - _smooth(np.abs(Fb) / gm, band - 1.0, band)   # okno: przesuniecie gasnie na brzegu pasa (odleglosc = F / |grad F|)
    F2 = F.copy()
    F2[ii, jj, kk] = Fb + (win * m * (h - A / 2) * gm).astype(np.float32)
    if verbose:
        print(f"  faktura nalozona ({time.time() - t0:.0f} s), sr. h w pasie {h.mean():.3f} mm")
    return F2
