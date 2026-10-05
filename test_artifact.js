// Test podgladu (artifact/zebrowana_kolekcja.html) w Node: laduje rdzen (CORE_START..CORE_END) i zrzuca wartosci do JSON
// do porownania z Pythonem (test_artifact.py). Uzycie: node test_artifact.js [plik.html] > wynik.json
const fs = require('fs'), vm = require('vm'), path = require('path');
const file = process.argv[2] || path.join(__dirname, 'artifact', 'zebrowana_kolekcja.html');
const stlDir = process.argv[3] === '--stl' ? process.argv[4] : null;   // opcjonalnie: zapisz STL (vox 0,5) wybranych modeli do katalogu
const html = fs.readFileSync(file, 'utf8');
const a = html.indexOf('/*CORE_START*/'), b = html.indexOf('/*CORE_END*/');
if (a < 0 || b < 0) throw new Error('brak znacznikow CORE');
const ctx = {Math, console, Float32Array, Float64Array, Int32Array, Uint32Array, Uint8Array, ArrayBuffer, DataView, Map, Set, Object, Array, JSON, Number, String, Promise, setTimeout, Buffer};
vm.createContext(ctx);
vm.runInContext(html.slice(a, b) + `;this.X={M,ORDER,defaults,bunDef,eggDef,buildModel,finalize,mountFrame,mkGrid,fillBun,lineGrid,fileNames,triCount,LINE,D2R,exportGroups,stlBytes};`, ctx);
const X = ctx.X;
const out = {};
const b64 = F => Buffer.from(F.buffer, F.byteOffset, F.byteLength).toString('base64');
const gridOut = G => ({x0: G.x0, y0: G.y0, z0: G.z0, v: G.v, nx: G.nx, ny: G.ny, nz: G.nz, F: b64(G.F)});

// --- krolik
{
  const P = X.defaults('krolik'), B = X.bunDef(P), zs = [];
  for (let z = 0; z <= 121; z += 0.37) zs.push(z);
  const tilt = P.earTilt * X.D2R;
  out.bun = {zs, prof: zs.map(B.prof), P0: [B.P0(1), B.P0(-1)], frames: [X.mountFrame(1, B.P0(1), tilt), X.mountFrame(-1, B.P0(-1), tilt)], params: P};
  const G = X.mkGrid(-24, 24, -24, 24, -1, 125, 1.0);
  X.fillBun(G, B);
  out.grid_krolik = gridOut(G);
}
// --- jajko
{
  const P = X.defaults('jajko'), E = X.eggDef(P), zs = [];
  for (let z = 0; z <= 90; z += 0.41) zs.push(z);
  out.egg = {zs, R: zs.map(E.R), cup: zs.map(E.cupCav), cap: zs.map(E.capCav), P0: [E.P0(1), E.P0(-1)], cone: E.cone, ZA: E.ZA, params: P};
}
// --- dynia, balwan: pola zebrowane z line.json
for (const id of ['dynia', 'balwan']) {
  const P = X.defaults(id), r = X.lineGrid(id, P, 1.0);
  out['grid_' + id] = gridOut(r.G);
  out['grid_' + id].H = r.S.H;
}
// --- dym: wszystkie modele, szkic (vox 1,0): brak wyjatkow, brak NaN, liczba trojkatow i wymiary
out.smoke = {};
for (const id of X.ORDER) {
  const t0 = Date.now(), P = X.defaults(id), res = X.buildModel(id, P, {draft: true, lo: true});
  let nan = 0, n = 0;
  for (const q of res.parts) { n += q.m.i.length / 3; for (const v of q.m.p) if (!isFinite(v)) nan++; }
  const dims = X.finalize(res.parts);
  out.smoke[id] = {warn: res.warn, parts: res.parts.map(q => q.name), tris: n, nan, w: dims.w, h: dims.h, d: dims.d, ms: Date.now() - t0, files: X.fileNames(id, P)};
}
if (stlDir) {
  fs.mkdirSync(stlDir, {recursive: true});
  out.stl = [];
  for (const id of ['krolik', 'jajko', 'dynia', 'balwan']) {
    const gs = X.exportGroups(X.buildModel(id, X.defaults(id), {vox: 0.5}));
    for (const g of gs) { const f = (gs.length > 1 ? id + '_' + g.g : id) + '.stl'; fs.writeFileSync(path.join(stlDir, f), X.stlBytes(g.parts)); out.stl.push(f); }
  }
}
process.stdout.write(JSON.stringify(out));
