"""Jelen 'knitted' (dzianina): TEN SAM wlasny jelen co w jelen.py (stojacy, bez podpor), ale zamiast gladkiej skory rzedy oczek jak z drutow / szydelka
(knit.py: oczka 'V' w kolumnach, rzedy poziome na tulowiu, nogach i szyi, pionowe na grzbiecie i czubku glowy).
Skala: wysokosc calosci --h mm (domyslnie 130; faktura ma ten sam rozmiar oczek w mm niezaleznie od skali, wiec duzy jelen = wiecej oczek).
  python3 jelen_knit.py                       -> out/jelen_knit_130.stl
  python3 jelen_knit.py --h 100 --stitch 3.2  -> mniejszy jelen z drobniejszymi oczkami
  python3 jelen_knit.py --check               -> dodatkowo porownanie nawisow z gladkim jelenien tej samej wielkosci (slicer 25 / 30 st.)
Parametry faktury: --stitch p (szerokosc oczka), --row q (wysokosc rzedu), --amp A (wysokosc wypuklosci). Dla dyszy 0,4: p >= 3, A <= 0,6."""
import sys, time, argparse, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rev import *
import jelen
import nawisy
import knit

CACHE = os.environ.get("KNIT_CACHE", "/tmp/jelen_knit_cache")


def smooth_F(H, vox, slab=24):
    """gladkie pole F jelenia (jak jelen.build, ale w plastrach z, zeby zmiescic duza siatke w pamieci) + obciecie nawisow"""
    S = jelen.S_STD * H / jelen.HEIGHT
    box, zhi = (-25.0, 31.0, -26.0, 26.0), 56.0
    axes, (X, Y, Z) = make_grid(box[0] * S, box[1] * S, box[2] * S, box[3] * S, -0.6, zhi * S, vox)
    nz = len(axes[2])
    F = np.empty((len(axes[0]), len(axes[1]), nz), np.float32)
    for k0 in range(0, nz, slab):
        Zs = Z[:, :, k0:k0 + slab]
        D = jelen.design((X / S, Y / S, Zs / S)) * S
        F[:, :, k0:k0 + slab] = jelen.smin(-D, Zs, 0.5)
    F = nawisy.carve(F, vox, axes[2], ang=jelen.NAWIS_ANG, zmin=0.0)
    return axes, F, S


def contact_area(m, z=0.1):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return 0.0
    p2, _ = sec.to_planar()
    return float(sum(p.area for p in p2.polygons_full))


def report_overhang(m, label):
    for thr in (25.0, 30.0):
        o = nawisy.slicer_overhang(m, 0.2, thr)
        print(f"  {label}: slicer {thr:.0f} st.: nawis {o['area']:.1f} mm2 | wyspy w powietrzu {o['floating']:.2f} mm2 | najszersze {o['width']:.2f} mm (z = {o['z']:.1f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h", type=float, default=130.0, help="wysokosc jelenia z porozem [mm]")
    ap.add_argument("--vox", type=float, default=0.3)
    ap.add_argument("--stitch", type=float, default=4.0, help="szerokosc oczka p [mm]")
    ap.add_argument("--row", type=float, default=3.2, help="wysokosc rzedu q [mm]")
    ap.add_argument("--amp", type=float, default=0.5, help="wysokosc wypuklosci oczek [mm]")
    ap.add_argument("--target", type=int, default=700000, help="docelowa liczba trojkatow")
    ap.add_argument("--name", default=None)
    ap.add_argument("--check", action="store_true", help="porownaj nawisy z gladkim jelenien")
    ap.add_argument("--nocache", action="store_true")
    a = ap.parse_args()
    name = a.name or f"jelen_knit_{a.h:.0f}.stl"
    os.makedirs(CACHE, exist_ok=True)
    cf = os.path.join(CACHE, f"F_{a.h:.0f}_{a.vox}.npy")
    t0 = time.time()
    S = jelen.S_STD * a.h / jelen.HEIGHT
    if os.path.exists(cf) and not a.nocache:
        F = np.load(cf)
        axes, (X, Y, Z) = make_grid(-25.0 * S, 31.0 * S, -26.0 * S, 26.0 * S, -0.6, 56.0 * S, a.vox)
        del X, Y, Z
        print(f"gladkie F z cache {F.shape} ({time.time() - t0:.0f} s)")
    else:
        axes, F, S = smooth_F(a.h, a.vox)
        np.save(cf, F)
        print(f"gladkie F {F.shape} ({time.time() - t0:.0f} s), S = {S:.3f}")
    if a.check:
        ms = mesh_from_F(F, axes, a.vox)
        ms = decimate(ms, 300000, label="gladki")
        print(f"gladki: {ms.extents.round(1)} mm | V {ms.volume / 1000:.1f} cm3 | stopy {contact_area(ms):.0f} mm2")
        report_overhang(ms, "gladki")
        del ms
    F2 = knit.knit_F(F, axes, a.vox, p=a.stitch, q=a.row, A=a.amp)
    del F
    note = f"jelen knitted (dzianina): oczka {a.stitch} x {a.row} mm, wypuklosc {a.amp} mm, wysokosc {a.h:.0f} mm, bez podpor"
    m = finish(F2, axes, a.vox, name, note, target=a.target)
    print(f"knitted: {m.extents.round(1)} mm | V {m.volume / 1000:.1f} cm3 (~{m.volume * 1.27 / 1000:.0f} g PETG @100%) | stopy {contact_area(m):.0f} mm2 ({time.time() - t0:.0f} s)")
    if a.check:
        report_overhang(m, "knitted")


if __name__ == "__main__":
    main()
