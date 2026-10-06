"""Usuwanie zdegenerowanych trojkatow (pole ~ 0) BEZ psucia szczelnosci i topologii.

Skad sie biora: marching cubes / zaokraglenie do float32 daje mikro-trojkaty (wszystkie 3 wierzcholki w odleglosci < 0,002 mm)
i rzadziej 'igly' (3 wierzcholki prawie wspolliniowe). Slicer je zwykle toleruje, ale walidatory (Bambu/Prusa/Cura 'repair',
Windows 3D Builder) zglaszaja je jako bledy, a wlasna kontrola (verify_print.py) liczy je jako FAIL.

Metoda (dziala na siatce zamknietej, 2-rozmaitosciowej; nigdy jej nie otwiera):
  * mikro-trojkat (najdluzsza krawedz <= MICRO) -> zwijamy najkrotsza krawedz (v -> u), tylko gdy spelniony warunek 'link condition'
    (zwiniecie nie tworzy krawedzi nieregularnych ani nie skleja przeciwleglych scian) i zadna sasiednia sciana sie nie odwraca,
  * igla (dluga krawedz) -> przeklucie najdluzszej krawedzi (flip): (a,b,c)+(a,c,d) -> (a,b,d)+(b,c,d); geometria bez zmian, bo b lezy na odcinku a-c;
    gdy flip niemozliwy -> zwiniecie najkrotszej krawedzi.
Wierzcholki po operacji maja dokladnie te same wspolrzedne float32 co przed (nie tworzymy nowych punktow).
"""
import numpy as np
import trimesh

MIN_AREA = 1e-8        # mm^2 (jak w verify_print.py)
MICRO = 0.05           # mm: trojkat o wszystkich krawedziach <= MICRO traktujemy jako mikro-trojkat


def _areas(V, F):
    a = V[F[:, 1]] - V[F[:, 0]]
    b = V[F[:, 2]] - V[F[:, 0]]
    c = np.cross(a, b)
    return 0.5 * np.linalg.norm(c, axis=1), c


def _tri_n(V, f):
    c = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
    return c, 0.5 * np.linalg.norm(c)


class _Mesh:
    """minimalna struktura topologii: sciany + zbiory scian przy wierzcholku"""

    def __init__(self, V, F):
        self.V = V
        Fa = np.asarray(F, np.int64)
        self.F = [tuple(int(x) for x in f) for f in Fa]
        self.alive = [True] * len(self.F)
        # CSR wierzcholek -> sciany (zbiory budujemy leniwie, tylko dla wierzcholkow, ktorych dotykamy)
        v = Fa.ravel(); fi = np.repeat(np.arange(len(Fa)), 3)
        o = np.argsort(v, kind="stable")
        self.idx = fi[o]
        self.ptr = np.searchsorted(v[o], np.arange(len(V) + 1))
        self.vfd = {}

    def vfs(self, v):
        s = self.vfd.get(v)
        if s is None:
            s = {int(i) for i in self.idx[self.ptr[v]:self.ptr[v + 1]] if self.alive[i] and v in self.F[i]}
            self.vfd[v] = s
        return s

    def nbrs(self, v):
        s = set()
        for i in self.vfs(v):
            s.update(self.F[i])
        s.discard(v)
        return s

    def edge_faces(self, u, v):
        return [i for i in self.vfs(u) if v in self.F[i]]

    def opposite(self, i, u, v):
        return [x for x in self.F[i] if x != u and x != v][0]

    # ---- zwiniecie krawedzi v -> u -------------------------------------------------------------------------
    def can_collapse(self, u, v):
        ef = self.edge_faces(u, v)
        if len(ef) != 2:
            return False
        opp = {self.opposite(i, u, v) for i in ef}
        if len(opp) != 2:
            return False
        if self.nbrs(u) & self.nbrs(v) != opp:          # link condition
            return False
        # zadna z pozostalych scian wokol v nie moze sie odwrocic ani zdegenerowac gorzej
        for i in self.vfs(v):
            if i in ef:
                continue
            f = self.F[i]
            g = tuple(u if x == v else x for x in f)
            c0, a0 = _tri_n(self.V, f)
            c1, a1 = _tri_n(self.V, g)
            if a1 < MIN_AREA and a0 >= MIN_AREA:        # zwiniecie nie moze tworzyc nowych zdegenerowanych
                return False
            if a0 >= MIN_AREA and float(np.dot(c0, c1)) <= 0.2 * np.linalg.norm(c0) * np.linalg.norm(c1) * (a1 >= MIN_AREA):
                return False
        return True

    def collapse(self, u, v):
        ef = set(self.edge_faces(u, v))
        for i in ef:
            self.alive[i] = False
            for x in self.F[i]:
                self.vfs(x).discard(i)
        for i in list(self.vfs(v)):
            f = self.F[i]
            g = tuple(u if x == v else x for x in f)
            self.F[i] = g
            self.vfs(u).add(i)
        self.vfd[v] = set()

    # ---- przeklucie krawedzi (a,c) w trojkacie i=(a,b,c) z sasiadem j=(a,c,d) --------------------------------
    def try_flip(self, i, a, c):
        ef = self.edge_faces(a, c)
        if len(ef) != 2:
            return False
        j = ef[0] if ef[1] == i else ef[1]
        b = self.opposite(i, a, c)
        d = self.opposite(j, a, c)
        if b == d or d in self.nbrs(b):                  # krawedz (b,d) juz istnieje -> flip stworzylby krawedz nieregularna
            return False
        fi, fj = self.F[i], self.F[j]
        # obrot fi do postaci (p,q,b), gdzie p->q to skierowana krawedz wspolna; wtedy fj = (q,p,d)
        k = [t for t in range(3) if {fi[t], fi[(t + 1) % 3]} == {a, c}][0]
        p, q = fi[k], fi[(k + 1) % 3]
        n1, n2 = (b, p, d), (d, q, b)                    # zachowuja skierowane krawedzie zewnetrzne: q->b, b->p, p->d, d->q
        c1, a1 = _tri_n(self.V, n1)
        c2, a2 = _tri_n(self.V, n2)
        cj, aj = _tri_n(self.V, fj)
        if a1 < MIN_AREA or a2 < MIN_AREA:
            return False
        if aj >= MIN_AREA and (np.dot(c1, cj) <= 0 or np.dot(c2, cj) <= 0):
            return False
        for f_, idx in ((n1, i), (n2, j)):
            for x in self.F[idx]:
                self.vfs(x).discard(idx)
            self.F[idx] = f_
            for x in f_:
                self.vfs(x).add(idx)
        return True


