"""STANDARD v1.0 -> line.json: stale, profile idealne, porty i zebra modeli kluczowych (krolik, jajko, dynia, balwan).

Python (standard.py / models.py / shapes.py / build_*.py) jest JEDYNYM zrodlem prawdy. Ten skrypt zamienia je w JSON,
z ktorego korzysta podglad w przegladarce (artefakt 'Zebrowana kolekcja': build_artifact.py wstrzykuje line.json do HTML).
Zmiana standardu = python export_line_json.py && python build_artifact.py && publikacja artefaktu.

Kontrole wbudowane (skrypt konczy sie bledem, gdy JSON rozjezdza sie z Pythonem):
  * zebra snowmana odtworzona z 'bands' == BS.snow_F (losowe punkty),
  * profil probkowany z JSON (interpolacja liniowa) == Rfun modelu (max odchylka < 0,01 mm).

Uzycie:  python export_line_json.py [sciezka_wyjsciowa]      (domyslnie ./line.json)
"""
import sys, os, json, math, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shapely.geometry as sg
import standard as S
import models as MD
import shapes as SH
import build_pumpkin as BP
import build_snowman as BS
import build_egg as BE

HERE = os.path.dirname(os.path.abspath(__file__))
R3 = lambda v: round(float(v), 4)
L3 = lambda a: [R3(x) for x in np.asarray(a, float).ravel()]


def sample_R(Rfun, z0, z1, step=0.5, steps=(), tol=0.004, dz_min=0.002):
    """profil boczny R(z) jako lista [z, R]: siatka co 'step', potem adaptacyjny podzial przedzialow, az srodek lamanej leży w tol od profilu
    (w normalnej do cieciwy; przy szczycie kuli dR/dz -> oo). Skoki w 'steps' = dwa punkty z - 1e-4 / z + 1e-4."""
    f = lambda z: max(float(Rfun(np.float64(z))), 0.0)
    sk = sorted(float(s) for s in steps)
    knots = [float(z0)] + sk + [float(z1)]
    pts = []
    for ka, kb in zip(knots[:-1], knots[1:]):
        a = ka + (1e-4 if ka in sk else 0.0)
        b = kb - (1e-4 if kb in sk else 0.0)
        zs = list(np.arange(a, b, step)) + [b]
        for za, zb in zip(zs[:-1], zs[1:]):
            stack = [(za, f(za), zb, f(zb))]
            while stack:
                za_, ra, zb_, rb = stack.pop()
                zm = 0.5 * (za_ + zb_)
                rm = f(zm)
                sl = (rb - ra) / (zb_ - za_)
                err = abs(rm - (ra + rb) / 2) / math.sqrt(1 + sl * sl)
                if err > tol and zb_ - za_ > dz_min:
                    stack += [(zm, rm, zb_, rb), (za_, ra, zm, rm)]
                else:
                    pts.append((za_, ra))
        pts.append((b, f(b)))
    pts = sorted(set(pts))
    return [[R3(x), R3(y)] for x, y in pts]


def interp_R(table, z):
    t = np.asarray(table, float)
    return np.interp(z, t[:, 0], t[:, 1])


def simplify_outline(o, tol=0.01):
    ls = sg.LineString([tuple(p) for p in o]).simplify(tol, preserve_topology=False)
    return [[R3(x), R3(y)] for x, y in ls.coords]


def frame_json(fr):
    return dict(O=L3(fr.O), A=L3(fr.A), B=L3(fr.B), C=L3(fr.C))


def ports_json(model):
    return {n: dict(kind=p.kind, P0=L3(p.P0), frame=frame_json(p.frame)) for n, p in model.ports.items()}


def rib_json(bands, fade=(4.0, 10.0)):
    return dict(amp=S.RIB_AMP, pow=0.8, fade=list(fade), bands=bands)


# profil bazowy POLA dyni (srednia: grzbiety zeber = srodek + amplituda); MD.Rp to profil grzbietow (obrys do koperty, a = 50)
R_PUMP_FIELD = lambda z: float(BP.R_mean(np.float64(z), BP.S_FINE))


# ------------------------------------------------------------------------------------------------ zebra
def bands_snowman():
    """pasma zeber snowmana zgodne z BS.snow_F: {N, up:[z0,z1]|None, down:[z0,z1]|None}; waga = sstep(up) * (1 - sstep(down))"""
    return [dict(N=BS.N1, up=None, down=[BS.ZW1 - 5.5, BS.ZW1 - 3.5]),
            dict(N=BS.N2, up=[BS.ZW1 + 3.5, BS.ZW1 + 5.5], down=[BS.ZW2 - 5.5, BS.ZW2 - 3.5]),
            dict(N=BS.N3, up=[BS.ZW2 + 3.5, BS.ZW2 + 5.5], down=[97.0, 99.5]),
            dict(N=BS.NH, up=[BS.ZT + 6.0, BS.ZT + 8.0], down=[BS.TOTAL - BS.FIL - 2.0, BS.TOTAL - BS.FIL])]


