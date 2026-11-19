"""WLASNY krolik siedzacy w dzianinie (projekt od zera, bez cudzych plikow): pole odleglosci z elips i kapsul (jak jelen.py), plaskie dno, nawisy obciete
(nawisy.carve), faktura oczek z knit.py, oczy jako OSOBNE czesci wciskane (kula + czop, gniazda w glowie jak w krolik_knit.py).
Uklad: x = przod, y = bok, z = gora; z = 0 to stol. Wysokosc z uszami --h (domyslnie 92 mm).
  python3 krolik_wlasny.py                 -> out/krolik_wlasny.stl (korpus z gniazdami), out/krolik_wlasny_oczy.stl (2 oczy do druku) + .png
  python3 krolik_wlasny.py --quick         -> szybki podglad gladkiej bryly (skok 0,4 mm, bez faktury) do dopracowania sylwetki
  python3 krolik_wlasny.py --stitch 3.2 --row 2.6 --amp 0.4 --name krolik_wlasny_gruby.stl   (grubsze oczka)"""
import sys, os, time, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
from jelen import smin, cap, ell
import trimesh
import nawisy
import knit
import krolik_knit as KK

H_DESIGN = 93.2
NAWIS_ANG = 55.0         # kat zbocza od pionu, do ktorego obcinamy nawisy (zbocza w dol >= 35 st. od poziomu)
EYE_R = 2.0              # promien oka [mm]
EYES = ((20.0, 8.2, 56.5), (20.0, -8.2, 56.5))     # przyblizone srodki oczu (poprawiane na powierzchnie glowy)


def ear(P, c, u, nrm, a, b, t):
    """ucho: plaska elipsoida; os dluga u (polowa a), szerokosc b, grubosc t wzdluz nrm (plaska strona patrzy w nrm)"""
    X, Y, Z = P
    u = np.array(u, float); u /= np.linalg.norm(u)
    w = np.array(nrm, float); w -= w.dot(u) * u; w /= np.linalg.norm(w)
    v = np.cross(u, w)
    d = (X - c[0], Y - c[1], Z - c[2])
    pu = d[0] * u[0] + d[1] * u[1] + d[2] * u[2]
    pv = d[0] * v[0] + d[1] * v[1] + d[2] * v[2]
    pw = d[0] * w[0] + d[1] * w[1] + d[2] * w[2]
    q = np.sqrt((pu / a) ** 2 + (pv / b) ** 2 + (pw / t) ** 2)
    return (q - 1.0) * min(a, b, t)


def design(P):
    """pole odleglosci (ujemne w srodku) w mm; wysokosc ok. 92"""
    D = ell(P, (-5.0, 0, 13.5), (17.5, 14.5, 17.0))                       # zad (ciety stolem: plaska plama styku)
    D = smin(D, ell(P, (6.5, 0, 23.0), (11.5, 11.0, 16.0)), 7.0)         # piers i brzuch
    D = smin(D, ell(P, (-1.5, 0, 28.0), (14.0, 11.5, 11.5)), 7.0)        # plecy
    D = smin(D, cap(P, (8.0, 0, 33.0), (12.5, 0, 48.0), 9.0, 8.5), 6.0)    # szyja
    D = smin(D, ell(P, (13.0, 0, 54.0), (13.0, 11.3, 11.5)), 5.0)        # glowa (duza, zabawkowa)
    D = smin(D, ell(P, (23.0, 0, 51.0), (7.5, 6.5, 6.0)), 3.5)           # pysk
    D = smin(D, ell(P, (28.3, 0, 51.5), (2.2, 2.8, 2.0)), 1.2)           # nos
    D = smin(D, ell(P, (-21.5, 0, 17.0), (5.5, 5.2, 5.2)), 2.5)          # ogon
    for s in (-1.0, 1.0):
        D = smin(D, ell(P, (19.0, s * 6.4, 49.0), (6.0, 4.6, 4.6)), 3.0)                       # policzek
        D = smin(D, ell(P, (-3.5, s * 12.0, 10.0), (13.0, 6.5, 13.5)), 4.5)                    # udo (ciete stolem)
        D = smin(D, cap(P, (-4.0, s * 11.0, 2.4), (15.0, s * 10.5, 2.2), 3.8, 3.4), 3.0)       # tylna stopa wysunieta do przodu (ciete stolem)
        D = smin(D, cap(P, (12.0, s * 6.8, 28.0), (19.0, s * 6.2, 2.5), 4.6, 3.8), 3.0)        # przednia noga
        D = smin(D, ell(P, (20.5, s * 6.4, 2.2), (5.5, 3.8, 3.6)), 2.5)                         # przednia lapa (ciete stolem)
        D = smin(D, ear(P, (6.5, s * 7.0, 77.0), (-0.12, s * 0.30, 0.95), (0.94, s * 0.34, 0.0), 17.0, 6.8, 3.3), 3.0)   # ucho
    return D


