"""Wspolna biblioteka linii: zebra, czopy/gniazda, czesci plaskie, kontrola siatek. Wymiary w mm."""
import json
import math
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import measure

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# ---------- standard linii ----------
RIB_AMP = 0.8            # amplituda zeber (razem 1,6 mm)
RIB_PITCH = 3.4          # docelowy rozstaw zeber na najszerszym obwodzie
PEG_W, PEG_L, PEG_R = 5.0, 8.0, 1.0      # czop 5 x 5 x 8, zaokraglenie 1 mm
SOCK_W, SOCK_D, SOCK_R = 5.4, 9.0, 1.25  # gniazdo 5,4 x 5,4 x 9 (luz 0,2 / strone)
TILT = math.radians(14)  # pochylenie gniazd uszu/poroza na zewnatrz
EAR_X = 6.0              # polozenie gniazd (x = +-6) na szczycie glowy
EAR_T, ANT_T = 5.5, 5.0  # grubosc ucha / poroza
RING_H = 0.7             # wypuklosc owalu na uchu
LIFT = 0.6               # podniesienie podstawy ucha nad powierzchnia glowy

REPORT = {}


def n_ribs(r_max):
    return int(round(2 * math.pi * r_max / RIB_PITCH))


# ---------- siatka 3D ----------
def make_grid(xlo, xhi, ylo, yhi, zlo, zhi, vox):
    """siatka z minimalnym przesunieciem, zeby wezly nie lezaly dokladnie na plaszczyznach (z=0, x=0)"""
    s = 0.0137
    x = (xlo + s + np.arange(0, int((xhi - xlo) / vox) + 2) * vox).astype(np.float32)
    y = (ylo + s + np.arange(0, int((yhi - ylo) / vox) + 2) * vox).astype(np.float32)
    z = (zlo + s + np.arange(0, int((zhi - zlo) / vox) + 2) * vox).astype(np.float32)
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij", sparse=True)
    return (x, y, z), (X, Y, Z)


def mesh_from_F(F, axes, vox, keep_largest=True):
    x, y, z = axes
    v, f, _, _ = measure.marching_cubes(F.astype(np.float32), level=0.0, spacing=(vox, vox, vox),
                                        gradient_direction="ascent")
    v[:, 0] += x[0]
    v[:, 1] += y[0]
    v[:, 2] += z[0]
    m = trimesh.Trimesh(v, f, process=True)
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    if keep_largest:
        m = max(m.split(only_watertight=False), key=lambda p: len(p.faces))
    m.remove_unreferenced_vertices()
    trimesh.repair.fix_normals(m)
    trimesh.repair.fill_holes(m)
    return m


# ---------- ramki i pudelka ----------
class Frame:
    """uklad lokalny (a,b,c) o poczatku O i osiach A,B,C (ortonormalne)"""

    def __init__(self, O, A, B, C):
        self.O, self.A, self.B, self.C = (np.asarray(v, float) for v in (O, A, B, C))

    def to_local(self, X, Y, Z):
        dx, dy, dz = X - self.O[0], Y - self.O[1], Z - self.O[2]
        a = self.A[0] * dx + self.A[1] * dy + self.A[2] * dz
        b = self.B[0] * dx + self.B[1] * dy + self.B[2] * dz
        c = self.C[0] * dx + self.C[1] * dy + self.C[2] * dz
        return a, b, c

    def matrix(self):
        T = np.eye(4)
        T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = self.A, self.B, self.C, self.O
        return T

    def det(self):
        return float(np.dot(np.cross(self.A, self.B), self.C))


def rbox_F(a, b, c, lo, hi, rad):
    """pole zaokraglonego pudelka (dodatnie wewnatrz, ok. odleglosc w mm)"""
    q = []
    for v, l, h in ((a, lo[0], hi[0]), (b, lo[1], hi[1]), (c, lo[2], hi[2])):
        q.append(np.abs(v - (l + h) / 2) - ((h - l) / 2 - rad))
    out = np.sqrt(np.maximum(q[0], 0) ** 2 + np.maximum(q[1], 0) ** 2 + np.maximum(q[2], 0) ** 2)
    ins = np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)
    return -(out + ins - rad)


