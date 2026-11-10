/* Rdzeń geometrii artefaktu „Świąteczne dodatki”: port algorytmów z etykieta.py, foremki_piernik.py (kołnierz, ścianka, ostrze) i czubek_choinkowy.py.
   Python = źródło prawdy; ten plik ma te same stałe i wzory (test: artifact/test_swieta.py porównuje objętości i wymiary).
   Zależności (wstrzykiwane): ClipperLib (clipper-lib 6.4.2), opentype (opentype.js 1.3.4), triangulate(contour, holes) -> płaska lista indeksów (earcut).
   UMD: w przeglądarce window.SwietaCore = create; w Node module.exports = create. Wymiary w mm, z = 0 to stół. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory; else root.SwietaCore = factory;
})(typeof self !== 'undefined' ? self : this, function create(deps) {
  'use strict';
  const { ClipperLib, opentype, triangulate } = deps;
  const SC = 1000;                    // jednostka Clippera: 1 µm
  const ARC_TOL = 10;                 // tolerancja łuków offsetu: 0,01 mm
  const PETG = 1.27;

  // ------------------------------------------------------------------------------------------ pomocnicze (Clipper)
  const toPath = (pts) => pts.map((p) => ({ X: Math.round(p[0] * SC), Y: Math.round(p[1] * SC) }));
  const area2 = (path) => { let s = 0; for (let i = 0, n = path.length; i < n; i++) { const a = path[i], b = path[(i + 1) % n]; s += a.X * b.Y - b.X * a.Y; } return s; };
  const orient = (path, ccw) => ((area2(path) > 0) === ccw ? path : path.slice().reverse());
  function clip(type, subj, cl, fill) {
    const c = new ClipperLib.Clipper(); c.PreserveCollinear = true;
    c.AddPaths(subj, ClipperLib.PolyType.ptSubject, true);
    if (cl && cl.length) c.AddPaths(cl, ClipperLib.PolyType.ptClip, true);
    const sol = new ClipperLib.Paths();
    const f = fill === undefined ? ClipperLib.PolyFillType.pftNonZero : fill;
    c.Execute(type, sol, f, f);
    return sol;
  }
  const union = (a, b, fill) => clip(ClipperLib.ClipType.ctUnion, a, b, fill);
  const diff = (a, b) => clip(ClipperLib.ClipType.ctDifference, a, b);
  function offset(paths, delta) {
    const co = new ClipperLib.ClipperOffset(2, ARC_TOL);
    co.AddPaths(paths, ClipperLib.JoinType.jtRound, ClipperLib.EndType.etClosedPolygon);
    const sol = new ClipperLib.Paths();
    co.Execute(sol, delta * SC);
    return sol;
  }
  function walkTree(paths, fn) {            // fn(zewnętrzny, [dziury]) dla każdego obszaru, wraz z wyspami w dziurach
    const c = new ClipperLib.Clipper(); c.PreserveCollinear = true;
    c.AddPaths(paths, ClipperLib.PolyType.ptSubject, true);
    const tree = new ClipperLib.PolyTree();
    c.Execute(ClipperLib.ClipType.ctUnion, tree, ClipperLib.PolyFillType.pftEvenOdd, ClipperLib.PolyFillType.pftEvenOdd);
    const rec = (nodes) => { for (const nd of nodes) { const holes = nd.Childs(); fn(orient(nd.Contour(), true), holes.map((h) => orient(h.Contour(), false))); for (const h of holes) rec(h.Childs()); } };
    rec(tree.Childs());
  }
  const polyArea = (paths) => paths.reduce((s, p) => s + area2(p), 0) / 2 / (SC * SC);     // dla regionów: kontury zewn. dodatnie, dziury ujemne

  // ------------------------------------------------------------------------------------------ siatka
  class MB {                                // siatka ze sklejaniem wierzchołków o współrzędnych całkowitych (µm)
    constructor() { this.pos = []; this.idx = []; this.map = new Map(); }
    v(X, Y, z) { const k = X + '_' + Y + '_' + Math.round(z * 1e4); let i = this.map.get(k); if (i === undefined) { i = this.pos.length / 3; this.pos.push(X / SC, Y / SC, z); this.map.set(k, i); } return i; }
    t(a, b, c) { if (a !== b && b !== c && a !== c) this.idx.push(a, b, c); }
    /* earcut (połączenia dziur, pominięte współliniowe wierzchołki) daje złącza T: długa krawędź jednego trójkąta leży nad kilkoma krótkimi krawędziami sąsiednich ścian.
       Naprawa: dla każdej krawędzi bez pary dzielimy jej trójkąt wachlarzem przez wierzchołki leżące dokładnie na tej krawędzi. */
    repairTJ() {
      const I = this.idx, P = this.pos, dirs = new Set();
      for (let i = 0; i < I.length; i += 3) for (let k = 0; k < 3; k++) dirs.add(I[i + k] + '_' + I[i + (k + 1) % 3]);
      const open = [], vo = new Set();
      for (let i = 0; i < I.length; i += 3) for (let k = 0; k < 3; k++) { const a = I[i + k], b = I[i + (k + 1) % 3]; if (!dirs.has(b + '_' + a)) { open.push([a, b]); vo.add(a); vo.add(b); } }
      if (!open.length) return 0;
      const V = [...vo], chains = new Map();
      for (const [a, b] of open) {
        const ax = P[a * 3], ay = P[a * 3 + 1], az = P[a * 3 + 2], dx = P[b * 3] - ax, dy = P[b * 3 + 1] - ay, dz = P[b * 3 + 2] - az, L2 = dx * dx + dy * dy + dz * dz, c = [];
        for (const v of V) {
          if (v === a || v === b) continue;
          const px = P[v * 3] - ax, py = P[v * 3 + 1] - ay, pz = P[v * 3 + 2] - az, t = (px * dx + py * dy + pz * dz) / L2;
          if (t <= 1e-9 || t >= 1 - 1e-9) continue;
          if (Math.hypot(px - t * dx, py - t * dy, pz - t * dz) < 1e-6) c.push([t, v]);
        }
        if (c.length) { c.sort((x, y) => x[0] - y[0]); chains.set(a + '_' + b, [a].concat(c.map((q) => q[1]), [b])); }
      }
      if (!chains.size) return open.length;
      const out = [], stack = [];
      for (let i = 0; i < I.length; i += 3) stack.push([I[i], I[i + 1], I[i + 2]]);
      while (stack.length) {
        const t = stack.pop(); let split = false;
        for (let e = 0; e < 3 && !split; e++) {
          const a = t[e], b = t[(e + 1) % 3], c = t[(e + 2) % 3], ch = chains.get(a + '_' + b);
          if (!ch) continue;
          for (let k = 0; k < ch.length - 1; k++) stack.push([ch[k], ch[k + 1], c]);
          split = true;
        }
        if (!split) out.push(t[0], t[1], t[2]);
      }
      this.idx = out;
      return 0;
    }
    done() { this.repairTJ(); return { positions: Float32Array.from(this.pos), indices: Uint32Array.from(this.idx) }; }
  }

  function faceTris(mb, outer, holes, z, up) {
    const ring = (p) => p.map((q) => [q.X, q.Y]);
    const O = ring(outer), Hs = holes.map(ring);
    const flat = O.concat(...Hs);
    const ids = flat.map((q) => mb.v(q[0], q[1], z));
    const idx = triangulate(O.map((q) => [q[0] / SC, q[1] / SC]), Hs.map((h) => h.map((q) => [q[0] / SC, q[1] / SC])));
    for (let q = 0; q < idx.length; q += 3) {
      const i0 = idx[q], i1 = idx[q + 1], i2 = idx[q + 2];
      const a = flat[i0], b = flat[i1], c = flat[i2];
      const s = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]);
      if (s === 0) continue;
      if ((s > 0) === up) mb.t(ids[i0], ids[i1], ids[i2]); else mb.t(ids[i0], ids[i2], ids[i1]);
    }
  }
  function wallTris(mb, path, z0, z1) {     // kontur CCW (zewnętrzny) lub CW (dziura): normalna na prawo od kierunku = na zewnątrz materiału
    for (let i = 0, n = path.length; i < n; i++) {
      const a = path[i], b = path[(i + 1) % n];
      const a0 = mb.v(a.X, a.Y, z0), b0 = mb.v(b.X, b.Y, z0), b1 = mb.v(b.X, b.Y, z1), a1 = mb.v(a.X, a.Y, z1);
      mb.t(a0, b0, b1); mb.t(a0, b1, a1);
    }
  }
  /* bryła z zagnieżdżonych płyt 2,5D: slabs = [{z0, z1, region}], każdy następny region zawiera się w poprzednim, z0[i+1] = z1[i] */
  function stack(slabs) {
    const mb = new MB();
    slabs.forEach((s, i) => {
      walkTree(s.region, (o, hs) => { wallTris(mb, o, s.z0, s.z1); hs.forEach((h) => wallTris(mb, h, s.z0, s.z1)); });
      const nxt = slabs[i + 1];
      const top = nxt ? diff(s.region, nxt.region) : s.region;
      walkTree(top, (o, hs) => faceTris(mb, o, hs, s.z1, true));
      if (i === 0) walkTree(s.region, (o, hs) => faceTris(mb, o, hs, s.z0, false));
    });
    return mb.done();
  }

  // ------------------------------------------------------------------------------------------ wymiary / eksport
  function meshInfo(m) {
    const P = m.positions, I = m.indices;
    let vol = 0, area = 0; const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (let i = 0; i < P.length; i += 3) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], P[i + k]); hi[k] = Math.max(hi[k], P[i + k]); }
    for (let i = 0; i < I.length; i += 3) {
      const a = I[i] * 3, b = I[i + 1] * 3, c = I[i + 2] * 3;
      vol += P[a] * (P[b + 1] * P[c + 2] - P[b + 2] * P[c + 1]) - P[a + 1] * (P[b] * P[c + 2] - P[b + 2] * P[c]) + P[a + 2] * (P[b] * P[c + 1] - P[b + 1] * P[c]);
      const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2], vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      area += 0.5 * Math.hypot(uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx);
    }
    vol /= 6;
    return { volume: vol, area, tris: I.length / 3, extents: [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]], lo, hi, grams: vol / 1000 * PETG };
  }
  function toStl(m) {                       // binarny STL z siatki indeksowanej
    const P = m.positions, I = m.indices, n = I.length / 3;
    const buf = new ArrayBuffer(84 + 50 * n), dv = new DataView(buf);
    const head = 'linia-3d swieta_core'; for (let i = 0; i < head.length; i++) dv.setUint8(i, head.charCodeAt(i));
    dv.setUint32(80, n, true);
    let o = 84;
    for (let t = 0; t < n; t++) {
      const a = I[3 * t] * 3, b = I[3 * t + 1] * 3, c = I[3 * t + 2] * 3;
      const ux = P[b] - P[a], uy = P[b + 1] - P[a + 1], uz = P[b + 2] - P[a + 2], vx = P[c] - P[a], vy = P[c + 1] - P[a + 1], vz = P[c + 2] - P[a + 2];
      let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
      const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
      dv.setFloat32(o, nx, true); dv.setFloat32(o + 4, ny, true); dv.setFloat32(o + 8, nz, true);
      for (const q of [a, b, c]) { dv.setFloat32(o + 12, P[q], true); dv.setFloat32(o + 16, P[q + 1], true); dv.setFloat32(o + 20, P[q + 2], true); o += 12; }
      dv.setUint16(o + 12, 0, true); o += 14;
    }
    return buf;
  }
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(u8) { let c = 0xffffffff; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
  function zipStore(filename, data) {       // ZIP bez kompresji z jednym plikiem (nazwa UTF-8)
    const name = new TextEncoder().encode(filename), d = new Uint8Array(data), crc = crc32(d), n = name.length, sz = d.length;
    const out = new ArrayBuffer(30 + n + sz + 46 + n + 22), dv = new DataView(out), u8 = new Uint8Array(out);
    const date = ((2026 - 1980) << 9) | (11 << 5) | 1, time = 0;
    let o = 0;
    dv.setUint32(o, 0x04034b50, true); dv.setUint16(o + 4, 20, true); dv.setUint16(o + 6, 0x0800, true); dv.setUint16(o + 8, 0, true); dv.setUint16(o + 10, time, true); dv.setUint16(o + 12, date, true);
    dv.setUint32(o + 14, crc, true); dv.setUint32(o + 18, sz, true); dv.setUint32(o + 22, sz, true); dv.setUint16(o + 26, n, true); dv.setUint16(o + 28, 0, true);
    u8.set(name, o + 30); u8.set(d, o + 30 + n); o += 30 + n + sz;
    const cd = o;
    dv.setUint32(o, 0x02014b50, true); dv.setUint16(o + 4, 20, true); dv.setUint16(o + 6, 20, true); dv.setUint16(o + 8, 0x0800, true); dv.setUint16(o + 10, 0, true); dv.setUint16(o + 12, time, true); dv.setUint16(o + 14, date, true);
    dv.setUint32(o + 16, crc, true); dv.setUint32(o + 20, sz, true); dv.setUint32(o + 24, sz, true); dv.setUint16(o + 28, n, true); dv.setUint16(o + 30, 0, true); dv.setUint16(o + 32, 0, true);
    dv.setUint16(o + 34, 0, true); dv.setUint16(o + 36, 0, true); dv.setUint32(o + 38, 0, true); dv.setUint32(o + 42, 0, true);
    u8.set(name, o + 46); o += 46 + n;
    dv.setUint32(o, 0x06054b50, true); dv.setUint16(o + 4, 0, true); dv.setUint16(o + 6, 0, true); dv.setUint16(o + 8, 1, true); dv.setUint16(o + 10, 1, true);
    dv.setUint32(o + 12, 46 + n, true); dv.setUint32(o + 16, cd, true); dv.setUint16(o + 20, 0, true);
    return out;
  }

  // ------------------------------------------------------------------------------------------ ETYKIETA (etykieta.py)
  const LB = { PT: 2.0, RAISE: 0.8, HOLE_D: 4.2, RING_W: 2.2, HOLE_X: 6.4, RIM_IN: 1.4, RIM_W: 1.0, CORNER: 5.0, TEXT_M: 1.4, H_MIN: 32.0, W_MIN: 60.0, CAP_DLA_MIN: 6.0, GAP: 3.0, TRACK: 0.06, CAP_DEFAULT: 11.0, CAP_MIN: 7.0, CAP_MAX: 15.0, CURVE_N: 6, ARC_N: 16 };

  function rrect(cx, cy, w, h, r) {
    r = Math.min(r, w / 2 - 1e-6, h / 2 - 1e-6);
    const pts = [];
    for (const [sx, sy, a0] of [[1, 1, 0], [-1, 1, 90], [-1, -1, 180], [1, -1, 270]]) {
      const ccx = cx + sx * (w / 2 - r), ccy = cy + sy * (h / 2 - r);
      for (let i = 0; i <= LB.ARC_N; i++) { const a = (a0 + 90 * i / LB.ARC_N) * Math.PI / 180; pts.push([ccx + r * Math.cos(a), ccy + r * Math.sin(a)]); }
    }
    return [toPath(pts)];
  }
  function circle(cx, cy, r, n) {
    const pts = []; for (let i = 0; i < n; i++) pts.push([cx + r * Math.cos(2 * Math.PI * i / n), cy + r * Math.sin(2 * Math.PI * i / n)]);
    return [toPath(pts)];
  }
  function textPaths(font, s, cap, x0, y0, measureOnly) {
    const k = cap / font.tables.os2.sCapHeight;
    const paths = []; let x = 0;
    for (const ch of s) {
      let g = font.charToGlyph(ch); if (!g || g.index === 0) g = font.charToGlyph('?');
      const rings = []; let cur = null;
      const N = LB.CURVE_N;
      for (const c of g.path.commands) {
        if (c.type === 'M') cur = [[c.x, c.y]];
        else if (c.type === 'L') cur.push([c.x, c.y]);
        else if (c.type === 'Q') { const p0 = cur[cur.length - 1]; for (let i = 1; i <= N; i++) { const t = i / N, u = 1 - t; cur.push([u * u * p0[0] + 2 * u * t * c.x1 + t * t * c.x, u * u * p0[1] + 2 * u * t * c.y1 + t * t * c.y]); } }
        else if (c.type === 'C') { const p0 = cur[cur.length - 1]; for (let i = 1; i <= N; i++) { const t = i / N, u = 1 - t; cur.push([u * u * u * p0[0] + 3 * u * u * t * c.x1 + 3 * u * t * t * c.x2 + t * t * t * c.x, u * u * u * p0[1] + 3 * u * u * t * c.y1 + 3 * u * t * t * c.y2 + t * t * t * c.y]); } }
        else if (c.type === 'Z') { if (cur && cur.length > 2) rings.push(cur); cur = null; }
      }
      if (cur && cur.length > 2) rings.push(cur);
      if (!measureOnly) for (const r of rings) paths.push(toPath(r.map((q) => [x0 + x + q[0] * k, y0 + q[1] * k])));
      x += g.advanceWidth * k + LB.TRACK * cap;
    }
    x -= LB.TRACK * cap;
    return { paths: measureOnly ? [] : union(paths, null, ClipperLib.PolyFillType.pftNonZero), width: x };
  }
  function labelLayout(font, name, cap) {
    cap = Math.min(Math.max(cap, LB.CAP_MIN), LB.CAP_MAX);
    const capD = Math.max(LB.CAP_DLA_MIN, 0.5 * cap);
    const wn = textPaths(font, name, cap, 0, 0, true).width, wd = textPaths(font, 'Dla', capD, 0, 0, true).width;
    const wt = Math.max(wn, wd), M = LB.RIM_IN + LB.RIM_W + LB.TEXT_M;
    const H = Math.max(LB.H_MIN, 2 * M + capD + LB.GAP + 1.32 * cap);
    const zone0 = LB.HOLE_X + LB.HOLE_D / 2 + LB.RING_W + LB.TEXT_M;
    const W = Math.max(LB.W_MIN, zone0 + wt + M);
    return { cap, capD, wn, wd, wt, M, H, W, zone0 };
  }
  function buildLabel(font, name, cap) {
    const L = labelLayout(font, name, cap == null ? LB.CAP_DEFAULT : cap), W = L.W, H = L.H;
    const S = rrect(0, 0, W, H, LB.CORNER);
    const hx = -W / 2 + LB.HOLE_X, hole = circle(hx, 0, LB.HOLE_D / 2, 48), ring = circle(hx, 0, LB.HOLE_D / 2 + LB.RING_W, 64);
    const rim = diff(rrect(0, 0, W - 2 * LB.RIM_IN, H - 2 * LB.RIM_IN, LB.CORNER - LB.RIM_IN), rrect(0, 0, W - 2 * (LB.RIM_IN + LB.RIM_W), H - 2 * (LB.RIM_IN + LB.RIM_W), LB.CORNER - LB.RIM_IN - LB.RIM_W));
    const xc = -W / 2 + L.zone0 + (W - L.zone0 - L.M) / 2, top = H / 2 - L.M;
    const yDla = top - L.capD, yName = yDla - LB.GAP - L.cap, xLeft = xc - L.wt / 2;
    const dla = textPaths(font, 'Dla', L.capD, xLeft, yDla).paths;
    const nm = textPaths(font, name, L.cap, xLeft + (L.wt - L.wn) / 2, yName).paths;
    const raised = diff(union(union(union(rim, ring), dla), nm), hole);
    const plate = diff(S, hole);
    const mesh = stack([{ z0: 0, z1: LB.PT, region: plate }, { z0: LB.PT, z1: LB.PT + LB.RAISE, region: raised }]);
    return { mesh, info: Object.assign(meshInfo(mesh), { W, H, cap: L.cap, plateArea: polyArea(plate), raisedArea: polyArea(raised), expectedVolume: polyArea(plate) * LB.PT + polyArea(raised) * LB.RAISE }) };
  }

  // ------------------------------------------------------------------------------------------ FOREMKA (foremki_piernik.py)
  const CT = { WALL: 1.2, EDGE: 0.45, TAPER: 2.0, H_TOT: 16.0, FL_T: 2.0, FL_W: 5.0, STEPS: 8 };
  function buildCutter(outline, opt) {
    opt = Object.assign({ scale: 1, FL_T: CT.FL_T, FL_W: CT.FL_W }, opt || {});
    const k = opt.scale;
    const S = [orient(toPath(outline.ext.map((p) => [p[0] * k, p[1] * k])), true)];
    (outline.holes || []).forEach((h) => S.push(orient(toPath(h.map((p) => [p[0] * k, p[1] * k])), false)));
    const ring = (d) => diff(offset(S, d), S);
    const slabs = [{ z0: 0, z1: opt.FL_T, region: ring(CT.WALL + opt.FL_W) }, { z0: opt.FL_T, z1: CT.H_TOT - CT.TAPER, region: ring(CT.WALL) }];
    const dz = CT.TAPER / CT.STEPS;
    for (let i = 0; i < CT.STEPS; i++) slabs.push({ z0: CT.H_TOT - CT.TAPER + i * dz, z1: CT.H_TOT - CT.TAPER + (i + 1) * dz, region: ring(CT.WALL - (CT.WALL - CT.EDGE) * (i + 1) / CT.STEPS) });
    const mesh = stack(slabs);
    const info = meshInfo(mesh);
    const bb = [1e9, 1e9, -1e9, -1e9]; S[0].forEach((p) => { bb[0] = Math.min(bb[0], p.X / SC); bb[1] = Math.min(bb[1], p.Y / SC); bb[2] = Math.max(bb[2], p.X / SC); bb[3] = Math.max(bb[3], p.Y / SC); });
    info.dough = [bb[2] - bb[0], bb[3] - bb[1]]; info.doughArea = polyArea(S);
    return { mesh, info };
  }

  // ------------------------------------------------------------------------------------------ CZUBEK (czubek_choinkowy.py)
  const TP = { CLEAR: 0.3, WALL_T: 2.7, DEPTH: 26.0, CONE: 1.3, CONE_OUT: 1.15, R_FLAT: 5.0, BULB_FLAT: 0.85, NECK: 0.21, SPIRE_BASE: 0.44, SPIRE_P: 2.2, R_TIP: 1.6, L_NECK: 2.0, K_NECK: 2.5, K_SHOULDER: 5.0, EPS: 0.01, SEG_MAX: 3.0, SEG_TRANS: 0.6, RIB_AMP: 0.8, RIB_PITCH: 3.4, DEFAULTS: { top: 18, h: 200, bulb: 62 } };
  const smax = (a, b, k) => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.max(a, b) + h * h * k * 0.25; };
  const smin = (a, b, k) => { const h = Math.max(k - Math.abs(a - b), 0) / k; return Math.min(a, b) - h * h * k * 0.25; };
  const sstep = (z, z0, z1) => { const t = Math.min(Math.max((z - z0) / (z1 - z0), 0), 1); return t * t * (3 - 2 * t); };
  const rib = (N, th) => { const c = Math.cos(N * th); return Math.sign(c) * Math.pow(Math.abs(c), 0.8); };
  const ribAmp = (r) => TP.RIB_AMP * Math.min(Math.max((r - 4) / 6, 0), 1);

  function topperGeo(top, h, bulb, check) {
    if (check === undefined) check = true;
    const g = { top, H: h, a: bulb / 2 };
    g.b = TP.BULB_FLAT * g.a;
    g.r_h = top / 2 + TP.CLEAR; g.r_s = g.r_h + TP.WALL_T; g.Z0 = TP.DEPTH - 4;
    const fa = g.a / g.b; g.phi_j = Math.atan(fa / TP.CONE_OUT);
    g.r_j = g.a * Math.sin(g.phi_j);
    if (check && !(g.r_j - g.r_s > 1.0)) throw new Error('Kula za mała względem tulei');
    g.z_j = g.Z0 + (g.r_j - g.r_s) / TP.CONE_OUT;
    g.z_e = g.z_j + g.b * Math.cos(g.phi_j); g.z_dome = g.z_e + g.b;
    g.k1 = Math.min(6.0, 0.8 * (g.r_j - g.r_s));
    g.r_neck = Math.max(TP.NECK * g.a, 4.5);
    g.z_ns = g.z_dome + TP.L_NECK;
    g.r_b = Math.max(TP.SPIRE_BASE * g.a, g.r_neck + 3.0);
    g.z_sb = g.z_ns + (g.r_b - g.r_neck) / TP.CONE_OUT;
    if (check && !(g.H - g.z_sb > 40)) throw new Error('Za niski czubek względem kuli');
    g.z_t = g.H - TP.R_TIP;
    g.trans = [[g.Z0 + 1.0, g.z_j], [g.z_e + 0.80 * g.b, g.z_e + 0.96 * g.b]];
    g.Ns = [Math.round(2 * Math.PI * g.r_s / TP.RIB_PITCH), Math.round(2 * Math.PI * g.a / TP.RIB_PITCH), Math.round(2 * Math.PI * g.r_b / TP.RIB_PITCH)];
    g.ceil = TP.DEPTH + (g.r_h - TP.R_FLAT) / TP.CONE;
    g.taper = (z) => { const t = (z - g.z_sb) / (g.z_t - g.z_sb); return TP.R_TIP + (g.r_b - TP.R_TIP) * Math.pow(Math.max(1 - t, 0), TP.SPIRE_P); };
    g.R = (z) => {
      const ell = g.a * Math.sqrt(Math.max(1 - ((z - g.z_e) / g.b) ** 2, 0));
      const lower = z <= g.z_j ? smax(g.r_s, g.r_s + TP.CONE_OUT * (z - g.Z0), g.k1) : ell;
      const N = smin(smax(g.r_neck, g.r_neck + TP.CONE_OUT * (z - g.z_ns), TP.K_NECK), g.taper(z), TP.K_SHOULDER);
      const core = z < g.z_dome + 2.0 ? smax(lower, N, TP.K_NECK) : N;
      const cap = z > g.z_t ? Math.sqrt(Math.max(TP.R_TIP ** 2 - (z - g.z_t) ** 2, 0)) : Infinity;
      return Math.min(core, cap);
    };
    g.ribField = (th, z) => {
      let w = [], wPrev = 1;
      for (const [za, zb] of g.trans) { const s = sstep(z, za, zb); w.push(wPrev * (1 - s)); wPrev *= s; }
      w.push(wPrev);
      let out = 0; for (let i = 0; i < w.length; i++) if (w[i] > 0) out += w[i] * rib(g.Ns[i], th);
      return out;
    };
    return g;
  }
  function topperRings(g) {
    const n = Math.floor(g.H / 0.02) + 1, zz = new Float64Array(n), rr = new Float64Array(n);
    for (let i = 0; i < n; i++) { zz[i] = g.H * i / (n - 1); rr[i] = g.R(zz[i]); }
    const keep = new Uint8Array(n); keep[0] = keep[n - 1] = 1;
    const st = [[0, n - 1]];
    while (st.length) {
      const [i, j] = st.pop(); if (j <= i + 1) continue;
      const dx = rr[j] - rr[i], dy = zz[j] - zz[i], nn = Math.hypot(dx, dy);
      let best = -1, bd = -1;
      for (let q = i + 1; q < j; q++) { const px = rr[q] - rr[i], py = zz[q] - zz[i]; const d = nn > 0 ? Math.abs(px * dy - py * dx) / nn : Math.hypot(px, py); if (d > bd) { bd = d; best = q; } }
      if (bd > TP.EPS) { keep[best] = 1; st.push([i, best], [best, j]); }
    }
    const zs = []; for (let i = 0; i < n; i++) if (keep[i]) zs.push(zz[i]);
    const out = [zs[0]];
    for (let q = 1; q < zs.length; q++) {
      const z0 = out[out.length - 1], z1 = zs[q];
      const inTr = g.trans.some(([ta, tb]) => !(z1 < ta || z0 > tb));
      const lim = inTr ? TP.SEG_TRANS : TP.SEG_MAX, m = Math.ceil((z1 - z0) / lim);
      for (let i = 0; i < m; i++) out.push(z0 + (z1 - z0) * (i + 1) / m);
    }
    return out;
  }
  function buildTopper(opt) {
    opt = Object.assign({}, TP.DEFAULTS, opt || {});
    const g = topperGeo(opt.top, opt.h, opt.bulb);
    const zr = topperRings(g), M = 8 * g.Ns[1];
    const cosT = new Float64Array(M), sinT = new Float64Array(M);
    for (let j = 0; j < M; j++) { const th = j * 2 * Math.PI / M; cosT[j] = Math.cos(th); sinT[j] = Math.sin(th); }
    const V = []; let nv = 0;
    const ring = (r, z, ribs) => {
      if (r < 1e-3) { V.push(0, 0, z); return { axis: true, n: nv++ }; }
      const base = nv;
      for (let j = 0; j < M; j++) {
        let rj = r;
        if (ribs) { const th = j * 2 * Math.PI / M; rj += ribAmp(r) * g.ribField(th, z); }
        V.push(rj * cosT[j], rj * sinT[j], z);
      }
      nv += M; return { axis: false, n: base };
    };
    const prof = [ring(g.r_h, 0, false)];
    for (const z of zr) prof.push(ring(g.R(z), z, true));
    prof.push(ring(0, g.ceil, false), ring(TP.R_FLAT, g.ceil, false), ring(g.r_h, TP.DEPTH, false));
    const F = [];
    for (let e = 0; e < prof.length; e++) {
      const A = prof[e], B = prof[(e + 1) % prof.length];
      if (A.axis && B.axis) continue;
      for (let j = 0; j < M; j++) {
        const j1 = (j + 1) % M;
        if (A.axis) F.push(A.n, B.n + j1, B.n + j);
        else if (B.axis) F.push(A.n + j, A.n + j1, B.n);
        else { F.push(A.n + j, A.n + j1, B.n + j); F.push(A.n + j1, B.n + j1, B.n + j); }
      }
    }
    const mesh = { positions: Float32Array.from(V), indices: Uint32Array.from(F) };
    const info = meshInfo(mesh);
    info.geo = { r_s: g.r_s, r_h: g.r_h, a: g.a, b: g.b, r_neck: g.r_neck, r_b: g.r_b, z_sb: g.z_sb, ceil: g.ceil, Ns: g.Ns, M };
    return { mesh, info };
  }
  function topperMin(top, bulb) {       // najmniejsza wysokość czubka dla danej średnicy czubka choinki i kuli; najmniejsza średnica kuli dla tulei
    const r_s = top / 2 + TP.CLEAR + TP.WALL_T, phi = Math.atan((1 / TP.BULB_FLAT) / TP.CONE_OUT);
    const bulbMin = Math.ceil(2 * (r_s + 2) / Math.sin(phi));
    const g = topperGeo(top, 1000, Math.max(bulb, bulbMin), false);
    return { bulbMin, hMin: Math.ceil(g.z_sb + 41) };
  }

  function loadFont(arrayBuffer) { return opentype.parse(arrayBuffer); }
  return { buildLabel, buildCutter, buildTopper, topperMin, toStl, zipStore, meshInfo, loadFont, LB, CT, TP, PETG };
});
