"""Light emission and a night-time block-light / mob-spawn check for a build.

Emission sources (blocks.db `light_value` misses the ones computed per position):
- ArchitectureCraft `shapeSE` (Glow) shapes: 15 (BlockShape.getLightValue)
- ExtraUtilities Lapis Caelestis (`greenscreen`): (r+g+b)/3*15 of its colour (BlockGreenScreen.getLightLevel)
- Forge Multipart cells: their brightest part's material (glowstone, coloured glowstone, inverted
  ProjectRed lamps 16..31 = 15, Lapis Caelestis, ...)
Full-bright but dark: chisel Anti Blocks render at full brightness, emit no light, and refuse spawns
(BlockCarvableAntiBlock.canCreatureSpawn = false).

Propagation is vanilla block light: -1 per step, stopped by opaque cubes, slabs and stairs (light
opacity 255 in 1.7.10); water/ice cost 3/2 per step. Microblock, Carpenter's and ArchitectureCraft
cells pass light (approximation: FMP/AC/CB report no light opacity of their own here).
Spawn check (hostile, at night so sky light ~0): the cell and the one above are empty or non-colliding,
the block below has a solid top (full opaque cube, top slab, upside-down stairs) and allows spawns,
and block light at the cell is <= 7. Only floors that belong to the build are checked.
"""
from __future__ import annotations

import struct
from collections import deque
from typing import TYPE_CHECKING

from PIL import ImageDraw

if TYPE_CHECKING:
    from .build import Block, Build
    from .palette import Palette

Pos = tuple[int, int, int]


def _f32(v: float) -> float:
    return struct.unpack("f", struct.pack("f", v))[0]


# BlockGreenScreen.cols (r, g, b) by meta; light = (int)((r+g+b)/3f*15f) in float32 (getLightLevel)
_GREENSCREEN_RGB = ((1, 1, 1), (1, .5, 0), (1, 0, 1), (0, .5, .85), (1, 1, 0), (0, 1, 0), (1, .6, .65), (.5, .5, .5),
                    (.8, .8, .8), (0, 1, 1), (.7, .2, 1), (0, 0, 1), (.5, .2, 0), (0, .6, 0), (1, 0, 0), (0, 0, 0))
_GREENSCREEN_LIGHT = tuple(int(_f32(_f32(_f32(_f32(_f32(r) + _f32(g)) + _f32(b)) / 3) * 15))
                           for r, g, b in _GREENSCREEN_RGB)
NO_SPAWN = {"chisel:antiBlock", "minecraft:bedrock"}
_PASSABLE_RT = {1, 2, 5, 6, 9, 12, 23, 40}  # plants, torches, redstone, crops, rails, lever, lily pad, tall plants


def full_bright(reg: str, meta: int) -> bool:
    """Rendered at full brightness regardless of surrounding light."""
    return (reg in ("ExtraUtilities:greenscreen", "chisel:antiBlock", "ArchitectureCraft:shapeSE")
            or (reg == "ProjRed|Illumination:projectred.illumination.lamp" and meta >= 16))


def flat_color(reg: str, meta: int) -> str | None:
    """Lapis Caelestis is an untextured flat colour (its texture is white, tinted per meta)."""
    if reg == "ExtraUtilities:greenscreen":
        return "#" + "".join(f"{round(c * 255):02x}" for c in _GREENSCREEN_RGB[meta & 15])
    return None


def block_light(reg: str, meta: int, palette: "Palette") -> int:
    if reg == "ExtraUtilities:greenscreen":
        return _GREENSCREEN_LIGHT[meta & 15]
    if reg == "ArchitectureCraft:shapeSE":
        return 15
    info = palette.info(reg, meta)
    return info.light if info else 0


def emission(b: "Block", palette: "Palette") -> int:
    from .microblocks import is_fmp, material_light, parts_of

    if is_fmp(b):
        return max((material_light(p["material"], palette) for p in parts_of(b)), default=0)
    return block_light(b.name, b.meta, palette)


def _cost(b: "Block | None", palette: "Palette") -> int | None:
    """Light lost entering this cell; None = blocked."""
    if b is None or b.te is not None:
        return 1
    info = palette.info(b.name, b.meta)
    if info is None:
        return 1
    if info.opaque or info.render_type == 10 or _is_slab(b, info):
        return None
    if info.render_type == 4 and "water" in b.name:
        return 3
    if "ice" in b.name:
        return 2
    return 1


def _is_slab(b, info) -> bool:
    x0, y0, z0, x1, y1, z1 = info.bounds
    return x0 == 0 and z0 == 0 and x1 == 1 and z1 == 1 and (y1 - y0) <= 0.5 + 1e-6 and "slab" in b.name.lower()


