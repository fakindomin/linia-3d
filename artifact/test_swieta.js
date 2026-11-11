/* Test rdzenia artefaktu "Swiateczne dodatki" w Node: buduje etykiety, foremki i czubek, sprawdza szczelnosc (kazda krawedz w dwoch trojkatach, przeciwnie skierowana),
   zapisuje STL do out/js/ i podsumowanie do out/js/_info.json (porownanie z Pythonem: artifact/test_swieta.py). */
const fs = require('fs'), path = require('path');
const ClipperLib = require('clipper-lib'), opentype = require('opentype.js'), earcut = require('earcut');
const triangulate = (contour, holes) => {
  const flat = [], hi = [];
  contour.forEach((p) => flat.push(p[0], p[1]));
  holes.forEach((h) => { hi.push(flat.length / 2); h.forEach((p) => flat.push(p[0], p[1])); });
  return earcut(flat, hi, 2);
};
const core = require('./swieta_core.js')({ ClipperLib, opentype, triangulate });
const root = path.join(__dirname, '..');
const fontBuf = fs.readFileSync(path.join(root, 'fonts', 'Poppins-Bold-subset.ttf'));
const font = core.loadFont(fontBuf.buffer.slice(fontBuf.byteOffset, fontBuf.byteOffset + fontBuf.length));
const outl = JSON.parse(fs.readFileSync(path.join(__dirname, 'swieta_outlines.json'), 'utf8'));
const outDir = path.join(root, 'out', 'js'); fs.mkdirSync(outDir, { recursive: true });

function watertight(m) {
  const I = m.indices, E = new Map(); let bad = 0;
  for (let i = 0; i < I.length; i += 3) for (let k = 0; k < 3; k++) {
    const a = I[i + k], b = I[i + (k + 1) % 3], key = a < b ? a + '_' + b : b + '_' + a, dir = a < b ? 1 : -1;
    const e = E.get(key) || [0, 0]; if (dir > 0) e[0]++; else e[1]++; E.set(key, e);
  }
  for (const [, e] of E) if (e[0] !== 1 || e[1] !== 1) bad++;
  return { edges: E.size, bad };
}
const res = {};
function emit(name, r) {
  const wt = watertight(r.mesh);
  fs.writeFileSync(path.join(outDir, name + '.stl'), Buffer.from(core.toStl(r.mesh)));
  res[name] = Object.assign({}, r.info, { badEdges: wt.bad });
  delete res[name].lo; delete res[name].hi;
  console.log(name.padEnd(34), 'tri', String(r.info.tris).padStart(7), 'V', r.info.volume.toFixed(1).padStart(9), 'ext', r.info.extents.map((v) => v.toFixed(2)).join(' x '), wt.bad ? 'NIESZCZELNA: ' + wt.bad : 'szczelna');
}
let t0 = Date.now();
for (const [n, cap] of [['Ania', 11], ['Łukasz', 11], ['Babcia Ela', 11], ['Jan', 14]]) emit('etykieta_' + n.replace(/\s/g, '_') + '_' + cap, core.buildLabel(font, n, cap));
for (const k of ['choinka', 'renifer', 'balwan', 'ludzik', 'gwiazdka']) emit('foremka_' + k, core.buildCutter(outl[k], {}));
emit('foremka_renifer_FL8x3_s1.2', core.buildCutter(outl.renifer, { FL_W: 8, FL_T: 3, scale: 1.2 }));
console.log('etykiety + foremki', Date.now() - t0, 'ms'); t0 = Date.now();
emit('czubek_18_240_62_62', core.buildTopper({}));
emit('czubek_14_200_54_50', core.buildTopper({ top: 14, h: 200, bulb: 54, sleeve: 50 }));
emit('czubek_26_260_80_70', core.buildTopper({ top: 26, h: 260, bulb: 80, sleeve: 70 }));
emit('czubek_10_180_40_30', core.buildTopper({ top: 10, h: 180, bulb: 40, sleeve: 30 }));
console.log('czubki', Date.now() - t0, 'ms');
// ZIP: poprawnosc kontrolna (python -m zipfile)
fs.writeFileSync(path.join(outDir, '_test.zip'), Buffer.from(core.zipStore('etykieta_Ania.stl', core.toStl(core.buildLabel(font, 'Ania', 11).mesh))));
fs.writeFileSync(path.join(outDir, '_info.json'), JSON.stringify(res, null, 1));
process.exit(Object.values(res).some((r) => r.badEdges) ? 1 : 0);
