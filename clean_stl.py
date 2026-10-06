"""Czyszczenie istniejacych STL (usuniecie zdegenerowanych trojkatow) w miejscu, bez zmiany szczelnosci.
Uzycie: python clean_stl.py [plik_lub_katalog ...]     (domyslnie out/*.stl bez plikow z prefiksem '_')
Pliki z bledem szczelnosci po czyszczeniu sa pomijane (zostaje oryginal)."""
import sys, os, glob, time
import trimesh
from meshclean import clean_degenerate

HERE = os.path.dirname(os.path.abspath(__file__))


def collect(args):
    if not args:
        args = [os.path.join(HERE, "out")]
    files = []
    for a in args:
        files += sorted(glob.glob(os.path.join(a, "*.stl"))) if os.path.isdir(a) else [a]
    return [f for f in files if not os.path.basename(f).startswith("_")]


def main(args):
    n_fix = 0
    for f in collect(args):
        m = trimesh.load(f, force="mesh", process=False)
        m.merge_vertices(merge_tex=True, merge_norm=True)
        t = time.time()
        o, info = clean_degenerate(m)
        if info["before"] == 0:
            continue
        ok = info["after"] == 0 and info["watertight_after"] and not info.get("rejected")
        print(f"{os.path.basename(f):34s} zle {info['before']:3d} -> {info['after']:3d} | zwiniete {info['collapsed']:3d}, flip {info['flipped']} | "
              f"dV {info['dvol']:+.1e} mm3 | {time.time()-t:4.1f}s | {'OK' if ok else 'POMINIETO'}")
        if ok:
            o.export(f)
            n_fix += 1
    print(f"poprawiono plikow: {n_fix}")


if __name__ == "__main__":
    main(sys.argv[1:])