def light_map(build: "Build", margin: int = 2) -> dict[Pos, int]:
    """Block light for every non-blocking cell inside the build's bounds (+margin)."""
    pal = build.palette
    lo, hi = build.bounds()
    lo = (lo[0] - margin, lo[1] - margin, lo[2] - margin)
    hi = (hi[0] + margin, hi[1] + margin, hi[2] + margin)
    light: dict[Pos, int] = {}
    queue: deque = deque()
    for pos, b in build.blocks.items():
        e = emission(b, pal)
        if e > 0:
            light[pos] = max(light.get(pos, 0), e)
            queue.append(pos)
    while queue:
        x, y, z = pos = queue.popleft()
        level = light[pos]
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            q = (x + d[0], y + d[1], z + d[2])
            if not all(lo[i] <= q[i] <= hi[i] for i in range(3)):
                continue
            cost = _cost(build.blocks.get(q), pal)
            if cost is None:
                continue
            nl = level - cost
            if nl > light.get(q, 0):
                light[q] = nl
                queue.append(q)
    return light


def _solid_top(b: "Block | None", palette: "Palette") -> bool:
    if b is None or b.te is not None or b.name in NO_SPAWN:
        return False
    info = palette.info(b.name, b.meta)
    if info is None:
        return False
    if info.render_type == 10:
        return bool(b.meta & 4)
    if _is_slab(b, info):
        return bool(b.meta & 8) and info.meta != b.meta
    return info.opaque and info.bounds == (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)


def _clear(b: "Block | None", palette: "Palette") -> bool:
    if b is None:
        return True
    if b.te is not None:
        return False
    info = palette.info(b.name, b.meta)
    return bool(info and info.render_type in _PASSABLE_RT)


def spawn_spots(build: "Build", light: dict[Pos, int] | None = None) -> dict[Pos, int]:
    """Walkable cells on the build's own floors -> block light there. Light <= 7 means hostiles spawn.
    On terrain builds only floors the design placed, or carved space above them, count."""
    pal = build.palette
    light = light if light is not None else light_map(build)
    own = build.changed() if build.base is not None else None
    out = {}
    for (x, y, z), b in build.blocks.items():
        p = (x, y + 1, z)
        if own is not None and (x, y, z) not in own and p not in own:
            continue
        if _solid_top(b, pal) and _clear(build.blocks.get(p), pal) and _clear(build.blocks.get((x, y + 2, z)), pal):
            out[p] = light.get(p, 0)
    return out


def report(build: "Build") -> str:
    """Emitters, darkest walkable spots and an ASCII map of floors (hex light, '!' = hostile spawn)."""
    pal = build.palette
    light = light_map(build)
    spots = spawn_spots(build, light)
    emitters: dict[str, int] = {}
    from .render import describe

    for b in build.blocks.values():
        e = emission(b, pal)
        if e:
            label = describe(b, pal)  # includes "(light N)"
            emitters[label] = emitters.get(label, 0) + 1
    dark = {p: v for p, v in spots.items() if v <= 7}
    lines = [f"{build.name}: {len(spots)} walkable floor cells, {len(dark)} can spawn hostiles at night"]
    lines += [f"  {n:>4} x {label}" for label, n in sorted(emitters.items(), key=lambda kv: -kv[1])] or ["  no light sources"]
    if not spots:
        return "\n".join(lines) + "\n"
    xs, _, zs = zip(*spots)
    lo, hi = (min(xs), 0, min(zs)), (max(xs), 0, max(zs))
    for y in sorted({p[1] for p in spots}):
        lines += ["", f"walk layer y={y}  (floor at y={y - 1}; hex = block light, ! = light<=7, # = solid)"]
        for z in range(lo[2], hi[2] + 1):
            row = []
            for x in range(lo[0], hi[0] + 1):
                p = (x, y, z)
                if p in spots:
                    row.append("!" if spots[p] <= 7 else f"{spots[p]:X}")
                elif p in build.blocks:
                    row.append("#")
                else:
                    row.append(".")
            lines.append(f"{z:>5} {''.join(row)}")
    return "\n".join(lines) + "\n"


def light_sheet(build: "Build", cell: int = 24):
    """Slices of each walk layer with light levels written in and spawnable cells tinted red."""
    from PIL import Image

    from .render import slice_image

    light = light_map(build)
    spots = spawn_spots(build, light)
    lo, _ = build.bounds()
    ys = sorted({p[1] for p in spots})
    imgs = []
    for y in ys:
        img = slice_image(build, y, cell=cell, arrows=False)
        over = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        ox, oy = 22, 38  # slice_image margins
        for (x, yy, z), v in spots.items():
            if yy != y:
                continue
            X, Z = ox + (x - lo[0]) * cell, oy + (z - lo[2]) * cell
            colour = (220, 40, 40, 120) if v <= 7 else (255, 210, 60, 25 + v * 8)
            d.rectangle([X + 1, Z + 1, X + cell - 1, Z + cell - 1], fill=colour)
            d.text((X + cell / 2 - 4, Z + cell / 2 - 6), f"{v:X}", fill=(255, 255, 255, 255),
                   stroke_width=1, stroke_fill=(0, 0, 0, 255))
        img.alpha_composite(over)
        imgs.append(img)
    if not imgs:
        return None
    w = max(i.width for i in imgs)
    sheet = Image.new("RGBA", (w, sum(i.height + 6 for i in imgs)), (10, 10, 12, 255))
    yoff = 0
    for im in imgs:
        sheet.alpha_composite(im, (0, yoff))
        yoff += im.height + 6
    return sheet