def smooth_F(S, vox, slab=24):
    """gladkie pole F (plaskie dno, nawisy obciete); liczone w plastrach z, zeby zmiescic siatke w pamieci"""
    box, zhi = (-33.0, 38.0, -26.0, 26.0), 99.0
    axes, (X, Y, Z) = make_grid(box[0] * S, box[1] * S, box[2] * S, box[3] * S, -0.6, zhi * S, vox)
    nz = len(axes[2])
    F = np.empty((len(axes[0]), len(axes[1]), nz), np.float32)
    for k0 in range(0, nz, slab):
        Zs = Z[:, :, k0:k0 + slab]
        D = design((X / S, Y / S, Zs / S)) * S
        F[:, :, k0:k0 + slab] = smin(-D, Zs, 0.5)
    F = nawisy.carve(F, vox, axes[2], ang=NAWIS_ANG, zmin=0.0)
    return axes, F


def quick_preview(m, eyes, path):
    import render
    from PIL import Image
    c = m.bounds.mean(0)
    ms = [m] + [trimesh.creation.icosphere(subdivisions=2, radius=EYE_R) for _ in eyes]
    for q, e in zip(ms[1:], eyes):
        q.apply_translation(e)
    imgs = [render.render(ms, yaw=y, pitch=p, W=800, H=1000, ext=9.5, center=(c[0], 46)) for y, p in ((0, 5), (-40, 12), (130, 12))]
    W = Image.new("RGB", (2400, 1000), "white")
    for i, im in enumerate(imgs):
        W.paste(im, (800 * i, 0))
    W.save(path)


def render_views(body, eyes, outdir, W=444, H=720, ss=2, ext=7.0):
    """4 ujecia do artefaktu 'Modele 3D' (przod, ukos, bok, tyl): PNG 444 x 720, przezroczyste tlo, korpus czerwony, oczy ciemne (dla czytelnosci);
    render w podwojnej rozdzielczosci i zmniejszony (gladkie krawedzie)"""
    import render
    from PIL import Image
    os.makedirs(outdir, exist_ok=True)
    SENT = (1, 254, 3)
    base, dark = (205, 46, 36), (52, 54, 60)
    for name, yaw, pitch in (("przod", -90, 5), ("ukos", -40, 8), ("bok", 0, 5), ("tyl", 90, 5)):
        im = np.asarray(render.render([body] + list(eyes), yaw=yaw, pitch=pitch, W=W * ss, H=H * ss, ext=ext * ss, colors=[base] + [dark] * len(eyes), bg=SENT, dens=10.0))
        mask = np.any(im != np.array(SENT, np.uint8), axis=2)
        rgb = im.copy()
        rgb[~mask] = base                                              # brzegi mieszaja sie z kolorem modelu, bez bialej obwodki
        out = Image.fromarray(np.dstack([rgb, (mask * 255).astype(np.uint8)]), "RGBA").resize((W, H), Image.LANCZOS)
        out.save(os.path.join(outdir, name + ".png"))
    print(f"  ujecia zapisane w {outdir}", flush=True)


