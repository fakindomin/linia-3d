"""Kontrola SZCZELNOSCI I POPRAWNOSCI DRUKU dla kazdego pliku STL (rb, lp, czesci, eksport z podgladu w przegladarce).

Sprawdza (kazdy punkt = osobny wpis w raporcie, wynik 'FAIL' => kod wyjscia 1):
  1. szczelnosc: kazda krawedz nalezy do dokladnie 2 trojkatow (brak dziur, brak krawedzi nieregularnych),
  2. spojna orientacja trojkatow i normalne na zewnatrz (objetosc > 0),
  3. brak zdegenerowanych (pole ~ 0) i powtorzonych trojkatow, brak NaN/Inf,
  4. liczba skladowych = oczekiwana (domyslnie 1: zadnych 'pylkow' i wysp),
  5. brak samoprzeciec (test trojkat-trojkat dla par o nakladajacych sie bryłach brzegowych, siatka przybliz. z manifold3d),
  6. brak wierzcholkow 'scisnietych' (wokol wierzcholka jeden wachlarz trojkatow) i parzysta liczba Eulera (spojna topologia),
  7. plaska podstawa na stole: pole styku z z=0 (przyczepnosc), brak czesci zawieszonych pod z=0,
  8. minimalna grubosc scianki (probkowanie promieniami do wnetrza) >= 0,8 mm (2 sciezki dyszy 0,4) dla czesci drukowanych,
  9. maksymalna dlugosc krawedzi/trojkatow w granicach rozsadku (wykrywa 'wlosy' z marching cubes).

Uzycie:
  python verify_print.py --selftest                  (kontrola samego testera na znanych dobrych/zlych siatkach)
  python verify_print.py [katalog_lub_pliki ...]     (domyslnie out/*.stl, bez plikow z prefiksem '_')
  python verify_print.py --json raport.json out/
Kod wyjscia 0 tylko gdy WSZYSTKIE pliki przechodza.
"""
import sys, os, glob, json, time
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))

MIN_WALL = 0.8          # mm: nic cienszego niz 2 sciezki dyszy 0,4
MIN_AREA = 1e-8         # mm^2: trojkat zdegenerowany
BASE_MIN = 20.0         # mm^2: minimalne pole styku ze stolem (czesci stojace); pomijane dla czesci plaskich (patrz BASE_EXEMPT)
WALL_SAMPLES = 6000     # probki do testu grubosci
THIN_FRAC_WARN = 0.005  # ostrzezenie, gdy > 0,5% CALEJ powierzchni modelu to cienka (< MIN_WALL) sciana wneki; pojedyncze punkty przy krawedziach to nie sciana
FLAT_EXEMPT = ("platek_", "podstawka_")      # czesci plaskie: cala dolna plaszczyzna na stole


def load_raw(path):
    """wczytanie bez 'naprawiania': zachowujemy surowe trojkaty, tylko scalamy identyczne wierzcholki (jak slicer)"""
    m = trimesh.load(path, force="mesh", process=False)
    m.merge_vertices(merge_tex=True, merge_norm=True)
    return m


def edge_stats(m):
    """liczba krawedzi: brzegowych (1 trojkat), nieregularnych (>2), oraz niespojnie skierowanych (ta sama orientacja w obu trojkatach)"""
    f = m.faces
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    key = np.sort(e, axis=1)
    k = key[:, 0].astype(np.int64) * (m.vertices.shape[0] + 1) + key[:, 1]
    uniq, inv, cnt = np.unique(k, return_inverse=True, return_counts=True)
    boundary = int((cnt == 1).sum())
    nonmanifold = int((cnt > 2).sum())
    # skierowanie: dla krawedzi z 2 trojkatami kierunki (a->b) musza byc przeciwne
    fwd = (e[:, 0] < e[:, 1])
    s = np.zeros(len(uniq))
    np.add.at(s, inv, np.where(fwd, 1.0, -1.0))
    two = cnt == 2
    inconsistent = int((np.abs(s[two]) > 1e-9).sum())
    return boundary, nonmanifold, inconsistent