def peg_F(a, b, c, c0=0.0):
    """czop 5 x 5 x 8 wchodzacy w b<0; c0 = dolna plaszczyzna"""
    return rbox_F(a, b, c, (-PEG_W / 2, -PEG_L, c0), (PEG_W / 2, 0.0, c0 + PEG_W), PEG_R)


def socket_F(a, b, c):
    """gniazdo 5,4 x 5,4 x 9 (os srodkowa c = 2,5); b=0 to plaszczyzna wejscia"""
    return rbox_F(a, b, c, (-SOCK_W / 2, -SOCK_D, 2.5 - SOCK_W / 2), (SOCK_W / 2, 1.5, 2.5 + SOCK_W / 2), SOCK_R)


def socket_frame(P0, B, A, C=(0, -1, 0)):
    """uklad gniazda: poczatek lezy w P0 przesuniety o 2,5 mm wzdluz -C (os gniazda przechodzi przez P0)"""
    C = np.asarray(C, float)
    return Frame(np.asarray(P0, float) - 2.5 * C, A, B, C)


# ---------- zebra ----------
def rib_amp(r, amp=RIB_AMP, r0=4.0, r1=10.0):
    return amp * np.clip((r - r0) / (r1 - r0), 0, 1)


def ribbed_F(R, N, theta, rho, amp=RIB_AMP, shape=0.8, fade=True):
    rib = np.cos(N * theta)
    rib = np.sign(rib) * np.abs(rib) ** shape
    a = rib_amp(R, amp) if fade else amp
    return (R + a * rib - 1e-3) - rho


# ---------- czesci plaskie ----------
class Canvas:
    def __init__(self, a0, a1, b0, b1, res=0.1):
        self.a0, self.b0, self.res = a0, b0, res
        self.na, self.nb = int(round((a1 - a0) / res)), int(round((b1 - b0) / res))
        self.img = Image.new("L", (self.na, self.nb), 0)
        self.d = ImageDraw.Draw(self.img)

    def P(self, a, b):
        return ((a - self.a0) / self.res, (b - self.b0) / self.res)

    def poly(self, pts, v=255):
        self.d.polygon([self.P(a, b) for a, b in pts], fill=v)

    def ellipse(self, ca, cb, ra, rb, v=255):
        x0, y0 = self.P(ca - ra, cb - rb)
        x1, y1 = self.P(ca + ra, cb + rb)
        self.d.ellipse([x0, y0, x1, y1], fill=v)

    def line(self, p, q, w, v=255):
        self.d.line([self.P(*p), self.P(*q)], fill=v, width=max(1, int(round(w / self.res))))
        self.ellipse(p[0], p[1], w / 2, w / 2, v)
        self.ellipse(q[0], q[1], w / 2, w / 2, v)

    def path(self, pts, w, v=255):
        for p, q in zip(pts[:-1], pts[1:]):
            self.line(p, q, w, v)

    def rect(self, a0, a1, b0, b1, v=255):
        self.poly([(a0, b0), (a1, b0), (a1, b1), (a0, b1)], v)

    def mask(self):
        return np.array(self.img) > 127   # [b_idx, a_idx]

    def _set(self, m):
        self.img = Image.fromarray((m * 255).astype(np.uint8))
        self.d = ImageDraw.Draw(self.img)

    def close_(self, r):
        """zaokraglenie wkleslych naroznikow (fillet) promieniem r [mm]"""
        m = self.mask()
        dil = ndi.distance_transform_edt(~m) * self.res <= r
        er = ndi.distance_transform_edt(np.pad(dil, 1, constant_values=True))[1:-1, 1:-1] * self.res > r
        self._set(er | m)

    def open_(self, r):
        """zaokraglenie wypuklych naroznikow promieniem r [mm]"""
        m = self.mask()
        er = ndi.distance_transform_edt(np.pad(m, 1))[1:-1, 1:-1] * self.res > r
        dil = ndi.distance_transform_edt(~er) * self.res <= r
        self._set(dil & m)


