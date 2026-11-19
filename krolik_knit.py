"""Krolik 'knitted' z WGRANEGO pliku STL (siedzacy krolik w dzianinie): TA SAMA BRYLA, ale faktura oczek z knit.py zamiast oryginalnej siatki.
Plik wejsciowy NIE jest czescia repo (cudzy model; sprawdz licencje, jesli miales wydruki sprzedawac): skrypt bierze go jako argument.
Kroki: korpus (najwieksza bryla) + plaskie wkladki podeszew (1,6 mm, wypelniaja kieszenie pod stopami) -> voxele -> wypelnienie -> pole odleglosci F ->
wygladzenie (gaussian sigma ~0,7 mm zeruje oryginalne oczka) -> plaskie dno -> knit.knit_F (wlasne oczka) -> oczy (dwie kule jak w pliku) -> marching cubes.
Kontrola ksztaltu: odleglosc oryginalnej powierzchni (200 tys. punktow) od nowej (percentyle), wymiary, objetosc; nawisy wg slicera (informacyjnie: ksztalt nie jest zmieniany).
  python3 krolik_knit.py /sciezka/Knitted__Easter_Bunny.stl                       -> out/krolik_knit.stl (+ .png: oryginal na gorze, nowy na dole)
  python3 krolik_knit.py plik.stl --stitch 3.2 --row 2.6 --amp 0.4 --name krolik_knit_gruby.stl   (grubsze oczka)"""
import sys, os, time, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trimesh
from scipy import ndimage as ndi
from lib import mesh_from_F, decimate, save, OUT
import nawisy
import knit

DEFAULT_IN = "/mnt/user-data/uploads/Knitted__Easter_Bunny.stl"


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


def smooth_sdf(shape, vox, sigma, pad=6.0, pad_top=5.0, pad_bot=5.0):
    """voxele -> F (dodatnie w srodku, mm); zwraca osie i F; dno: dolna warstwa powielona w dol, potem plaszczyzna z = 0"""
    vg = shape.voxelized(vox).fill()
    occ = np.asarray(vg.matrix, bool)
    T = vg.transform
    o = T[:3, 3]
    n, nb, nt = int(pad / vox), int(pad_bot / vox), int(pad_top / vox)
    occ = np.pad(occ, ((n, n), (n, n), (nb, nt)))
    org = o - np.array([n, n, nb]) * vox
    kmin = int(np.argmax(occ.any(axis=(0, 1))))
    occ[:, :, kmin - int(3.0 / vox):kmin] = occ[:, :, kmin:kmin + 1]
    din = ndi.distance_transform_edt(occ).astype(np.float32)
    dout = ndi.distance_transform_edt(~occ).astype(np.float32)
    F = np.where(occ, din - 0.5, -(dout - 0.5)).astype(np.float32) * vox
    del din, dout
    F = ndi.gaussian_filter(F, sigma / vox).astype(np.float32)
    axes = [(org[i] + vox * np.arange(occ.shape[i])).astype(np.float32) for i in range(3)]
    F = np.minimum(F, axes[2][None, None, :])                      # plaskie dno w z = 0
    return axes, F.astype(np.float32), occ


def add_sphere(F, axes, vox, c, r):
    ix = [slice(max(0, int((c[i] - r - 1 - axes[i][0]) / vox)), min(len(axes[i]), int((c[i] + r + 1 - axes[i][0]) / vox) + 1)) for i in range(3)]
    gx, gy, gz = np.meshgrid(axes[0][ix[0]], axes[1][ix[1]], axes[2][ix[2]], indexing="ij")
    s = r - np.sqrt((gx - c[0]) ** 2 + (gy - c[1]) ** 2 + (gz - c[2]) ** 2)
    F[ix[0], ix[1], ix[2]] = np.maximum(F[ix[0], ix[1], ix[2]], s.astype(np.float32))


def preview(orig, mine, path):
    import render
    from PIL import Image
    imgs = []
    for m in (orig, mine):
        c = m.bounds.mean(0)
        for y, p in ((0, 5), (-40, 12), (130, 12)):
            imgs.append(render.render([m], yaw=y, pitch=p, W=800, H=1000, ext=9.5, center=(c[0], 46)))
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
    ap.add_argument("--target", type=int, default=900000)
    ap.add_argument("--name", default="krolik_knit.stl")
    ap.add_argument("--noview", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    main_m, eyes, plates = load_parts(a.inp)
    print(f"korpus {len(main_m.faces):,} tr., {main_m.extents.round(1)} mm; oczy: {len(eyes)}, wkladki podeszew: {len(plates)}")
    shape = trimesh.util.concatenate([main_m] + plates)
    axes, F, occ = smooth_sdf(shape, a.vox, a.sigma)
    print(f"gladkie F {F.shape} ({time.time() - t0:.0f} s), objetosc wokseli {occ.sum() * a.vox ** 3 / 1000:.1f} cm3")
    del occ
    F2 = knit.knit_F(F, axes, a.vox, p=a.stitch, q=a.row, A=a.amp, min_len=2.3 * a.stitch)
    for c, r in eyes:
        add_sphere(F2, axes, a.vox, c, r)
    del F
    # ksztalt: odleglosc oryginalnej powierzchni korpusu od nowej
    pts, _ = trimesh.sample.sample_surface(main_m, 200000)
    idx = np.stack([(pts[:, i] - axes[i][0]) / a.vox for i in range(3)])
    d = np.abs(ndi.map_coordinates(F2, idx, order=1))
    print(f"ksztalt vs oryginal: odleglosc powierzchni sr. {d.mean():.2f} mm, 95% {np.percentile(d, 95):.2f} mm, 99% {np.percentile(d, 99):.2f} mm, maks. {d.max():.2f} mm")
    m = mesh_from_F(F2, axes, a.vox)
    del F2
    m = decimate(m, a.target, label=a.name)
    save(m, a.name, True, f"krolik knitted z pliku: oczka {a.stitch} x {a.row} mm, wypuklosc {a.amp} mm")
    m = trimesh.load(os.path.join(OUT, a.name))
    print(f"krolik: {m.extents.round(1)} mm (oryginal {main_m.extents.round(1)}) | V {m.volume / 1000:.1f} cm3 | szczelny {m.is_watertight} ({time.time() - t0:.0f} s)")
    for thr in (25.0, 30.0):
        o = nawisy.slicer_overhang(m, 0.2, thr)
        print(f"  slicer {thr:.0f} st.: nawis {o['area']:.1f} mm2 | wyspy w powietrzu {o['floating']:.2f} mm2 | najszersze {o['width']:.2f} mm (z = {o['z']:.1f})")
    if not a.noview:
        preview(main_m, m, os.path.join(OUT, a.name.replace(".stl", ".png")))
    return m


if __name__ == "__main__":
    main()