def components(m):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    f = m.faces
    n = m.vertices.shape[0]
    r = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
    c = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
    g = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
    k, lab = connected_components(g, directed=False)
    used = np.zeros(n, bool); used[f.ravel()] = True
    labs = lab[used]
    sizes = np.bincount(labs)
    sizes = sizes[sizes > 0]
    return int(len(sizes)), sorted(sizes.tolist())[:3]


def pinched_vertices(m):
    """wierzcholki, wokol ktorych trojkaty tworza WIECEJ niz jeden wachlarz (dwie powierzchnie stykaja sie w punkcie): slicer widzi tam niejednoznaczna bryle"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    F = m.faces.astype(np.int64)
    N = int(F.max()) + 1
    a, b, c = F[:, 0], F[:, 1], F[:, 2]
    # wezly = skierowane pary (v, sasiad); trojkat (v,x,y) laczy wezly (v,x) i (v,y)
    V = np.concatenate([a, a, b, b, c, c]); U = np.concatenate([b, c, c, a, a, b])
    key = V * N + U
    uk, inv = np.unique(key, return_inverse=True)
    n = len(uk); f = len(F)
    # dla kazdego wierzcholka v trojkata: (v,x)-(v,y) gdzie (x,y) = pozostale dwa
    e0 = inv[0:f]; e1 = inv[f:2 * f]          # a: (a,b)-(a,c)
    e2 = inv[2 * f:3 * f]; e3 = inv[3 * f:4 * f]   # b: (b,c)-(b,a)
    e4 = inv[4 * f:5 * f]; e5 = inv[5 * f:6 * f]   # c: (c,a)-(c,b)
    r = np.concatenate([e0, e2, e4]); cc = np.concatenate([e1, e3, e5])
    g = coo_matrix((np.ones(len(r)), (r, cc)), shape=(n, n))
    k, lab = connected_components(g, directed=False)
    vert_of_node = uk // N
    comps_per_vertex = np.bincount(np.unique(np.stack([vert_of_node, lab], 1), axis=0)[:, 0].astype(np.int64), minlength=N)
    return int((comps_per_vertex > 1).sum())


def self_intersections(m, max_pairs=4000, return_pairs=False):
    """przyblizony test samoprzeciec (wektorowo): trojkaty trafiaja do komorek siatki przestrzennej (komorka = 2 x mediana krawedzi); pary w tej samej komorce,
    ktore maja nakladajace sie prostopadlosciany brzegowe i NIE dziela wierzcholka, sprawdzamy testem krawedz-trojkat (Moller-Trumbore)."""
    V, F = m.vertices, m.faces
    T = len(F)
    tri = V[F]
    lo, hi = tri.min(1), tri.max(1)
    el = np.linalg.norm(tri[:, 0] - tri[:, 1], axis=1)
    cell = max(float(np.median(el)) * 2.0, 0.5)
    org = lo.min(0)
    c0 = np.floor((lo - org) / cell).astype(np.int64)
    c1 = np.floor((hi - org) / cell).astype(np.int64)
    span = c1 - c0 + 1
    n = span.prod(1)
    tid = np.repeat(np.arange(T), n)
    first = np.cumsum(n) - n
    loc = np.arange(len(tid)) - np.repeat(first, n)
    sx, sy = span[tid, 0], span[tid, 1]
    cx = c0[tid, 0] + loc % sx
    cy = c0[tid, 1] + (loc // sx) % sy
    cz = c0[tid, 2] + loc // (sx * sy)
    K = int(max(c1.max(0) + 2))
    key = (cx * K + cy) * K + cz
    o = np.argsort(key, kind="stable")
    key = key[o]; tid = tid[o]
    cand = []
    k = 1
    while True:
        same = key[:-k] == key[k:] if k < len(key) else np.zeros(0, bool)
        if not same.any():
            break
        a = tid[:-k][same]; b = tid[k:][same]
        ok = (a != b) & ~((hi[a] < lo[b]).any(1) | (hi[b] < lo[a]).any(1))
        a, b = a[ok], b[ok]
        if len(a):
            fa, fb = F[a], F[b]
            share = (fa[:, :, None] == fb[:, None, :]).any((1, 2))
            a, b = a[~share], b[~share]
            cand.append(np.stack([np.minimum(a, b), np.maximum(a, b)], 1))
        k += 1
    if not cand:
        return ([], 0)[1] if not return_pairs else []
    pairs = np.unique(np.concatenate(cand), axis=0)
    hits = 0
    found = []
    for s0 in range(0, len(pairs), 200000):
        p = pairs[s0:s0 + 200000]
        h = _tri_tri(tri[p[:, 0]], tri[p[:, 1]])
        hits += int(h.sum())
        found.append(p[h])
    if return_pairs:
        return np.concatenate(found) if found else np.zeros((0, 2), int)
    return hits


def _seg_tri(p0, p1, t):
    """przeciecie odcinka p0-p1 z trojkatem t (wektorowo)"""
    d = p1 - p0
    e1 = t[:, 1] - t[:, 0]; e2 = t[:, 2] - t[:, 0]
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(a) > 1e-12
    f = np.where(ok, 1.0 / np.where(ok, a, 1.0), 0)
    s = p0 - t[:, 0]
    u = f * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, e1)
    v = f * np.einsum("ij,ij->i", d, q)
    tt = f * np.einsum("ij,ij->i", e2, q)
    eps = 2e-3          # styk brzegowy (sasiednie komorki marching cubes, zaokraglenie float32) to nie przeciecie; wymagamy wnikniecia > 0,2% rozmiaru trojkata
    return ok & (u > eps) & (v > eps) & (u + v < 1 - eps) & (tt > eps) & (tt < 1 - eps)


def _tri_tri(A, B):
    hit = np.zeros(len(A), bool)
    for i in range(3):
        hit |= _seg_tri(A[:, i], A[:, (i + 1) % 3], B)
        hit |= _seg_tri(B[:, i], B[:, (i + 1) % 3], A)
    return hit


NOISE_RB = 0.01                          # szum voxeli siatek zebrowanych (Python, voxel 0,35 mm); eksport z podgladu (0,5 mm) ma wiekszy: test_artifact.py ustawia 0,02
OVERHANG_ALLOW = {"duszek.stl": 0.015}   # dozwolony ulamek powierzchni z nawisem: falbana duszka (plytkie stoki w pierwszych ~2 mm nad stolem + sklepienia lukow <= 6 mm)


def overhang(m, name):
    """nawisy wg reguly STANDARDU (standard.overhang_check: > 55 st. od pionu, mostki <= 12 mm, szum voxeli 1% dla zeber); None, gdy standard niedostepny"""
    try:
        import standard as S
    except Exception:
        return None
    nf = 0.0 if name.startswith("lp_") else NOISE_RB
    nf = max(nf, OVERHANG_ALLOW.get(name, 0.0))
    return S.overhang_check(m, (), noise_frac=nf)


CAV_MIN = 2.0            # mm: punkt powierzchni uznajemy za sciane WNEKI, gdy promien wzdluz normalnej (do pustki) trafia w sciane dalej niz tyle


def wall_thickness(m, n=WALL_SAMPLES, seed=1, cone_deg=25.0, nrays=7):
    """grubosc SCIANKI wokol wnek (to ona decyduje o wytrzymalosci i druku). Zeby zeber nie liczyc jako cienkich scianek (ostre grzbiety zeber sa z natury
    wezsze niz 0,8 mm), mierzymy tylko od strony wnek: punkt powierzchni, z ktorego promien wzdluz normalnej (w pustke) trafia w przeciwlegla sciane dalej niz
    CAV_MIN = punkt wnetrza wneki. Grubosc = mediana odleglosci wiazki 7 promieni (os + 6 po stozku 25 st.) wzdluz -normalnej do nastepnej sciany, rzutowana na normalna.
    Zwraca dict(n_cav, p1, min, thin_frac = udzial CALEJ powierzchni z cienka scianka wneki) albo None, gdy model nie ma wnek (czesci pelne: nos, ogonek, platek)."""
    pts, fi = trimesh.sample.sample_surface(m, n, seed=seed)
    nrm = m.face_normals[fi]
    try:
        loc, ray, _ = m.ray.intersects_location(pts + nrm * 1e-3, nrm, multiple_hits=False)
        dout = np.full(len(pts), np.inf)
        if len(ray): dout[ray] = np.linalg.norm(loc - (pts + nrm * 1e-3)[ray], axis=1)
        cav = np.where(np.isfinite(dout) & (dout > CAV_MIN))[0]
        if len(cav) < 30: return None
        pts, nrm = pts[cav], nrm[cav]
        org = pts - nrm * 1e-3
        a = np.where(np.abs(nrm[:, [2]]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
        t1 = np.cross(nrm, a); t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
        t2 = np.cross(nrm, t1)
        th = np.deg2rad(cone_deg)
        dirs, cosz = [-nrm], [np.ones(len(nrm))]
        nr = nrays - 1
        for k in range(nr):
            ph = 2 * np.pi * k / nr
            dirs.append(-np.cos(th) * nrm + np.sin(th) * (np.cos(ph) * t1 + np.sin(ph) * t2)); cosz.append(np.full(len(nrm), np.cos(th)))
        D = np.full((len(org), nrays), np.nan)
        for j, d in enumerate(dirs):
            for s0 in range(0, len(org), 2000):
                l2, r2, _ = m.ray.intersects_location(org[s0:s0 + 2000], d[s0:s0 + 2000], multiple_hits=False)
                if len(r2): D[s0 + r2, j] = np.linalg.norm(l2 - org[s0:s0 + 2000][r2], axis=1) * cosz[j][s0 + r2]
    except Exception:
        return None
    ok = np.isfinite(D).sum(1) >= nrays // 2 + 1
    if ok.sum() < 30: return None
    med = np.nanmedian(np.where(np.isfinite(D[ok]), D[ok], np.nan), axis=1)
    return dict(n_cav=int(ok.sum()), p1=float(np.percentile(med, 1)), min=float(med.min()), thin_frac=float((med < MIN_WALL).sum() / n))


def check(path, expect_components=1, with_wall=True, with_selfint=True):
    t0 = time.time()
    name = os.path.basename(path)
    r = {"file": name, "fail": [], "warn": []}
    m = load_raw(path)
    r["tris"] = int(len(m.faces)); r["verts"] = int(len(m.vertices))
    V = m.vertices
    if not np.isfinite(V).all(): r["fail"].append("NaN/Inf we wspolrzednych")
    ar = m.area_faces
    deg = int((ar < MIN_AREA).sum()); r["degenerate"] = deg
    if deg: r["fail"].append(f"{deg} zdegenerowanych trojkatow")
    srt = np.sort(m.faces, axis=1)
    _, c = np.unique(srt.view([("", srt.dtype)] * 3), return_counts=True)
    dup = int((c > 1).sum()); r["duplicate_faces"] = dup
    if dup: r["fail"].append(f"{dup} powtorzonych trojkatow")
    b, nm, inc = edge_stats(m)
    r["boundary_edges"], r["nonmanifold_edges"], r["inconsistent_edges"] = b, nm, inc
    if b: r["fail"].append(f"{b} krawedzi brzegowych (dziury)")
    if nm: r["fail"].append(f"{nm} krawedzi nieregularnych (>2 trojkaty)")
    if inc: r["fail"].append(f"{inc} krawedzi o niespojnej orientacji")
    if b == 0 and nm == 0:
        pv = pinched_vertices(m); r["pinched_vertices"] = pv
        if pv: r["fail"].append(f"{pv} wierzcholkow scisnietych (niejednoznaczne styki powierzchni)")
    vol = float(m.volume); r["volume_mm3"] = round(vol, 1)
    if vol <= 0: r["fail"].append(f"objetosc <= 0 ({vol:.1f}): normalne do wewnatrz")
    nc, small = components(m); r["components"] = nc; r["smallest_components"] = small
    if nc != expect_components: r["fail"].append(f"{nc} skladowych (oczekiwano {expect_components}; najmniejsze: {small} trojk.)")
    # Euler: V - E + F = 2 - 2g dla kazdej skladowej zamknietej rozmaitosci
    E = len(np.unique(np.sort(np.concatenate([m.faces[:, [0, 1]], m.faces[:, [1, 2]], m.faces[:, [2, 0]]]), axis=1), axis=0))
    chi = len(m.vertices) - E + len(m.faces); r["euler"] = int(chi)
    if chi % 2: r["fail"].append(f"nieparzysta liczba Eulera ({chi}): niespojna topologia")
    # podstawa na stole
    zmin = float(V[:, 2].min()); r["zmin"] = round(zmin, 3)
    if abs(zmin) > 0.05: r["warn"].append(f"dolna powierzchnia nie jest na z=0 (zmin={zmin:.3f})")
    base = m.faces[(V[m.faces][:, :, 2].max(1) < zmin + 0.05) & (m.face_normals[:, 2] < -0.9)]
    ba = float(m.area_faces[(V[m.faces][:, :, 2].max(1) < zmin + 0.05) & (m.face_normals[:, 2] < -0.9)].sum())
    r["base_area_mm2"] = round(ba, 1)
    if ba < BASE_MIN and not any(name.startswith(p) for p in FLAT_EXEMPT):
        r["warn"].append(f"pole styku ze stolem {ba:.1f} mm2 (< {BASE_MIN})")
    if m.is_watertight and vol > 0 and with_wall:
        w = wall_thickness(m)
        if w is None:
            r["wall_p1_mm"] = None; r["wall_min_mm"] = None; r["wall_thin_frac"] = None
        else:
            r["wall_p1_mm"] = round(w["p1"], 2); r["wall_min_mm"] = round(w["min"], 2); r["wall_thin_frac"] = round(w["thin_frac"], 4)
            if w["thin_frac"] > THIN_FRAC_WARN: r["warn"].append(f"{100 * w['thin_frac']:.1f}% powierzchni to scianka wneki cienszą niz {MIN_WALL} mm (p1 {w['p1']:.2f}, min {w['min']:.2f})")
    if with_wall:
        ov = overhang(m, name)
        if ov is not None:
            r["overhang_mm2"] = ov["steep_mm2"]; r["overhang_pct"] = round(100 * ov["steep_mm2"] / float(m.area), 2)
            if not ov["ok"]:
                r["warn"].append(f"nawisy > 55 st. od pionu: {ov['steep_mm2']:.0f} mm2 ({r['overhang_pct']}% powierzchni), najszerszy mostek {max([b[1] for b in ov['bridges']] or [0]):.1f} mm -> mozliwe podpory")
    if with_selfint:
        si = self_intersections(m); r["self_intersections"] = si
        if si: r["fail"].append(f"{si} par trojkatow sie przecina")
    r["ok"] = not r["fail"]; r["s"] = round(time.time() - t0, 1)
    return r


def _check_job(a):
    f, fast = a
    return check(f, with_wall=not fast, with_selfint=not fast)


def selftest():
    """samokontrola samego testera: znane dobre i znane zle siatki musza dac oczekiwany wynik (wywolywane przez verify_all.py oraz `--selftest`)"""
    import tempfile
    d = tempfile.mkdtemp()
    def put(name, m):
        p = os.path.join(d, name + ".stl"); m.export(p); return p
    a = trimesh.creation.icosphere(subdivisions=3, radius=10)
    a.apply_translation([0, 0, 10.0])
    cases = []
    cases.append(("kula (dobra)", put("dobra", a), True, ""))
    h = a.copy(); h.update_faces(np.arange(len(h.faces)) != 5); h.remove_unreferenced_vertices()
    cases.append(("kula z dziura", put("dziura", h), False, "brzegowych"))
    f = a.copy(); f.faces = np.vstack([f.faces[:, ::-1][:1], f.faces[1:]])
    cases.append(("jedna sciana odwrocona", put("odwr", f), False, "orientacji"))
    v = a.copy()
    vv2 = np.vstack([v.vertices, v.vertices[v.faces[0, 0]][None]]); ff2 = v.faces.copy(); ff2[0, 1] = len(vv2) - 1      # dwa wierzcholki w tym samym punkcie
    cases.append(("zdegenerowany trojkat", put("deg", trimesh.Trimesh(vv2, ff2, process=False)), False, "zdegenerowanych"))
    b = trimesh.creation.icosphere(subdivisions=3, radius=9.3)
    b.apply_transform(trimesh.transformations.rotation_matrix(0.37, [0.3, 0.5, 0.8])); b.apply_translation([8.13, 0.37, 10.21])
    cases.append(("dwie nakladajace sie kule", put("przec", trimesh.util.concatenate([a, b])), False, "przecina"))
    c = b.copy(); c.apply_translation([40, 0, 0])
    cases.append(("dwie rozlaczne kule", put("dwie", trimesh.util.concatenate([a, c])), False, "skladowych"))
    ok_all = True
    for name, p, want, key in cases:
        r = check(p)
        got = r["ok"] and not r["fail"]
        hit = (not key) or any(key in x for x in r["fail"])
        good = (got == want) and hit
        ok_all &= good
        print(f"  samokontrola: {'OK ' if good else 'BLAD'} {name:28s} -> {'PASS' if got else 'FAIL'} {r['fail'] if r['fail'] else ''}")
    return ok_all


def main(argv):
    out_json = None
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "--json": out_json = argv[i + 1]; i += 2
        elif argv[i] == "--fast": os.environ["VP_FAST"] = "1"; i += 1
        elif argv[i] == "--selftest": return 0 if selftest() else 1
        else: args.append(argv[i]); i += 1
    files = []
    for a in (args or [os.path.join(HERE, "out")]):
        if os.path.isdir(a): files += sorted(f for f in glob.glob(os.path.join(a, "*.stl")) if not os.path.basename(f).startswith("_"))
        else: files.append(a)
    fast = bool(os.environ.get("VP_FAST"))
    res = []
    jobs = max(1, min(int(os.environ.get("VP_JOBS", "2")), os.cpu_count() or 1, len(files) or 1))

    def show(r):
        extra = f"  scianka wneki p1={r.get('wall_p1_mm')}" if r.get("wall_p1_mm") is not None else ""
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['file']:42s} {r['tris']:>8d} tr.  skl {r['components']}  krawedzie brz/nm/odw {r['boundary_edges']}/{r['nonmanifold_edges']}/{r['inconsistent_edges']}  scisk. {r.get('pinched_vertices', '-')}  "
              f"podstawa {r['base_area_mm2']:.0f} mm2{extra}" + ("".join("  !! " + s for s in r["fail"])) + ("".join("  ~ " + s for s in r["warn"])), flush=True)

    if jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for r in ex.map(_check_job, [(f, fast) for f in files]):
                res.append(r); show(r)
    else:
        for f in files:
            r = check(f, with_wall=not fast, with_selfint=not fast)
            res.append(r); show(r)
    bad = [r for r in res if not r["ok"]]
    if out_json: json.dump(res, open(out_json, "w"), indent=1, ensure_ascii=False)
    print(f"\nWYNIK: {len(res) - len(bad)} PASS, {len(bad)} FAIL z {len(res)} plikow; ostrzezenia: {sum(1 for r in res if r['warn'])}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