class FlatPart:
    """plaska czesc: kontur 2D + faza (pillow) do grubosci T; opcjonalnie wypukly owal i rowki"""

    def __init__(self, canvas, T, w=1.0, k=1.5, ring_mask=None, ring_h=0.0, groove_mask=None, groove_d=0.0, mirror=False):
        m = canvas.mask()
        self.cv, self.T, self.mirror = canvas, T, mirror
        res = canvas.res
        din = ndi.distance_transform_edt(m) - 0.5
        dout = ndi.distance_transform_edt(~m) - 0.5
        self.d = ndi.gaussian_filter(np.where(m, din, -dout) * res, 2.5)
        top = np.minimum(T, w + k * np.maximum(self.d, 0))
        if ring_mask is not None and ring_h > 0:
            dist = ndi.distance_transform_edt(~ring_mask) * res
            top = top + ring_h * np.clip((0.9 - dist) / 0.35, 0, 1)
        if groove_mask is not None and groove_d > 0:
            dist = ndi.distance_transform_edt(~groove_mask) * res
            top = top - groove_d * np.clip((0.7 - dist) / 0.3, 0, 1)
        self.top = top
        self.res = res

    def F(self, a, b, c):
        a, b, c = np.broadcast_arrays(a, b, c)
        shp = a.shape
        aa = -a if self.mirror else a
        ia = (aa.ravel() - self.cv.a0) / self.res - 0.5
        ib = (b.ravel() - self.cv.b0) / self.res - 0.5
        coords = np.vstack([ib, ia])
        d = ndi.map_coordinates(self.d, coords, order=1, mode="constant", cval=-5.0)
        top = ndi.map_coordinates(self.top, coords, order=1, mode="constant", cval=0.0)
        cc = c.ravel()
        F = np.minimum(np.minimum(cc, top - cc), d)
        return F.reshape(shp).astype(np.float32)


def local_mesh(field_fn, a_rng, b_rng, c_rng, vox=0.2):
    axes, (A_, B_, C_) = make_grid(a_rng[0], a_rng[1], b_rng[0], b_rng[1], c_rng[0], c_rng[1], vox)
    F = field_fn(A_, B_, C_)
    return mesh_from_F(F, axes, vox)


# ---------- kontrola ----------
def overhang_report(m, limit_deg=55.0, min_z=0.6):
    """powierzchnia scianek zwroconych w dol bardziej niz limit (od pionu), poza kontaktem ze stolem"""
    n = m.face_normals
    zc = m.triangles_center[:, 2]
    steep = (n[:, 2] < -math.sin(math.radians(limit_deg))) & (zc > min_z)
    area = float(m.area_faces[steep].sum())
    zs = zc[steep]
    return area, (float(zs.min()), float(zs.max())) if steep.any() else (None, None)


def report(m, name, upright=True, note=""):
    e = m.extents
    row = dict(name=name, extents=[round(float(v), 1) for v in e], tris=int(len(m.faces)),
               watertight=bool(m.is_watertight), volume_cm3=round(abs(float(m.volume)) / 1000, 1),
               size_mb=None)
    if upright:
        area, zr = overhang_report(m)
        row["overhang55_mm2"] = round(area, 1)
        row["overhang55_z"] = zr
    if note:
        row["note"] = note
    REPORT[name] = row
    return row


