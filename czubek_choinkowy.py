"""Czubek na choinkę (iglica jak na szklanych czubkach): tuleja na czubek drzewka, kula (bańka), wąska szyjka i długa iglica. Bryła obrotowa
z pionowymi żebrami linii (STANDARD: amplituda ±0,8 mm, rozstaw 3,4 mm, zanik żeber przy r <= 4 mm). Druk STOJĄCY (tuleja na stole), bez podpór:
  - profil r(z) = gładkie złożenie (smax/smin) kawałków: walec tulei -> stożek 49° (|dr/dz| = 1,15, zapas na żebra) -> elipsoida (kula spłaszczona, dolna połowa styczna do stożka)
    -> szyjka -> stożek 49° rozszerzający się do podstawy iglicy -> wklęsła iglica (potęga p) -> półkulista końcówka; wszędzie |dr/dz| <= 1,15 tam, gdzie
    powierzchnia patrzy w dół, więc żaden nawis nie przekracza 55° od pionu,
  - wnęka na czubek choinki: Ø TOP_D + 0,6 mm przez całą tuleję (walec SLEEVE mm), potem PUSTA KULA otwarta od dołu: wnętrze = zewnętrzny profil przesunięty
    do środka o WALL_T (2,7 mm, w dolinie żebra 1,9 mm), a nad równikiem strop stożkowy 52° do płaskiego sufitu r = 5 (mostek 10 mm) tuż pod szczytem kuli
    (CAP). Czubek choinki wchodzi więc do środka kuli, aż do ok. 11 cm od dołu przy domyślnych wymiarach,
  - żebra w trzech pasach (tuleja / kula / iglica) z płynnymi przejściami; N = round(2π·r/3,4) w każdym pasie (jak `rev.rib_field`).
Siatka jest liczona ANALITYCZNIE (obrót profilu, bez marching cubes): ten sam algorytm działa w artefakcie „Świąteczne dodatki” (artifact/swieta_core.js),
więc STL pobrany z przeglądarki = STL z tego skryptu.
Parametry: TOP_D (średnica czubka choinki), H (wysokość całkowita), D_B (średnica kuli), SLEEVE (długość walca tulei).
  python3 czubek_choinkowy.py [--top 18] [--h 240] [--bulb 62] [--sleeve 62]   -> out/czubek_choinkowy.stl
Zalecenie do slicera: obwódka (brim) zewnętrzna 8 mm, bo podstawa to pierścień ok. Ø 24 mm."""
import os, sys, math, time, argparse
import numpy as np
import trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from lib import RIB_AMP, RIB_PITCH

# ---- parametry (jedna definicja; artefakt ma te same wartości w swieta_core.js) ----
CLEAR = 0.3                      # luz wnęki na stronę [mm]
WALL_T = 2.7                     # ścianka tulei i pustej kuli, mierzona po normalnej (przed żebrami) [mm]
SLEEVE = 62.0                    # długość walca tulei (do początku stożka kuli) [mm]; było 22, teraz +40
CAP = 3.5                        # grubość pełnego szczytu nad sufitem wnęki, liczona od bieguna zewnętrznej kuli [mm]
CONE = 1.3                       # |dr/dz| stropu wnęki (52° od pionu, STANDARD)
CONE_OUT = 1.15                  # |dr/dz| stożków zewnętrznych (49° od pionu): zapas na żebra, które w przejściach i przy zaniku amplitudy dodają do nachylenia grzbietu do 0,27
R_FLAT = 5.0                     # promień płaskiego sufitu wnęki [mm]
BULB_FLAT = 0.85                 # pionowa / pozioma półoś kuli
NECK = 0.21                      # promień szyjki / promień kuli
SPIRE_BASE = 0.44                # promień podstawy iglicy / promień kuli
SPIRE_P = 2.2                    # wykładnik wklęsłości iglicy
R_TIP = 1.6                      # promień końcówki [mm]
L_NECK = 2.0                     # długość szyjki ponad kulą [mm]
K_NECK, K_SHOULDER = 2.5, 5.0    # wygładzenie: szyjka/kula, ramię iglicy [mm]
EPS_PROFILE = 0.01               # dopuszczalne odchylenie siatki od profilu [mm]
SEG_MAX, SEG_TRANS = 3.0, 0.6    # największy odstęp pierścieni; w przejściach żeber [mm]
PETG = 1.27
DEFAULTS = dict(top=18.0, h=240.0, bulb=62.0, sleeve=SLEEVE)