def ribbed_from_bands(Rfun, bands, z0, z1, X, Y, Z, amp=S.RIB_AMP, pw=0.8, fade=(4.0, 10.0)):
    """to samo co robi podglad JS: F = R + amp*fade(R)*sum(w_i*rib_i) - rho, ograniczone plaszczyznami z0 / z1"""
    rho, th = np.sqrt(X ** 2 + Y ** 2), np.arctan2(Y, X)
    R = Rfun(Z)
    ss = lambda z, a, b: (lambda t: t * t * (3 - 2 * t))(np.clip((z - a) / (b - a), 0, 1))
    mod = 0.0
    for b in bands:
        w = 1.0
        if b.get("up"):
            w = w * ss(Z, *b["up"])
        if b.get("down"):
            w = w * (1 - ss(Z, *b["down"]))
        c = np.cos(b["N"] * th)
        mod = mod + w * np.sign(c) * np.abs(c) ** pw
    a = amp * np.clip((R - fade[0]) / (fade[1] - fade[0]), 0, 1)
    return np.minimum(np.minimum((R + a * mod - 1e-3) - rho, Z - z0), z1 - Z).astype(np.float32)


# ------------------------------------------------------------------------------------------------ eksport
def build():
    rng = np.random.default_rng(7)
    out = dict(version=S.VERSION)
    out["const"] = dict(
        PEG_W=S.PEG_W, PEG_L=S.PEG_L, PEG_R=S.PEG_R, SOCK_W=S.SOCK_W, SOCK_D=S.SOCK_D, SOCK_R=S.SOCK_R, SOCK_OVER=S.SOCK_OVER,
        LP_PEG_CH=S.LP_PEG_CH, LP_SOCK_CH=S.LP_SOCK_CH, EAR_X=S.EAR_X, EAR_Y=S.EAR_Y, TILT_DEG=R3(math.degrees(S.TILT)), GAP=S.GAP,
        RIB_AMP=S.RIB_AMP, RIB_PITCH=S.RIB_PITCH, RIB_SHAPE=0.8, RIB_FADE=[4.0, 10.0], TOTAL_H=S.TOTAL_H,
        LP_SLOPE=S.LP_SLOPE, OVERHANG_DEG=S.OVERHANG_DEG, ENV_PAD=S.ENV_PAD, PAD_MIN=S.PAD_MIN, PORT_TOL=S.PORT_TOL, MIN_CLEAR=S.MIN_CLEAR,
        LP_TOL=S.LP_TOL, FACET_DIV=S.FACET_DIV, FACET_MIN=S.FACET_MIN)
    out["peg_socket_clearance"] = S.peg_socket_matrix()
    M = {}

    # --- krolik / renifer: korpus bazowy
    B = MD.BUNNY
    M["krolik"] = dict(
        H=B.H, outline=simplify_outline(B.outline), R=sample_R(B.Rfun, 0.0, B.H), ports=ports_json(B), pad=B.pad,
        params=dict(bodyW=2 * SH.BODY_R, bodyHz=SH.BODY_HZ, bodyN=SH.BODY_N, headR=SH.HEAD_R, headZ=SH.HEAD_ZC, blend=SH.SMOOTH_P,
                    ribs=SH.N_BUNNY, ribDepth=2 * S.RIB_AMP, ribPow=0.8, earX=S.EAR_X, earTilt=R3(math.degrees(S.TILT))),
        ribs=rib_json([dict(N=SH.N_BUNNY, up=None, down=None)]), zport=R3(B.zport))

    # --- jajko
    E = MD.EGG
    M["jajko"] = dict(
        H=E.H, outline=simplify_outline(E.outline), R=sample_R(E.Rfun, 0.0, SH.H_EGG), ports=ports_json(E), pad=E.pad,
        params=dict(eggW=2 * SH.RMAX, eggH=SH.H_EGG, seam=SH.ZM, cavR=SH.R_CAV, floor=SH.FLOOR, lipH=SH.LIP_H, wallCup=SH.WALL_CUP,
                    ceilZ=SH.CEIL_Z, ribs=SH.N_EGG, ribDepth=2 * S.RIB_AMP, ribPow=0.8, earX=S.EAR_X, earTilt=R3(math.degrees(S.TILT))),
        cone=dict(slope=BE.CONE_DR_DZ, R_TOP=BE.R_TOP, Z_A=R3(BE.Z_A), ceil=SH.CEIL_Z),
        ribs=rib_json([dict(N=SH.N_EGG, up=None, down=None)]), zport=R3(E.zport))

    # --- dynia (pole zebrowane 'fine': N = 92, zanik zeber (R-12)/16 - odstepstwo od standardu, zob. STANDARD.md 'znane odstepstwa')
    P = MD.PUMPKIN
    M["dynia"] = dict(
        H=BP.H_TOP, outline=simplify_outline(P.outline), R=sample_R(R_PUMP_FIELD, 0.0, BP.H_TOP), ports=ports_json(P), pad=P.pad,
        top=dict(R_SH=BP.R_SH, DIP=BP.DIP, H_TOP=BP.H_TOP,
                 surface=[[R3(r), R3(float(BP.top_surface(r)))] for r in np.linspace(0.0, BP.R_SH, 41)]),
        ribs=rib_json([dict(N=92, up=None, down=None)], fade=(12.0, 28.0)), zport=R3(MD.P_DIP_Z),
        stem=dict(H=BP.STEM_H, R0=BP.STEM_R0, RT=BP.STEM_RT, bend=BP.BEND, N=BP.STEM_N, amp=BP.STEM_AMP))

    # --- balwan
    W = MD.SNOWMAN
    bands = bands_snowman()
    M["balwan"] = dict(
        H=W.H, outline=simplify_outline(W.outline), R=sample_R(W.Rfun, 0.0, BS.TOTAL, steps=(BS.ZT,)), ports=ports_json(W), pad=W.pad,
        ribs=rib_json(bands), zhat=BS.ZT, zport=None,
        balls=dict(R1=BS.R1, Z1=BS.Z1, R2=BS.R2, Z2=BS.Z2, R3=BS.R3, Z3=BS.Z3, ZW1=BS.ZW1, ZW2=BS.ZW2),
        nose=dict(L=BS.NOSE_L, R0=BS.NOSE_R0, RT=BS.NOSE_RT), broom=dict(handle=BS.BR_HANDLE, total=BS.BR_TOTAL, elev_deg=55.0))
    out["models"] = M

    # ------------------------------------------------------------------------------------------ kontrole
    # profil z JSON == Rfun
    for name, rf, z1 in (("krolik", MD.Rb, B.H), ("jajko", MD.Re, SH.H_EGG), ("dynia", R_PUMP_FIELD, BP.H_TOP), ("balwan", MD.Rs, BS.TOTAL)):
        zz = np.concatenate([rng.uniform(0.0, z1, 3000), [0.0, z1]])
        Rt = np.array([max(float(rf(np.float64(z))), 0.0) for z in zz])
        ln = sg.LineString(M[name]["R"])                                                      # odleglosc punktu profilu od lamanej JSON (w plaszczyznie z-R)
        dev = np.array([ln.distance(sg.Point(z, r)) for z, r in zip(zz, Rt)])
        assert dev.max() < 0.01, f"profil {name}: odchylka od lamanej {dev.max():.4f} mm"
        out["models"][name]["R_maxdev"] = R3(dev.max())
    # zebra snowmana z pasm == BS.snow_F
    n = 40000
    X, Y, Z = rng.uniform(-30, 30, n), rng.uniform(-30, 30, n), rng.uniform(-1, 151, n)
    Fb = ribbed_from_bands(lambda z: BS.R_prof(z), bands, 0.0, BS.TOTAL, X, Y, Z)
    Fp = BS.snow_F(X, Y, Z)
    assert np.abs(Fb - Fp).max() < 1e-4, f"zebra snowmana: {np.abs(Fb - Fp).max()}"
    # zebra krolika / jajka z pasm == bunny_F / egg_F (z wylaczeniem przycinania do dolu: tam min(.., Z))
    Fk = ribbed_from_bands(lambda z: SH.bunny_profile(z), M["krolik"]["ribs"]["bands"], 0.0, 1e9, X, Y, np.abs(Z))
    assert np.abs(Fk - np.minimum(SH.ribbed_F(SH.bunny_profile(np.abs(Z)), SH.N_BUNNY, np.arctan2(Y, X), np.sqrt(X ** 2 + Y ** 2)), np.abs(Z))).max() < 1e-4
    out["checks"] = dict(snowman_bands_vs_snow_F=R3(np.abs(Fb - Fp).max()), profile_samples=3000)

    # ------------------------------------------------------------------------------------------ odcisk zrodel
    h = hashlib.sha1()
    for f in ("standard.py", "models.py", "shapes.py", "build_pumpkin.py", "build_snowman.py", "build_egg.py", "lib.py"):
        h.update(open(os.path.join(HERE, f), "rb").read())
    out["source_sha1"] = h.hexdigest()[:12]
    return out


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "line.json")
    d = build()
    with open(path, "w") as f:
        json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(path) / 1024
    print(f"line.json: {kb:.1f} kB, standard v{d['version']}, zrodla {d['source_sha1']}")
    for k, m in d["models"].items():
        print(f"  {k:7s} H={m['H']:.1f}  R:{len(m['R'])} pkt  obrys:{len(m['outline'])} pkt  porty:{list(m['ports'])}  zebra:{[b['N'] for b in m['ribs']['bands']]}  dev={m['R_maxdev']}")
    print("  luz czop-gniazdo:", d["peg_socket_clearance"])
    print("  kontrole:", d["checks"])
