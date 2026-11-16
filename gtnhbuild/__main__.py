"""CLI: python -m gtnhbuild <command> ...  (run from the repo root)."""
from __future__ import annotations

import argparse
import re
import runpy
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from . import render, schematic
from .build import Block, Build, format_bom
from .orient import DIR_NAMES, scheme_for
from .palette import SIDES, default


def _load(path: str) -> Build:
    p = Path(path)
    if p.suffix == ".py":
        ns = runpy.run_path(str(p), run_name="__gtnhbuild__")
        b = ns.get("build")
        if not isinstance(b, Build):
            sys.exit(f"{path} must define a module-level `build = Build(...)`")
        return b
    return schematic.load(p)


def cmd_search(a) -> None:
    from .lighting import block_light

    pal = default()
    rows = pal.search(a.query or "", mod=a.mod, regex=a.regex, solid=True if a.solid else None, color=a.color,
                      limit=100000 if a.light else a.limit)
    if a.light:
        rows = [r for r in rows if block_light(r[0].registry, r[0].meta, pal) > 0][:a.limit]
    for info, color in rows:
        light = block_light(info.registry, info.meta, pal)
        flags = "".join(c for c, on in (("S", info.opaque), ("T", info.render_pass == 1)) if on) + (f"L{light}" if light else "")
        name = re.sub("§.", "", info.name)
        print(f"{info.registry}:{info.meta:<3} {name:<40} {color or '':8} rt={info.render_type:<4} {flags}")
    if not rows:
        print("no matches")