def place_eyes(F, axes, vox, S, inside=0.4):
    """srodki oczu na powierzchni gladkiej glowy (srodek 'inside' mm pod powierzchnia) + normalne zewnetrzne"""
    out = []
    for e in EYES:
        c = np.array(e, float) * S
        for _ in range(3):
            n, fc = KK.eye_normal(F, axes, vox, c)
            c = c + n * (fc - inside)
        n, fc = KK.eye_normal(F, axes, vox, c)
        out.append((c, n, fc))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h", type=float, default=92.0, help="wysokosc z uszami [mm]")
    ap.add_argument("--vox", type=float, default=0.2)
    ap.add_argument("--quick", action="store_true", help="gladka bryla, skok 0,4 mm, bez faktury i oczu (podglad sylwetki)")
    ap.add_argument("--stitch", type=float, default=2.6, help="szerokosc oczka p [mm]")
    ap.add_argument("--row", type=float, default=2.2, help="wysokosc rzedu q [mm]")
    ap.add_argument("--amp", type=float, default=0.35, help="wysokosc wypuklosci [mm]")
    ap.add_argument("--peg", type=float, default=2.2, help="srednica czopa oka [mm]")
    ap.add_argument("--peglen", type=float, default=2.5, help="dlugosc czopa za kula [mm]")
    ap.add_argument("--gap", type=float, default=0.10, help="luz gniazda oka na strone [mm]")
    ap.add_argument("--target", type=int, default=900000)
    ap.add_argument("--name", default="krolik_wlasny.stl")
    ap.add_argument("--noview", action="store_true")
    ap.add_argument("--views", metavar="KATALOG", help="tylko 4 ujecia PNG (przod, ukos, bok, tyl) gotowego out/<name> z oczami na miejscu, do artefaktu Modele 3D")
    a = ap.parse_args()
    S = a.h / H_DESIGN
    t0 = time.time()
    if a.views:
        axes, F = smooth_F(S, a.vox)
        r_eye = EYE_R * S
        rp = min(a.peg / 2, 0.55 * r_eye)
        flat = r_eye * (1 - np.cos(np.radians(35.0)))
        placed = [KK.eye_mesh(c, n, r_eye, rp, a.peglen, flat, a.gap) for c, n, _ in place_eyes(F, axes, a.vox, S)]
        render_views(trimesh.load(os.path.join(OUT, a.name)), placed, a.views)
        return
    if a.quick:
        axes, F = smooth_F(S, a.vox)
        m = mesh_from_F(F, axes, a.vox)
        m.apply_translation([0, 0, -m.bounds[0][2]])
        print(f"quick: {m.extents.round(1)} mm, V {m.volume / 1000:.1f} cm3 ({time.time() - t0:.0f} s)")
        ev = place_eyes(F, axes, a.vox, S)
        for c, n, fc in ev:
            print(f"  oko: srodek {np.round(c, 1)}, F = {fc:+.2f}, n {np.round(n, 2)}")
        m.export("/tmp/krolik_wlasny_quick.stl")
        quick_preview(m, [c for c, _, _ in ev], "/tmp/krolik_wlasny_quick.png")
        return
    axes, F = smooth_F(S, a.vox)
    print(f"gladkie F {F.shape} ({time.time() - t0:.0f} s), RSS {KK.rss():.1f} GB", flush=True)
    r_eye = EYE_R * S
    rp = min(a.peg / 2, 0.55 * r_eye)
    flat = r_eye * (1 - np.cos(np.radians(35.0)))
    info = []
    for c, n, fc in place_eyes(F, axes, a.vox, S):
        info.append((c, n))
        print(f"  oko: srodek {np.round(c, 1)}, F(srodka) = {fc:+.2f} mm, normalna {np.round(n, 2)}", flush=True)
    F2 = knit.knit_F(F, axes, a.vox, p=a.stitch, q=a.row, A=a.amp, min_len=2.3 * a.stitch, renorm=True)
    del F
    for c, n in info:
        R = r_eye + a.peglen + 0.3 + rp + a.gap + 2.0
        sl = KK.window(F2, axes, a.vox, c, R)
        gx = axes[0][sl[0]][:, None, None] - c[0]
        gy = axes[1][sl[1]][None, :, None] - c[1]
        gz = axes[2][sl[2]][None, None, :] - c[2]
        _, sock = KK.eye_fields(gx, gy, gz, n, r_eye, rp, a.peglen, flat, a.gap)
        F2[sl] = np.minimum(F2[sl], -np.broadcast_to(sock, F2[sl].shape).astype(np.float32))
    m = mesh_from_F(F2, axes, a.vox)
    del F2
    m = decimate(m, a.target, label=a.name)
    save(m, a.name, True, f"wlasny krolik siedzacy w dzianinie: oczka {a.stitch} x {a.row} mm, wypuklosc {a.amp} mm, gniazda na wciskane oczy")
    m = trimesh.load(os.path.join(OUT, a.name))
    print(f"krolik: {m.extents.round(1)} mm | V {m.volume / 1000:.1f} cm3 | szczelny {m.is_watertight} ({time.time() - t0:.0f} s, RSS {KK.rss():.1f} GB)", flush=True)
    for thr in (25.0, 30.0):
        o = nawisy.slicer_overhang(m, 0.2, thr)
        print(f"  slicer {thr:.0f} st.: nawis {o['area']:.1f} mm2 | wyspy w powietrzu {o['floating']:.2f} mm2 | najszersze {o['width']:.2f} mm (z = {o['z']:.1f})", flush=True)
    placed, plate = [], []
    for k, (c, n) in enumerate(info):
        em = KK.eye_mesh(c, n, r_eye, rp, a.peglen, flat, a.gap)
        placed.append(em)
        plate.append(KK.print_pose(em, c, n, (k - (len(info) - 1) / 2) * (2 * r_eye + 6.0)))
    for k, em in enumerate(placed):
        try:
            inter = trimesh.boolean.intersection([m, em], engine="manifold")
            vi = float(inter.volume) if len(inter.faces) else 0.0
            dmin = float(trimesh.proximity.ProximityQuery(m).on_surface(em.vertices[::3])[1].min())
            print(f"  oko {k + 1} w gniezdzie: interferencja {vi:.4f} mm3 | najmniejszy luz {dmin:.3f} mm", flush=True)
        except Exception as ex:
            print(f"  (kontrola pasowania oka {k + 1} pominieta: {ex})", flush=True)
    pe = trimesh.util.concatenate(plate)
    name_e = a.name.replace(".stl", "_oczy.stl")
    save(pe, name_e, True, f"oczy do krolika: kula r {r_eye:.2f} mm splaszczona {flat:.2f} mm, czop {2 * rp:.1f} x {a.peglen} mm, do druku przodem do stolu")
    for k, q in enumerate(plate):
        o = nawisy.slicer_overhang(q, 0.2, 30.0)
        print(f"  oko {k + 1}: {q.extents.round(2)} mm, V {q.volume:.1f} mm3, szczelne {q.is_watertight}, nawis (slicer 30 st.) {o['area']:.2f} mm2", flush=True)
    if not a.noview:
        import render
        from PIL import Image
        c0 = m.bounds.mean(0)
        imgs = [render.render([m] + placed, yaw=y, pitch=p, W=800, H=1000, ext=9.5, center=(c0[0], 46)) for y, p in ((0, 5), (-40, 12), (130, 12))]
        W = Image.new("RGB", (2400, 1000), "white")
        for i, im in enumerate(imgs):
            W.paste(im, (800 * i, 0))
        W.save(os.path.join(OUT, a.name.replace(".stl", ".png")))
        ce = pe.bounds.mean(0)
        render.render([pe], yaw=0, pitch=18, W=900, H=500, ext=26, center=(ce[0], pe.extents[2] / 2)).save(os.path.join(OUT, name_e.replace(".stl", ".png")))
    return m


if __name__ == "__main__":
    main()
