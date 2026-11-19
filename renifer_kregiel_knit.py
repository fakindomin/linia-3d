"""Renifer KREGIEL 'knitted': ten sam renifer co w renifer_kregiel.py (smukly korpus-kregiel, jajowata glowa, poroze o 3 poziomach, boczne uszy-liscie),
ale zamiast pionowych zeber skora z rzedow oczek (knit.py). Jeden wydruk: poroze i uszy przytopione do glowy, bez podpor, dnem do stolu.
  python3 renifer_kregiel_knit.py              -> out/renifer_kregiel_knit.stl (+ .png podglad)
  python3 renifer_kregiel_knit.py --stitch 5 --row 4 --amp 0.6   (grubsze oczka)
  python3 renifer_kregiel_knit.py --check      -> dodatkowo nawisy jak slicer (25 / 30 st.) w porownaniu z zebrowanym renifer_kregiel_calosc.stl
Gladki korpus = bunny_F z 0 zeber (promien profilu + amplituda zeber = grzbiety zeber), wiec szczyty oczek leza na wysokosci grzbietow zeber:
wymiar po grzbietach (54,6 mm) i pasowanie na tace (taca.py) zostaja takie jak w zebrowanym."""
import sys, os, time, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trimesh
import renifer_kregiel as RK
import nawisy
import knit
from lib import decimate, save, mesh_from_F, OUT


def smooth_field(vox):
    """gladki korpus (0 zeber) + poroza i uszy-liscie przytopione; zwraca osie i F"""
    P = {**RK.params(), "ribs": 0}
    axes, F = RK.body_field(P, vox, fuse_ant=True)
    return P, axes, F


def contact_area(m, z=0.1):
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return 0.0
    p2, _ = sec.to_2D()
    return float(sum(p.area for p in p2.polygons_full))


def report_overhang(m, label):
    for thr in (25.0, 30.0):
        o = nawisy.slicer_overhang(m, 0.2, thr)
        print(f"  {label}: slicer {thr:.0f} st.: nawis {o['area']:.1f} mm2 | wyspy w powietrzu {o['floating']:.2f} mm2 | najszersze {o['width']:.2f} mm (z = {o['z']:.1f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vox", type=float, default=0.25)
    ap.add_argument("--stitch", type=float, default=4.0, help="szerokosc oczka p [mm]")
    ap.add_argument("--row", type=float, default=3.2, help="wysokosc rzedu q [mm]")
    ap.add_argument("--amp", type=float, default=0.5, help="wysokosc wypuklosci oczek [mm]")
    ap.add_argument("--target", type=int, default=700000)
    ap.add_argument("--name", default="renifer_kregiel_knit.stl")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    P, axes, F = smooth_field(a.vox)
    F = (F - a.amp / 2).astype(np.float32)      # szczyty oczek = grzbiety zeber (R + amplituda zeber)
    print(f"gladki F {F.shape} ({time.time() - t0:.0f} s)")
    if a.check:
        ref = os.path.join(OUT, "renifer_kregiel_calosc.stl")
        if os.path.exists(ref):
            mr = trimesh.load(ref)
            print(f"zebrowany (wzorzec): {mr.extents.round(1)} mm | V {mr.volume / 1000:.1f} cm3 | stopy {contact_area(mr):.0f} mm2")
            report_overhang(mr, "zebrowany")
            del mr
    F2 = knit.knit_F(F, axes, a.vox, p=a.stitch, q=a.row, A=a.amp, renorm=True)
    del F
    m = mesh_from_F(F2, axes, a.vox)
    del F2
    m = decimate(m, a.target, label=a.name)
    save(m, a.name, True, f"renifer kregiel knitted: oczka {a.stitch} x {a.row} mm, wypuklosc {a.amp} mm, poroze i uszy przytopione, bez podpor")
    m = trimesh.load(os.path.join(OUT, a.name))
    print(f"knitted: {m.extents.round(1)} mm | V {m.volume / 1000:.1f} cm3 | stopy {contact_area(m):.0f} mm2 ({time.time() - t0:.0f} s)")
    if a.check:
        report_overhang(m, "knitted")
    return m


if __name__ == "__main__":
    main()