def smax(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.maximum(a, b) + h * h * k * 0.25


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def sstep(z, z0, z1):
    t = np.clip((z - z0) / (z1 - z0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def rib(N, th):
    c = np.cos(N * th)
    return np.sign(c) * np.abs(c) ** 0.8


def rib_amp(r, amp=RIB_AMP, r0=4.0, r1=10.0):
    return amp * np.clip((r - r0) / (r1 - r0), 0.0, 1.0)


class Geo:
    """geometria czubka: wszystkie wymiary z trzech parametrów"""

    def __init__(s, top=18.0, h=240.0, bulb=62.0, sleeve=SLEEVE):
        s.top, s.H = float(top), float(h)
        s.a = bulb / 2.0
        s.b = BULB_FLAT * s.a
        s.r_h = s.top / 2.0 + CLEAR                         # promień wnęki
        s.r_s = s.r_h + WALL_T                              # promień tulei
        s.Z0 = float(sleeve)                                # koniec walca tulei, początek stożka
        fa = s.a / s.b
        s.phi_j = math.atan(fa / CONE_OUT)                      # kąt na elipsie, gdzie stożek 49° jest styczny
        s.r_j = s.a * math.sin(s.phi_j)
        assert s.r_j - s.r_s > 1.0, "kula za mała względem tulei (zwiększ średnicę kuli)"
        s.z_j = s.Z0 + (s.r_j - s.r_s) / CONE_OUT
        s.z_e = s.z_j + s.b * math.cos(s.phi_j)             # równik kuli
        s.z_dome = s.z_e + s.b                              # biegun górny kuli
        s.k1 = min(6.0, 0.8 * (s.r_j - s.r_s))
        s.r_neck = max(NECK * s.a, 4.5)
        s.z_ns = s.z_dome + L_NECK                          # początek rozszerzenia nad szyjką
        s.r_b = max(SPIRE_BASE * s.a, s.r_neck + 3.0)       # podstawa iglicy
        s.z_sb = s.z_ns + (s.r_b - s.r_neck) / CONE_OUT
        assert s.H - s.z_sb > 40.0, "za niski czubek względem kuli (zwiększ wysokość lub zmniejsz kulę)"
        s.z_t = s.H - R_TIP                                 # środek końcówki
        # strefy przejść żeber: tuleja -> kula, kula -> iglica
        s.trans = [(s.Z0 + 1.0, s.z_j), (s.z_e + 0.80 * s.b, s.z_e + 0.96 * s.b)]
        s.Ns = [int(round(2 * math.pi * s.r_s / RIB_PITCH)), int(round(2 * math.pi * s.a / RIB_PITCH)), int(round(2 * math.pi * s.r_b / RIB_PITCH))]
        s.ceil = s.z_dome - CAP                             # z płaskiego sufitu wnęki (tuż pod szczytem kuli)

    def taper(s, z):
        t = (z - s.z_sb) / (s.z_t - s.z_sb)
        return R_TIP + (s.r_b - R_TIP) * np.clip(1.0 - t, 0.0, None) ** SPIRE_P

    def R(s, z):
        """promień zewnętrzny (bez żeber)"""
        z = np.asarray(z, float)
        ell = s.a * np.sqrt(np.clip(1.0 - ((z - s.z_e) / s.b) ** 2, 0.0, None))
        lower = np.where(z <= s.z_j, smax(s.r_s, s.r_s + CONE_OUT * (z - s.Z0), s.k1), ell)
        N = smin(smax(s.r_neck, s.r_neck + CONE_OUT * (z - s.z_ns), K_NECK), s.taper(z), K_SHOULDER)
        core = np.where(z < s.z_dome + 2.0, smax(lower, N, K_NECK), N)
        cap = np.where(z > s.z_t, np.sqrt(np.clip(R_TIP ** 2 - (z - s.z_t) ** 2, 0.0, None)), np.inf)
        return np.minimum(core, cap)

    def inner(s):
        """profil wnętrza (kula pusta, otwarta od dołu): zewnętrzny profil R(z) przesunięty po normalnej o WALL_T do punktu Q, w którym przecina go stożek stropu
        (|dr/dz| = CONE, od Q do płaskiego sufitu r = R_FLAT na z = s.ceil). Zwraca tablicę punktów (r, z) od (r_h, 0) do Q, uproszczoną (DP, odchylenie <= EPS_PROFILE,
        odcinki <= SEG_MAX). Nad Q wnętrze to prosty stożek (Q -> (R_FLAT, ceil))."""
        h = 0.02
        n = int(math.ceil(s.ceil / h))
        z = np.arange(n) * h
        R = s.R(z)
        d = np.gradient(R, h)
        L = np.sqrt(1.0 + d * d)
        rho = R - WALL_T / L
        zeta = z + WALL_T * d / L
        f = (R_FLAT + CONE * (s.ceil - zeta)) - rho
        ie = int(math.ceil(s.z_e / h))
        assert f[ie] > 0, "kula za mała na wnękę"
        k = ie + int(np.argmax(f[ie:] < 0))
        assert f[k] < 0, "strop wnęki nie przecina ścianki kuli (zwiększ kulę)"
        t = f[k - 1] / (f[k - 1] - f[k])
        Q = (rho[k - 1] + t * (rho[k] - rho[k - 1]), zeta[k - 1] + t * (zeta[k] - zeta[k - 1]))
        P = np.vstack([np.column_stack([rho[:k], zeta[:k]]), [Q]])
        keep = np.zeros(len(P), bool); keep[0] = keep[-1] = True
        stack = [(0, len(P) - 1)]
        while stack:
            i, j = stack.pop()
            if j <= i + 1:
                continue
            dd = P[j] - P[i]; nn = math.hypot(*dd)
            q = P[i + 1:j] - P[i]
            dist = np.abs(q[:, 0] * dd[1] - q[:, 1] * dd[0]) / nn
            kk = int(np.argmax(dist))
            if dist[kk] > EPS_PROFILE:
                keep[i + 1 + kk] = True
                stack += [(i, i + 1 + kk), (i + 1 + kk, j)]
        K = P[keep]
        out = [K[0]]
        for a, b in zip(K[:-1], K[1:]):
            m = int(math.ceil(math.hypot(*(b - a)) / SEG_MAX))
            out += [a + (b - a) * (i + 1) / m for i in range(m)]
        out = np.array(out)
        out[0] = (s.r_h, 0.0)
        return out

    def rib_field(s, th, Z):
        ws, w_prev = [], 1.0
        for za, zb in s.trans:
            st = sstep(Z, za, zb)
            ws.append(w_prev * (1 - st))
            w_prev = w_prev * st
        ws.append(w_prev)
        out = 0
        for w, N in zip(ws, s.Ns):
            out = out + w * rib(N, th)
        return out

    def rings(s):
        """z pierścieni: Douglas-Peucker po gęstym profilu (odchylenie <= EPS_PROFILE) + podział długich odcinków"""
        zz = np.linspace(0.0, s.H, int(s.H / 0.02) + 1)
        P = np.column_stack([s.R(zz), zz])
        keep = np.zeros(len(P), bool); keep[0] = keep[-1] = True
        stack = [(0, len(P) - 1)]
        while stack:
            i, j = stack.pop()
            if j <= i + 1:
                continue
            d = P[j] - P[i]; n = math.hypot(*d)
            q = P[i + 1:j] - P[i]
            dist = np.abs(q[:, 0] * d[1] - q[:, 1] * d[0]) / n if n > 0 else np.hypot(q[:, 0], q[:, 1])
            k = int(np.argmax(dist))
            if dist[k] > EPS_PROFILE:
                keep[i + 1 + k] = True
                stack += [(i, i + 1 + k), (i + 1 + k, j)]
        zs = list(zz[keep])
        out = [zs[0]]
        for z1 in zs[1:]:
            z0 = out[-1]
            in_tr = any(not (z1 < ta or z0 > tb) for ta, tb in s.trans)
            lim = SEG_TRANS if in_tr else SEG_MAX
            n = int(math.ceil((z1 - z0) / lim))
            out += [z0 + (z1 - z0) * (i + 1) / n for i in range(n)]
        return np.array(out)


def build(top=18.0, h=240.0, bulb=62.0, sleeve=SLEEVE):
    g = Geo(top, h, bulb, sleeve)
    zr = g.rings()
    r0 = g.R(zr)
    M = int(round(8 * g.Ns[1] / 2.0)) * 2                   # 8 punktów na żebro kuli
    th = np.arange(M) * (2 * math.pi / M)
    verts, faces = [], []

    def ring(r, z, ribs):
        n = len(verts)
        if r < 1e-3:
            verts.append((0.0, 0.0, float(z))); return ("axis", n)
        rr = r + (rib_amp(r) * g.rib_field(th, z) if ribs else 0.0)
        rr = np.broadcast_to(rr, th.shape)
        verts.extend(zip(rr * np.cos(th), rr * np.sin(th), np.full(M, z)))
        return ("ring", n)

    prof = [ring(g.r_h, 0.0, False)]                        # wnętrze, dół
    prof += [ring(r, z, True) for r, z in zip(r0, zr)]      # zewnętrzny profil od z = 0 do wierzchołka (r = 0 w z = H)
    ip = g.inner()                                           # (r_h, 0) ... Q
    prof += [ring(0.0, g.ceil, False), ring(R_FLAT, g.ceil, False)]
    prof += [ring(r, z, False) for r, z in ip[:0:-1]]       # od Q w dół (bez punktu (r_h, 0) = prof[0])
    J = np.arange(M)
    for A, B in zip(prof, prof[1:] + prof[:1]):             # krawędzie profilu CCW w (r, z): zewnętrzna normalna po prawej
        (ka, ia), (kb, ib) = A, B
        if ka == "axis" and kb == "axis":
            continue
        if ka == "axis":
            faces += list(zip([ia] * M, ib + (J + 1) % M, ib + J))      # P na osi: trójkąt (P, Q_{j+1}, Q_j)
            continue
        if kb == "axis":
            faces += list(zip(ia + J, ia + (J + 1) % M, [ib] * M))
            continue
        Pj, Pk, Qj, Qk = ia + J, ia + (J + 1) % M, ib + J, ib + (J + 1) % M
        faces += list(zip(Pj, Pk, Qj)) + list(zip(Pk, Qk, Qj))
    m = trimesh.Trimesh(np.array(verts), np.array(faces), process=False)
    m.merge_vertices()
    return m, g, M


def profile_slopes(g):
    """nawisy profilu: |dr/dz| tam, gdzie r rośnie z z (powierzchnia patrzy w dół); wnęka zawsze <= CONE"""
    z = np.arange(0.05, g.H - R_TIP, 0.02)
    d = np.gradient(g.R(z), z)
    return float(d.max()), float(z[int(np.argmax(d))])


def inner_curve(g, step=0.05):
    """gęsto próbkowany kontur wnętrza (r, z): od (r_h, 0) przez ściankę i stożek stropu do osi na suficie"""
    ip = g.inner()
    pts = np.vstack([ip, [[R_FLAT, g.ceil], [0.0, g.ceil]]])
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(1, int(math.ceil(math.hypot(*(b - a)) / step)))
        out += [a + (b - a) * (i + 1) / n for i in range(n)]
    return np.array(out), ip


def min_wall(g):
    """najmniejsza odległość wnętrza od zewnętrznej powierzchni w dolinie żebra (profil R minus amplituda żebra); w przekroju osiowym = grubość ścianki"""
    from scipy.spatial import cKDTree
    ic, _ = inner_curve(g)
    zo = np.arange(0.0, g.H, 0.02)
    ro = g.R(zo); ro = ro - rib_amp(ro)
    d, _ = cKDTree(np.column_stack([ro, zo])).query(ic)
    return float(d.min())


def inner_overhang(g):
    """największe |dr/dz| powierzchni wnętrza zwróconej w dół (r maleje ze wzrostem z): strop stożkowy <= CONE"""
    ic, _ = inner_curve(g)
    dz = np.diff(ic[:, 1]); dr = np.diff(ic[:, 0])
    m = (dz > 1e-9) & (dr < 0)
    return float((-dr[m] / dz[m]).max()) if m.any() else 0.0


def mass_est(V, A):
    """szacunek masy [g]: 3 obwiednie po obu stronach (ok. 1,2 mm na powierzchnię) pełne, reszta objętości 15% wypełnienia"""
    shell = min(V, A * 1.2)
    return (shell + 0.15 * max(V - shell, 0.0)) / 1000 * PETG


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=float, default=DEFAULTS["top"], help="średnica czubka choinki [mm]")
    ap.add_argument("--h", type=float, default=DEFAULTS["h"], help="wysokość całkowita [mm]")
    ap.add_argument("--bulb", type=float, default=DEFAULTS["bulb"], help="średnica kuli [mm]")
    ap.add_argument("--sleeve", type=float, default=DEFAULTS["sleeve"], help="długość walca tulei [mm]")
    ap.add_argument("--out", default=os.path.join(HERE, "out", "czubek_choinkowy.stl"))
    ap.add_argument("--fast", action="store_true", help="bez kontroli slicera (wolna)")
    a = ap.parse_args(argv)
    t0 = time.time()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    m, g, M = build(a.top, a.h, a.bulb, a.sleeve)
    from meshclean import clean_degenerate
    m, ci = clean_degenerate(m)
    m.export(a.out)
    m = trimesh.load(a.out)
    comps = len(m.split(only_watertight=False))
    smax_, zsm = profile_slopes(g)
    print(f"czubek_choinkowy.stl: {m.extents.round(1)} mm | tri {len(m.faces):,} | {os.path.getsize(a.out) / 1e6:.1f} MB | {m.volume / 1000:.1f} cm3 (materiał; w slicerze ok. {mass_est(m.volume, m.area):.0f} g PETG przy 3 obwiedniach i 15% wypełnienia)")
    print(f"  tuleja Ø {2 * g.r_s:.1f} (walec {g.Z0:.0f} mm, wnęka Ø {2 * g.r_h:.1f} aż do sufitu Ø {2 * R_FLAT:.0f} na z = {g.ceil:.1f} mm, wnętrze kuli puste do Ø {2 * g.inner()[:, 0].max():.1f}), kula Ø {2 * g.a:.0f} x {2 * g.b:.0f}, szyjka Ø {2 * g.r_neck:.1f}, podstawa iglicy Ø {2 * g.r_b:.1f} na z = {g.z_sb:.0f}, żeber: tuleja {g.Ns[0]}, kula {g.Ns[1]}, iglica {g.Ns[2]}")
    wall = min_wall(g)
    iov = inner_overhang(g)
    ok = m.is_watertight and comps == 1 and smax_ <= CONE_OUT + 0.02 and wall >= 1.8 and iov <= CONE + 0.02
    print(f"  profil: największe |dr/dz| nad stołem {smax_:.2f} (limit {CONE_OUT}) na z = {zsm:.0f} | strop wnętrza |dr/dz| {iov:.2f} (limit {CONE}) | ścianka min. {wall:.2f} mm (w dolinie żebra) | szczelna {m.is_watertight}, składowe {comps}")
    import nawisy
    from lib import overhang_report
    rep = overhang_report(m)
    print(f"  nawis > 55° (lib.overhang_report): {rep}")
    if not a.fast:
        for thr in (35.0,):
            r = nawisy.slicer_overhang(m, h=0.4, thr=thr)
            print(f"  nawis wg slicera (próg {thr:.0f}° od poziomu, warstwa 0,4): {r['area']:.1f} mm2, wyspy {r['floating']:.1f} mm2, najszersze niepodparte {r['width']:.1f} mm @ z {r['z']:.1f}")
            ok &= r["floating"] < 0.5 and r["width"] <= 12.0
    print(f"czas {time.time() - t0:.0f} s | {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