def cmd_swatch(a) -> None:
    pal = default()
    rows = pal.search(a.query or "", mod=a.mod, regex=a.regex, solid=True if a.solid else None, color=a.color,
                      limit=a.limit)
    cols, cell, label_w = 4, 48, 260
    rows_n = (len(rows) + cols - 1) // cols
    img = Image.new("RGBA", (cols * (cell + label_w), max(1, rows_n) * (cell + 6)), (30, 30, 34, 255))
    d = ImageDraw.Draw(img)
    for k, (info, _) in enumerate(rows):
        x, y = (k % cols) * (cell + label_w), (k // cols) * (cell + 6)
        sprite = render.iso(_single(info.registry, info.meta), scale=cell // 2, label=False)
        img.alpha_composite(sprite.resize((cell, cell * sprite.height // sprite.width)), (x, y))
        d.text((x + cell + 4, y + 4), info.name[:38], fill=(240, 240, 240, 255))
        d.text((x + cell + 4, y + 20), f"{info.registry}:{info.meta}"[:42], fill=(160, 160, 170, 255))
    out = a.out or "out/swatch.png"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(out)


def _single(reg: str, meta: int) -> Build:
    b = Build(f"{reg}:{meta}")
    b.blocks[(0, 0, 0)] = Block(reg, meta)
    return b


def cmd_gradient(a) -> None:
    pal = default()
    wall = Build("gradient")
    pool = [Block(i.registry, i.meta) for i, _ in pal.search(a.pool_query, mod=a.pool_mod, solid=True, limit=500)] \
        if a.pool_query is not None else None
    if a.pool:
        pool = (pool or []) + [wall.block(p) for p in a.pool]
    blocks = wall.gradient((0, 0, 0), (a.length - 1, a.height - 1, 0), a.waypoints, pool=pool, steps=a.steps,
                           axis="x", style=a.style, seed=a.seed, scale=a.scale, face=a.face)
    for i, blk in enumerate(blocks):
        info = pal.info(blk.name, blk.meta)
        print(f"{i:>2}  {blk.name}:{blk.meta:<4} {info.name if info else ''}")
    out = a.out or "out/gradient.png"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    render.iso(wall, view="se", scale=a.cell, label=False).save(out)
    print(out)


def cmd_info(a) -> None:
    pal = default()
    reg, meta = pal.resolve(a.block)
    info = pal.info(reg, meta)
    print(f"{info.registry}:{info.meta}  {info.name}")
    print(f"  item {info.gtnh_item}  opaque={info.opaque} full={info.normal} render_type={info.render_type} "
          f"pass={info.render_pass} light={info.light} bounds={info.bounds}")
    for side, tex in zip(SIDES, pal.face_textures(reg, meta)):
        print(f"  {side:<5} {tex}  {pal.texture_color(tex) or ''}")
    sch = scheme_for(reg, meta, pal)
    if sch:
        def label(v):
            return "xyz"[[abs(c) for c in v].index(1)] if sch.axis else DIR_NAMES[v]
        print(f"  orientation metas (bits {sch.mask:#x}" + (", axis" if sch.axis else "") + "): " +
              ", ".join(f"{k}={label(v)}" for k, v in sorted(sch.table.items())) +
              ("  (+4 = upside-down)" if info.render_type == 10 else ""))
    variants = pal.variants(reg)
    if len(variants) > 1:
        print("  variants: " + "; ".join(f"{v.meta}={v.name}" for v in variants[:40]))


def cmd_preview(a) -> None:
    b = _load(a.file)
    prefix = a.out or f"out/{b.name}"
    paths = b.preview(prefix, views=tuple(a.views.split(",")), scale=a.scale, slices=not a.no_slices,
                      html=not a.no_html, cell=a.cell)
    for k, v in paths.items():
        print(f"{k:7} {v}")


def cmd_layers(a) -> None:
    b = _load(a.file)
    ys = None
    if a.y:
        lo, _, hi = a.y.partition(":")
        ys = list(range(int(lo), int(hi or lo) + 1))
    print(render.ascii_layers(b, ys))


def cmd_bom(a) -> None:
    print(format_bom(_load(a.file)), end="")


def cmd_light(a) -> None:
    from .lighting import light_sheet, report

    b = _load(a.file)
    print(report(b), end="")
    if a.out:
        sheet = light_sheet(b)
        if sheet is not None:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            sheet.save(a.out)
            print(a.out)


def cmd_run(a) -> None:
    b = _load(a.file)
    issues = b.check()
    for i in issues:
        print("check:", i)
    print(b)
    for path in b.save(a.schematic):
        print(f"schematic {path}")
    from .lighting import report

    print(report(b).splitlines()[0])
    if not a.no_preview:
        for k, v in b.preview(a.out or f"out/{b.name}").items():
            print(f"{k:9} {v}")


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m gtnhbuild")
    sub = p.add_subparsers(dest="cmd", required=True)

    def search_args(s):
        s.add_argument("query", nargs="?")
        s.add_argument("--mod")
        s.add_argument("-r", "--regex", action="store_true")
        s.add_argument("--solid", action="store_true", help="opaque full blocks only")
        s.add_argument("--color", help="sort by closest top-face colour, e.g. '#8a6b4a'")
        s.add_argument("--limit", type=int, default=30)
        s.add_argument("--light", action="store_true", help="light-emitting blocks only")

    s = sub.add_parser("search", help="find blocks by name / registry / colour")
    search_args(s)
    s.set_defaults(fn=cmd_search)
    s = sub.add_parser("swatch", help="PNG grid of matching blocks (rendered), to pick materials visually")
    search_args(s)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_swatch, limit=24)
    s = sub.add_parser("info", help="one block: textures, flags, orientation metas, variants")
    s.add_argument("block")
    s.set_defaults(fn=cmd_info)
    s = sub.add_parser("gradient", help="colour gradient between blocks: print the strip, render a sample wall")
    s.add_argument("waypoints", nargs="+", help="two or more block specs, low end first")
    s.add_argument("--pool-query", help="search text for in-between candidates (solid blocks), e.g. marble")
    s.add_argument("--pool-mod", help="restrict the pool search to one mod")
    s.add_argument("--pool", nargs="*", help="extra candidate block specs")
    s.add_argument("--steps", type=int)
    s.add_argument("--style", default="bands", choices=("bands", "dither", "noise", "patches"))
    s.add_argument("--face", default="side", choices=("side", "top", "all"))
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--scale", type=float, default=6.0)
    s.add_argument("--length", type=int, default=24)
    s.add_argument("--height", type=int, default=10)
    s.add_argument("--cell", type=int, default=16)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_gradient)
    s = sub.add_parser("run", help="run a build script (defines `build`), save .schematic + previews")
    s.add_argument("file")
    s.add_argument("--schematic", help="output path (default: Threshold schematics folder)")
    s.add_argument("--out", help="preview prefix (default out/<name>)")
    s.add_argument("--no-preview", action="store_true")
    s.set_defaults(fn=cmd_run)
    s = sub.add_parser("preview", help="previews for a .schematic or build script")
    s.add_argument("file")
    s.add_argument("--out")
    s.add_argument("--views", default="se,nw", help="comma list of se,sw,nw,ne")
    s.add_argument("--scale", type=int, default=16)
    s.add_argument("--cell", type=int, default=16)
    s.add_argument("--no-slices", action="store_true")
    s.add_argument("--no-html", action="store_true")
    s.set_defaults(fn=cmd_preview)
    s = sub.add_parser("layers", help="ASCII layer maps with legend")
    s.add_argument("file")
    s.add_argument("--y", help="layer or range, e.g. 3 or 0:4")
    s.set_defaults(fn=cmd_layers)
    s = sub.add_parser("bom", help="bill of materials")
    s.add_argument("file")
    s.set_defaults(fn=cmd_bom)
    s = sub.add_parser("light", help="light sources, block light on floors, hostile-spawn spots at night")
    s.add_argument("file")
    s.add_argument("--out", help="PNG with light levels per walk layer")
    s.set_defaults(fn=cmd_light)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