def clean_degenerate(m, area_tol=MIN_AREA, max_rounds=40, verbose=False):
    """zwraca (mesh, info); mesh = kopia bez zdegenerowanych trojkatow (jesli sie da), nigdy nie pogarsza szczelnosci.
    info = dict(before, after, collapsed, flipped, watertight_before, watertight_after, dvol)"""
    m = m.copy()
    V = np.asarray(m.vertices, np.float64)
    V = V.astype(np.float32).astype(np.float64)          # to, co zapisze STL
    F = np.asarray(m.faces, np.int64)
    ar, _ = _areas(V, F)
    before = int((ar < area_tol).sum())
    wt0 = bool(trimesh.Trimesh(V, F, process=False).is_watertight)
    info = dict(before=before, collapsed=0, flipped=0, watertight_before=wt0)
    if before == 0:
        info.update(after=0, watertight_after=wt0, dvol=0.0)
        return trimesh.Trimesh(V, F, process=False), info
    vol0 = trimesh.Trimesh(V, F, process=False).volume
    T = _Mesh(V, F)
    cand = None
    for rnd in range(max_rounds):
        if cand is None:
            bad = [int(i) for i in np.where(ar < area_tol)[0]]
        else:
            bad = [i for i in cand if T.alive[i] and _tri_n(V, T.F[i])[1] < area_tol]
        if not bad:
            break
        progress = 0
        for i in bad:
            if not T.alive[i]:
                continue
            f = T.F[i]
            if _tri_n(V, f)[1] >= area_tol:
                continue
            e = [(float(np.linalg.norm(V[f[k]] - V[f[(k + 1) % 3]])), f[k], f[(k + 1) % 3]) for k in range(3)]
            e.sort()
            micro = e[2][0] <= MICRO
            done = False
            if not micro:                                # igla: flip najdluzszej krawedzi
                L, x, y = e[2]
                if T.try_flip(i, x, y):
                    info["flipped"] += 1; progress += 1; done = True
            if not done:
                for L, x, y in e:                        # zwijamy od najkrotszej
                    if T.can_collapse(x, y):
                        T.collapse(x, y); info["collapsed"] += 1; progress += 1; done = True
                        break
                    if T.can_collapse(y, x):
                        T.collapse(y, x); info["collapsed"] += 1; progress += 1; done = True
                        break
        if verbose:
            print(f"  runda {rnd}: zle {len(bad)} -> usuniete/naprawione {progress}")
        cand = bad
        if progress == 0:
            break
    Fn = np.array([f for i, f in enumerate(T.F) if T.alive[i]], np.int64)
    out = trimesh.Trimesh(V, Fn, process=False)
    out.remove_unreferenced_vertices()
    ar, _ = _areas(np.asarray(out.vertices), np.asarray(out.faces))
    info["after"] = int((ar < area_tol).sum())
    info["watertight_after"] = bool(out.is_watertight)
    info["dvol"] = float(out.volume - vol0)
    if wt0 and not out.is_watertight:                    # nie wolno pogorszyc: zwracamy oryginal
        info["rejected"] = True
        return trimesh.Trimesh(V, F, process=False), info
    return out, info
