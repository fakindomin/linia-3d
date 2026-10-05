"""Prosty renderer (z-buffer przez probkowanie trojkatow) do podgladow."""
import numpy as np
from PIL import Image, ImageDraw

def _rot(yaw, pitch):
    a, p = np.deg2rad(yaw), np.deg2rad(pitch)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    return Rx @ Rz

def render(meshes, yaw=0, pitch=8, W=600, H=900, margin=24, colors=None, ext=None, center=None,
           light=(-0.45, -0.6, 0.65), bg=(255, 255, 255), dens=5.0, up_extent=None):
    R = _rot(yaw, pitch)
    L = np.array(light, float); L /= np.linalg.norm(L)
    allV = np.vstack([m.vertices @ R.T for m in meshes])
    lo, hi = allV.min(0), allV.max(0)
    span = max(hi[0]-lo[0], hi[2]-lo[2]) if ext is None else ext
    sc = (min(W, H) - 2*margin) / span if ext is None else ext
    if ext is None:
        sc = min((W-2*margin)/(hi[0]-lo[0]), (H-2*margin)/(hi[2]-lo[2]))
    else:
        sc = ext
    cx = (hi[0]+lo[0])/2 if center is None else center[0]
    cz = (hi[2]+lo[2])/2 if center is None else center[1]
    img = np.zeros((H, W, 3), np.uint8); img[:] = bg
    zbuf = np.full((H, W), np.inf, np.float32)
    for mi, m in enumerate(meshes):
        col = np.array((colors[mi] if colors else (205, 195, 180)), float)
        V = m.vertices @ R.T
        N = m.vertex_normals @ R.T
        F = m.faces
        P = np.stack([(V[:, 0]-cx)*sc + W/2, H/2 - (V[:, 2]-cz)*sc, V[:, 1]], 1)
        t = P[F]                                  # (nf,3,3)
        e1, e2 = t[:, 1, :2]-t[:, 0, :2], t[:, 2, :2]-t[:, 0, :2]
        area = 0.5*np.abs(e1[:, 0]*e2[:, 1]-e1[:, 1]*e2[:, 0])
        # tylko zwrocone do kamery (normalna trojkata ma skladowa -y' w ukladzie widoku)
        fn = np.cross(V[F[:, 1]]-V[F[:, 0]], V[F[:, 2]]-V[F[:, 0]])
        front = fn[:, 1] < 0
        cnt = np.ceil(area*dens).astype(int)*front
        idx = np.repeat(np.arange(len(F)), cnt)
        if len(idx) == 0: continue
        r1, r2 = np.random.rand(len(idx)), np.random.rand(len(idx))
        flip = r1+r2 > 1
        r1[flip], r2[flip] = 1-r1[flip], 1-r2[flip]
        w0, w1, w2 = 1-r1-r2, r1, r2
        tt = t[idx]
        px = (w0*tt[:, 0, 0]+w1*tt[:, 1, 0]+w2*tt[:, 2, 0])
        py = (w0*tt[:, 0, 1]+w1*tt[:, 1, 1]+w2*tt[:, 2, 1])
        pz = (w0*tt[:, 0, 2]+w1*tt[:, 1, 2]+w2*tt[:, 2, 2])
        nn = (w0[:, None]*N[F[idx, 0]]+w1[:, None]*N[F[idx, 1]]+w2[:, None]*N[F[idx, 2]])
        nn /= np.linalg.norm(nn, axis=1, keepdims=True)+1e-9
        sh = np.clip(-(nn @ L) * -1, 0, 1)
        sh = np.clip(nn @ (-L*np.array([1, -1, 1])), 0, 1) if False else np.clip(nn @ L, 0, 1)
        shade = 0.28 + 0.72*sh
        ix, iy = px.astype(int), py.astype(int)
        ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        ix, iy, pz, shade = ix[ok], iy[ok], pz[ok], shade[ok]
        order = np.argsort(-pz)      # od najdalszych
        ix, iy, pz, shade = ix[order], iy[order], pz[order], shade[order]
        # z-buffer: zapis tylko gdy blizej
        keyl = iy*W+ix
        # dla kazdego piksela wez probke o najmniejszym pz (ostatnia po sortowaniu malejacym)
        last = np.ones(len(keyl), bool)
        _, ui = np.unique(keyl[::-1], return_index=True)
        sel = len(keyl)-1-ui
        ix2, iy2, pz2, sh2 = ix[sel], iy[sel], pz[sel], shade[sel]
        closer = pz2 < zbuf[iy2, ix2]
        ix2, iy2, pz2, sh2 = ix2[closer], iy2[closer], pz2[closer], sh2[closer]
        zbuf[iy2, ix2] = pz2
        img[iy2, ix2] = np.clip(col[None, :]*sh2[:, None], 0, 255).astype(np.uint8)
    # zamknij drobne dziury (pojedyncze piksele tla wewnatrz bryly)
    return Image.fromarray(img)

def grid(images, cols, pad=10, bg=(255, 255, 255), labels=None):
    w = max(i.width for i in images); h = max(i.height for i in images)
    rows = (len(images)+cols-1)//cols
    out = Image.new("RGB", (cols*w+(cols+1)*pad, rows*h+(rows+1)*pad), bg)
    d = ImageDraw.Draw(out)
    for k, im in enumerate(images):
        r, c = divmod(k, cols)
        out.paste(im, (pad+c*(w+pad), pad+r*(h+pad)))
        if labels:
            d.text((pad+c*(w+pad)+6, pad+r*(h+pad)+4), labels[k], fill=(60, 60, 60))
    return out


def section_img(meshes, W=440, H=880, ext=1.0, center=(0, 0), colors=None, extra_polys=None, plane_y=0.0):
    """kontur przekroju plaszczyzna y=plane_y (x poziomo, z pionowo); extra_polys: lista [(x,z),...] rysowana na czerwono"""
    img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
    cols = colors or [(40, 40, 40), (90, 60, 40), (40, 80, 120)]
    P = lambda x, z: ((x - center[0]) * ext + W / 2, H / 2 - (z - center[1]) * ext)
    for k, m in enumerate(meshes):
        sec = m.section(plane_origin=[0, plane_y, 0], plane_normal=[0, 1, 0])
        if sec is None:
            continue
        for line in sec.discrete:
            pts = [P(p[0], p[2]) for p in line]
            d.line(pts, fill=cols[k % len(cols)], width=2)
    for poly in (extra_polys or []):
        d.line([P(x, z) for x, z in poly], fill=(200, 40, 40), width=2)
    return img