def save(m, name, upright=True, note="", shift_to_bed=True):
    if shift_to_bed:
        m = m.copy()
        m.apply_translation([0, 0, -m.bounds[0][2]])
    path = os.path.join(OUT, name)
    m.export(path)
    # kontrola po zapisie: wczytaj plik (float32, scalanie wierzcholkow) i usun ewentualne resztki / zdegenerowane trojkaty
    r = trimesh.load(path, process=True)
    r.update_faces(r.nondegenerate_faces())
    r.remove_unreferenced_vertices()
    parts_ = r.split(only_watertight=False)
    if len(parts_) > 1 or not r.is_watertight or len(r.faces) != len(m.faces):
        if len(parts_) > 1:
            r = max(parts_, key=lambda p: len(p.faces))
        trimesh.repair.fill_holes(r)
        trimesh.repair.fix_normals(r)
        if r.is_watertight:
            r.export(path)
            m = r
            print(f"  ({name}: oczyszczono po zapisie)")
    REPORT.setdefault(name, {})
    r = report(m, name, upright, note)
    r["size_mb"] = round(os.path.getsize(path) / 1e6, 1)
    print(f"{name}: {r['extents']} mm | tri {r['tris']:,} | wt {r['watertight']} | {r['size_mb']} MB"
          + (f" | nawis>55: {r.get('overhang55_mm2')} mm2 {r.get('overhang55_z')}" if upright else ""))
    json.dump(REPORT, open(os.path.join(OUT, "_raport.json"), "w"), indent=1, ensure_ascii=False)
    return path


def save_assembled(m, name):
    m.export(os.path.join(OUT, "_zlozone_" + name))


def splat(meshes, yaw, W=520, H=860, pitch=8, ext_override=None, dot=3):
    a, p = np.deg2rad(yaw), np.deg2rad(pitch)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    R = Rx @ Rz
    V = np.vstack([m.vertices @ R.T for m in meshes])
    N = np.vstack([m.vertex_normals @ R.T for m in meshes])
    vis = N[:, 1] < 0.2
    L = np.array([-0.4, -0.7, 0.6]); L /= np.linalg.norm(L)
    sh = np.clip(N @ L, 0, 1) * 0.75 + 0.25
    ext = ext_override or max(np.ptp(V[:, 0]) * 1.15, np.ptp(V[:, 2]))
    sc = (H - 50) / ext
    cx = (V[:, 0].max() + V[:, 0].min()) / 2
    px = ((V[:, 0] - cx) * sc + W / 2).astype(int)
    py = (H - 25 - (V[:, 2] - V[:, 2].min()) * sc).astype(int)
    idx = np.where(vis)[0]
    o = idx[np.argsort(-V[idx, 1])]
    img = np.full((H, W), 255, np.uint8)
    for dx in range(dot):
        for dy in range(dot):
            img[np.clip(py[o] + dy, 0, H - 1), np.clip(px[o] + dx, 0, W - 1)] = (sh[o] * 230).astype(np.uint8)
    return Image.fromarray(img)


def decimate(m, target_faces, agg=3, label=""):
    """redukcja liczby trojkatow (quadric) z kontrola szczelnosci i odchylki (mm); przy porazce zwraca oryginal"""
    import fast_simplification as fs
    if len(m.faces) <= target_faces:
        return m
    d = None
    for ag, tg in ((agg, target_faces), (5, target_faces), (7, target_faces), (agg, int(target_faces * 1.15)), (agg, int(target_faces * 1.33)),
                   (agg, int(target_faces * 1.5)), (5, int(target_faces * 1.5)), (agg, int(target_faces * 1.8))):
        v, f = fs.simplify(np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64), target_count=int(tg), agg=ag)
        c = trimesh.Trimesh(v, f, process=True)
        c.merge_vertices()
        c.update_faces(c.nondegenerate_faces())
        c.remove_unreferenced_vertices()
        parts_ = c.split(only_watertight=False)
        if len(parts_) > 1:
            c = max(parts_, key=lambda p: len(p.faces))
        if not c.is_watertight:
            trimesh.repair.fill_holes(c)
        trimesh.repair.fix_normals(c)
        if c.is_watertight and c.volume > 0:
            d = c
            break
    if d is None:
        print(f"  decymacja {label} odrzucona (nieszczelna)")
        return m
    idx = np.random.default_rng(0).choice(len(m.vertices), min(15000, len(m.vertices)), replace=False)
    _, dist, _ = trimesh.proximity.closest_point(d, m.vertices[idx])
    print(f"  decymacja {label}: {len(m.faces):,} -> {len(d.faces):,} tr. | odchylka sr. {dist.mean():.4f} maks. {dist.max():.4f} mm | "
          f"objetosc {d.volume / m.volume:.5f}")
    return d
