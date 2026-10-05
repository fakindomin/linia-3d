"""Grupa B - narzedzia do bryl obrotowych: profile (PCHIP), zebra pasmowe z plynnymi przejsciami, wnetrza,
kontrola nawisow profilu, zapis. Wymiary w mm; z = 0 to stol (plaska podstawa)."""
import sys, math, time
import numpy as np
from scipy.interpolate import PchipInterpolator
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *

SLOPE_MAX = 1.0 / math.tan(math.radians(35.0))     # 1,428: maks. |dr/dz| powierzchni zwroconej w dol (nawis 55 st. od pionu)


def sstep(z, z0, z1):
    t = np.clip((z - z0) / (z1 - z0), 0, 1)
    return t * t * (3 - 2 * t)


def rib(N, th):
    c = np.cos(N * th)
    return np.sign(c) * np.abs(c) ** 0.8


class Prof:
    """profil obrotowy r(z): punkty (z, r) -> PCHIP (bez przeregulowan); poza [z0, z1] wartosc brzegowa"""

    def __init__(self, pts, ds=0.05):
        P = np.array(sorted(pts), float)
        assert np.all(np.diff(P[:, 0]) > 0), "z musi rosnac scisle"
        self.z0, self.z1 = float(P[0, 0]), float(P[-1, 0])
        zz = np.linspace(self.z0, self.z1, int((self.z1 - self.z0) / ds) + 1)
        self.zt = zz
        self.rt = PchipInterpolator(P[:, 0], P[:, 1])(zz).astype(np.float32)

    def __call__(self, z):
        z = np.asarray(z, np.float32)
        return np.interp(z, self.zt, self.rt).astype(np.float32)      # poza zakresem: wartosc brzegowa (ciecie robia plaszczyzny)

    def d(self, z):
        return np.gradient(np.interp(z, self.zt, self.rt), z)


def arc_pts(zc, rc, rad, a0, a1, n=7):
    """punkty luku (z, r): srodek (zc, rc), katy w stopniach (0 = +r, 90 = +z)"""
    out = []
    for a in np.linspace(math.radians(a0), math.radians(a1), n):
        out.append((zc + rad * math.sin(a), rc + rad * math.cos(a)))
    return out


def with_top_fillet(pts, f=1.0, n=8):
    """zaokragla gorna krawedz zewnetrzna: ostatni punkt (ztop, r) -> luk o promieniu f (koniec: (ztop, r-f))"""
    zt, r = pts[-1]
    keep = [p for p in pts[:-1] if p[0] < zt - f - 0.25]
    return keep + [(zt - f, r)] + arc_pts(zt - f, r - f, f, 0, 90, n)[1:]


def rib_field(th, Z, Ns, trans=(), quiet=(), edge=2.5):
    """zebra o liczbach Ns[k] w pasach rozdzielonych plynnymi przejsciami trans=[(za,zb),...] (rosnaco);
    quiet=[(za,zb)]: gladkie pasy (amplituda -> 0 na brzegach ~'edge' mm)"""
    ws, w_prev = [], 1.0
    for za, zb in trans:
        s = sstep(Z, za, zb)
        ws.append(w_prev * (1 - s))
        w_prev = w_prev * s
    ws.append(w_prev)
    out = 0
    for w, N in zip(ws, Ns):
        out = out + w * rib(N, th)
    for za, zb in quiet:
        out = out * (1 - sstep(Z, za - edge, za) * (1 - sstep(Z, zb, zb + edge)))
    return out


def rev_F(X, Y, Z, R, Ns, trans=(), quiet=(), zlo=0.0, zhi=None, amp=RIB_AMP, r0=4.0, r1=10.0):
    """bryla obrotowa ze zebrami: promien R(z) + amp*rib; przyciecie plaszczyznami z=zlo, z=zhi"""
    rho = np.sqrt(X ** 2 + Y ** 2)
    th = np.arctan2(Y, X)
    Rz = R(Z)
    mod = rib_amp(Rz, amp, r0, r1) * rib_field(th, Z, Ns, trans, quiet)
    F = (Rz + mod - 1e-3) - rho
    zhi = R.z1 if zhi is None else zhi
    return np.minimum(np.minimum(F, Z - zlo), zhi - Z).astype(np.float32)


def cav_F(X, Y, Z, Rin, zf):
    """wneka (dodatnie w srodku): promien Rin(z), dno plaskie w z = zf; wneka otwarta u gory (Rin okresla gore)"""
    rho = np.sqrt(X ** 2 + Y ** 2)
    return np.minimum(Rin(Z) - rho, Z - zf).astype(np.float32)


def offset_in(R, t, zf=None, ztop=None, n_ext=0.0):
    """promien wnetrza: normalna grubosc scianki t (poziomo t*sqrt(1+R'^2)); zakres [zf, ztop + n_ext]"""
    zf = R.z0 if zf is None else zf
    ztop = R.z1 if ztop is None else ztop
    z = np.linspace(zf, ztop + n_ext, int((ztop + n_ext - zf) / 0.25) + 1)
    r = R(np.minimum(z, R.z1))
    dr = np.gradient(r, z)
    rin = r - t * np.sqrt(1 + dr ** 2)
    return Prof(list(zip(z, rin)))


def check_profile(Rout, Rin=None, label="", flat_max=4.0):
    """nawisy profilu: powierzchnia zwrocona w dol bardziej niz 55 st. od pionu (|dr/dz| > 1,428)"""
    z = np.arange(Rout.z0 + 0.1, Rout.z1 - 0.1, 0.05)
    bad = []
    d = Rout.d(z)
    m = d > SLOPE_MAX                      # r rosnie z z: powierzchnia zewn. patrzy w dol
    bad += _ranges(z, m, "zewn.")
    if Rin is not None:
        zi = np.arange(Rin.z0 + 0.3, Rin.z1 - 0.3, 0.05)
        di = Rin.d(zi)
        bad += _ranges(zi, di < -SLOPE_MAX, "wneka (sufit)")
    ok = not bad
    print(f"  profil {label}: " + ("OK (|dr/dz| <= 1,43 wszedzie)" if ok else "NAWIS " + "; ".join(bad)))
    return ok


def _ranges(z, m, what):
    out = []
    if not m.any():
        return out
    idx = np.where(m)[0]
    start = idx[0]
    prev = idx[0]
    for i in list(idx[1:]) + [None]:
        if i is None or i != prev + 1:
            out.append(f"{what} z={z[start]:.1f}..{z[prev]:.1f}")
            if i is not None:
                start = i
        if i is not None:
            prev = i
    return out


def rev_grid(rmax, zhi, vox, zlo=-1.0, pad=2.5, rmax_y=None):
    ry = rmax if rmax_y is None else rmax_y
    return make_grid(-(rmax + pad), rmax + pad, -(ry + pad), ry + pad, zlo, zhi, vox)


def finish(F, axes, vox, name, note="", target=250000, upright=True, shift_to_bed=True, keep_largest=True):
    m = mesh_from_F(F, axes, vox, keep_largest=keep_largest)
    m = decimate(m, target, label=name)
    save(m, name, upright, note, shift_to_bed=shift_to_bed)
    return m


def flat_cut_sphere_z(R, ang_deg=35.0):
    """kula R ucieta plaszczyzna na kacie biegunowym ang (nawis 90-ang od pionu): odleglosc plaszczyzny od srodka i promien plaskiego"""
    a = math.radians(ang_deg)
    return R * math.cos(a), R * math.sin(a)
