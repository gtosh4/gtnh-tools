"""Self-describing HTML 3D viewer (three.js from a CDN; textures embedded as data URIs)."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from .build import Build
from .geometry import SIDE_DIRS, faces_for, is_full_opaque
from .render import _neighbour_fn, _shade, describe
from .palette import Palette


def _on_boundary(f, side: int) -> bool:
    axis, val = {0: (1, 0), 1: (1, 1), 2: (2, 0), 3: (2, 1), 4: (0, 0), 5: (0, 1)}[side]
    return all(abs(p[axis] - val) < 1e-6 for p in f.pts)


def _side_of(n) -> int | None:
    for s, d in enumerate(SIDE_DIRS):
        if abs(n[0] - d[0]) < 1e-6 and abs(n[1] - d[1]) < 1e-6 and abs(n[2] - d[2]) < 1e-6:
            return s
    return None


def scene_data(build: Build, palette: Palette | None = None) -> dict:
    palette = palette or build.palette
    groups: dict[str, dict] = {}
    states: dict = {}
    block_list = []
    for pos, b in build.blocks.items():
        key = (b.name, b.meta, repr(sorted(b.te.items())) if b.te else None)
        if key not in states:
            states[key] = len(states)
        bi = len(block_list)
        block_list.append([pos[0], pos[1], pos[2], states[key]])
        x, y, z = pos
        for f in faces_for(b, palette, _neighbour_fn(build, pos)):
            side = _side_of(f.normal)
            if side is not None and _on_boundary(f, side):
                d = SIDE_DIRS[side]
                if is_full_opaque(build.blocks.get((x + d[0], y + d[1], z + d[2])), palette):
                    continue
            gkey = f.tex if (f.tex and palette.texture(f.tex) is not None) else f"#{(f.color or palette.texture_color(f.tex) or '#808080').lstrip('#')}"
            g = groups.setdefault(gkey, {"pos": [], "uv": [], "shade": [], "block": []})
            pts = [(p[0] + x, p[1] + y, p[2] + z) for p in f.pts]
            tris = [(0, 1, 2)] if len(pts) == 3 else [(0, 1, 2), (0, 2, 3)]
            s = 1.0 if f.bright else round(_shade(f.normal), 3)
            for t in tris:
                for i in t:
                    g["pos"].extend(round(c, 4) for c in pts[i])
                    g["uv"].extend((round(f.uvs[i][0], 4), round(1 - f.uvs[i][1], 4)))
                    g["shade"].append(s)
                g["block"].append(bi)
    textures = {}
    translucent = {}
    for gkey in groups:
        if gkey.startswith("#"):
            continue
        img = palette.texture(gkey)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        textures[gkey] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
        # semi-transparent pixels (glass, water, ice) need blending; cut-out textures use alphaTest
        translucent[gkey] = any(0 < v < 255 for v in img.getchannel("A").getdata())
    descr: list[str | None] = [None] * len(states)
    for b in build.blocks.values():
        i = states[(b.name, b.meta, repr(sorted(b.te.items())) if b.te else None)]
        if descr[i] is None:
            descr[i] = describe(b, palette)
    lo, hi = build.bounds()
    return {"name": build.name, "groups": groups, "textures": textures, "translucent": translucent,
            "blocks": block_list, "states": descr, "lo": lo, "hi": hi}


_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title>
<style>body{margin:0;overflow:hidden;background:#1e1f24;font:13px sans-serif;color:#ddd}
#ui{position:absolute;top:8px;left:8px;background:#000a;padding:8px 10px;border-radius:6px}
#tip{position:absolute;bottom:8px;left:8px;background:#000a;padding:6px 10px;border-radius:6px;white-space:pre}
input[type=range]{width:220px;vertical-align:middle}</style>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.160.0/build/three.module.js",
"three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}</script></head><body>
<div id="ui"><b>__TITLE__</b><br>
Show y ≤ <input id="ymax" type="range"> <span id="yv"></span><br>
<label><input id="only" type="checkbox"> only that layer</label>
<label><input id="grid" type="checkbox" checked> grid</label><br>
<small>drag: orbit · right-drag: pan · wheel: zoom · hover: block info</small></div>
<div id="tip"></div>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
const D = __DATA__;
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(devicePixelRatio); renderer.setSize(innerWidth, innerHeight);
renderer.localClippingEnabled = true; document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x1e1f24);
const [lo, hi] = [D.lo, D.hi];
const c = new THREE.Vector3((lo[0]+hi[0]+1)/2, (lo[1]+hi[1]+1)/2, (lo[2]+hi[2]+1)/2);
const span = Math.max(hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]) + 1;
const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 0.1, span*20);
camera.position.set(c.x + span*1.1, c.y + span*0.9, c.z + span*1.3);
const controls = new OrbitControls(camera, renderer.domElement); controls.target.copy(c); controls.update();
const top = new THREE.Plane(new THREE.Vector3(0,-1,0), hi[1]+1);
const bottom = new THREE.Plane(new THREE.Vector3(0,1,0), -lo[1]);
const planes = [top, bottom];
const loader = new THREE.TextureLoader(); const meshes = [];
for (const [key, g] of Object.entries(D.groups)) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(g.pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(g.uv, 2));
  const base = key.startsWith('#') ? new THREE.Color(key) : new THREE.Color(1,1,1);
  const col = []; for (const s of g.shade) col.push(base.r*s, base.g*s, base.b*s);
  geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  const opts = {vertexColors:true, clippingPlanes:planes, side:THREE.DoubleSide};
  if (!key.startsWith('#')) {
    const t = loader.load(D.textures[key]); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter;
    t.colorSpace = THREE.SRGBColorSpace; opts.map = t;
    if (D.translucent[key]) { opts.transparent = true; opts.depthWrite = false; } else opts.alphaTest = 0.1;
  }
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial(opts)); mesh.userData.block = g.block;
  scene.add(mesh); meshes.push(mesh);
}
const grid = new THREE.GridHelper(span+4, span+4, 0x555555, 0x333333);
grid.position.set(c.x, lo[1], c.z); scene.add(grid);
const ymax = document.getElementById('ymax'), yv = document.getElementById('yv'), only = document.getElementById('only');
ymax.min = lo[1]; ymax.max = hi[1]; ymax.value = hi[1];
function clip(){ const y = +ymax.value; yv.textContent = y; top.constant = y+1-1e-3;  // drop faces lying on y+1
  bottom.constant = only.checked ? -(y+1e-3) : -lo[1]; grid.position.y = only.checked ? y : lo[1]; }
ymax.oninput = clip; only.onchange = clip; document.getElementById('grid').onchange = e => grid.visible = e.target.checked; clip();
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tip = document.getElementById('tip');
addEventListener('pointermove', e => {
  mouse.set(e.clientX/innerWidth*2-1, -e.clientY/innerHeight*2+1); ray.setFromCamera(mouse, camera);
  const hit = ray.intersectObjects(meshes).find(h => h.point.y <= top.constant + 1e-3 && h.point.y >= -bottom.constant - 1e-3);
  if (!hit) { tip.textContent = ''; return; }
  const b = D.blocks[hit.object.userData.block[hit.faceIndex]];
  tip.textContent = `(${b[0]}, ${b[1]}, ${b[2]})  ${D.states[b[3]]}`;
});
addEventListener('resize', () => { camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); });
renderer.setAnimationLoop(() => renderer.render(scene, camera));
</script></body></html>"""


def write_html(build: Build, path: str | Path, palette: Palette | None = None) -> Path:
    data = scene_data(build, palette)
    html = _HTML.replace("__TITLE__", build.name).replace("__DATA__", json.dumps(data, separators=(",", ":")))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)
    return path
