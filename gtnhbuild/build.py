"""Sparse voxel build: blocks keyed by (x, y, z), plus shape primitives.

Coordinates: +x = east, +y = up, +z = south (Minecraft). All ranges are inclusive.
(0, 0, 0) is the paste anchor: with WorldEdit, `//schem load` + `//paste` puts build (0,0,0) at the
player's feet. Negative coordinates are fine.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterator

from . import orient
from .palette import Palette, default as default_palette

Pos = tuple[int, int, int]


@dataclass(frozen=True)
class Block:
    """A block state: registry name + metadata, plus tile-entity NBT (without id/x/y/z) if any."""

    name: str
    meta: int = 0
    te: dict | None = field(default=None, hash=False)  # NBT compound (nbt.* typed values); includes "id"

    def with_meta(self, meta: int) -> "Block":
        return Block(self.name, meta, self.te)

    def __str__(self) -> str:
        return f"{self.name}:{self.meta}" + (" +TE" if self.te else "")


AIR = Block("minecraft:air")


def _box(a: Pos, b: Pos) -> Iterator[Pos]:
    (x0, x1), (y0, y1), (z0, z1) = (sorted((a[i], b[i])) for i in range(3))
    for y in range(y0, y1 + 1):
        for z in range(z0, z1 + 1):
            for x in range(x0, x1 + 1):
                yield x, y, z


class Build:
    """Mutable voxel model. Primitives return self so calls chain."""

    def __init__(self, name: str = "build", palette: Palette | None = None, anchor: Pos = (0, 0, 0)):
        self.name = name
        self.blocks: dict[Pos, Block] = {}
        self.palette = palette or default_palette()
        # WorldEdit paste anchor: the block the player's feet are in for `//paste`. Builds in world
        # coordinates (terrain.py) set it to a real stand-on spot; `//paste -o` ignores it.
        self.anchor: Pos = anchor
        # Terrain this build was carved from (terrain.World.load). Reports, previews and checks then
        # cover only what the design changes; the schematic still carries the whole box.
        self.base: dict[Pos, Block] | None = None
        # Item name -> numeric id used for item stacks written into tile-entity NBT (the target world's
        # registry; terrain loads set the server's). Schematics carry it as WorldEdit's ItemMapping.
        self.item_registry: dict[str, int] | None = None
        # The world box a terrain build covers (terrain.World.load): the schematic is exactly this box,
        # and blocks may not be set outside it (they would paste over whatever is there).
        self.box: tuple[Pos, Pos] | None = None

    def inside(self, p: Pos) -> bool:
        return self.box is None or all(self.box[0][i] <= p[i] <= self.box[1][i] for i in range(3))

    def item_id(self, name: str) -> int:
        """Numeric item id for `name` in this build's item registry (default: palette level.dat)."""
        reg = self.item_registry or self.palette.numeric_ids()[1]
        if name not in reg:
            raise KeyError(f"item {name} not in the item registry")
        return reg[name]

    def changed(self) -> set[Pos]:
        """Cells whose block differs from `base` (placed, replaced or cleared); all cells if no base."""
        if self.base is None:
            return set(self.blocks)
        return {p for p in self.blocks.keys() | self.base.keys() if self.blocks.get(p) != self.base.get(p)}

    def design(self) -> "Build":
        """New build holding only the blocks placed or replaced relative to `base`."""
        out = Build(self.name, self.palette, self.anchor)
        out.item_registry = self.item_registry
        out.blocks = {p: b for p, b in self.blocks.items() if self.base is None or self.base.get(p) != b}
        return out

    # ---- block construction ------------------------------------------------------------------
    def block(self, spec: str | Block, meta: int | None = None) -> Block:
        """Validated block from 'mod:name', 'mod:name:meta' or an exact localized name."""
        if isinstance(spec, Block):
            return spec if meta is None else spec.with_meta(meta)
        reg, m = self.palette.resolve(spec)
        return Block(reg, m if meta is None else meta)

    def stairs(self, spec: str, ascend: str, upside_down: bool = False) -> Block:
        """Stairs whose high (back) side is toward `ascend` (n/e/s/w) — you walk up toward it."""
        b = self.block(spec)
        return b.with_meta(orient.stairs_meta(ascend, upside_down))

    def slab(self, spec: str, top: bool = False) -> Block:
        b = self.block(spec)
        return b.with_meta((b.meta & 7) | (8 if top else 0))

    def pillar(self, spec: str, axis: str = "y") -> Block:
        """Logs / pillar-style blocks (meta bits 2-3 = axis); keeps the wood-type bits."""
        b = self.block(spec)
        return b.with_meta(orient.pillar_meta(b.meta, axis))

    def facing(self, spec: str, direction: str) -> Block:
        """Front-facing blocks with 2..5 metas (furnace, chest, ladder, wall sign, dispenser…)."""
        b = self.block(spec)
        return b.with_meta(orient.facing_meta(b.name, direction))

    def ac(self, shape: int | str, material: str | Block, front: str = "n", up: str = "u", *,
           secondary: str | Block | None = None, glow: bool = False) -> Block:
        """ArchitectureCraft shape (see modblocks.SHAPES) made of `material`. `front` is the shape's
        local north: the side a roof tile slopes down to; corners slope to front and front+90° clockwise."""
        from .modblocks import ac_shape

        return ac_shape(shape, self.block(material), front=front, up=up,
                        secondary=self.block(secondary) if secondary else None, glow=glow)

    def cb_block(self, cover: str | Block, slab: str | None = None) -> Block:
        from .modblocks import cb_block

        return cb_block(self.block(cover), slab)

    def cb_slope(self, cover: str | Block, faces: str = "n", kind: str = "wedge", upside_down: bool = False) -> Block:
        from .modblocks import cb_slope

        return cb_slope(self.block(cover), faces, kind, upside_down)

    def cb_stairs(self, cover: str | Block, faces: str = "n", kind: str = "normal", upside_down: bool = False) -> Block:
        from .modblocks import cb_stairs

        return cb_stairs(self.block(cover), faces, kind, upside_down)

    def mb(self, kind: str, material: str | Block, where: str = "", size: int = 1) -> dict:
        """One Forge Multipart microblock part (see microblocks.part): kind face/hollow/corner/edge/post,
        size in eighths (1 cover/nook/strip, 2 panel/corner/post, 4 slab/notch/pillar)."""
        from .microblocks import part

        return part(kind, self.block(material), where, size)

    def micro(self, *parts: dict) -> Block:
        """A microblock cell from parts made with mb()."""
        from .microblocks import micro

        return micro(list(parts))

    def add_micro(self, x: int, y: int, z: int, *parts: dict) -> "Build":
        """Add parts to the microblock cell at (x,y,z), creating it if the spot is empty."""
        from .microblocks import is_fmp, micro, parts_of

        cur = self.blocks.get((x, y, z))
        if cur is not None and not is_fmp(cur):
            raise ValueError(f"({x},{y},{z}) holds {cur}, not a microblock cell")
        self.blocks[(x, y, z)] = micro((parts_of(cur) if cur else []) + list(parts))
        return self

    # ---- access -------------------------------------------------------------------------------
    def _coerce(self, block: str | Block | None) -> Block | None:
        if block is None or isinstance(block, Block):
            return block
        return self.block(block)

    def set(self, x: int, y: int, z: int, block: str | Block | None) -> "Build":
        """Place one block; None or AIR removes it."""
        if not self.inside((x, y, z)):
            raise ValueError(f"{self.name}: ({x},{y},{z}) is outside the build's box {self.box}")
        b = self._coerce(block)
        if b is None or b.name == AIR.name:
            self.blocks.pop((x, y, z), None)
        else:
            self.blocks[(x, y, z)] = b
        return self

    def get(self, x: int, y: int, z: int) -> Block | None:
        return self.blocks.get((x, y, z))

    def __len__(self) -> int:
        return len(self.blocks)

    def bounds(self) -> tuple[Pos, Pos]:
        """The build's box if it has one (every block must lie in it), else the box around every block."""
        if self.box is not None:
            stray = [p for p in self.blocks if not self.inside(p)]
            if stray:
                raise ValueError(f"{self.name}: {len(stray)} blocks outside the box {self.box}, e.g. {stray[:3]}")
            return self.box
        if not self.blocks:
            return (0, 0, 0), (0, 0, 0)
        xs, ys, zs = zip(*self.blocks)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def size(self) -> tuple[int, int, int]:
        lo, hi = self.bounds()
        return tuple(hi[i] - lo[i] + 1 for i in range(3))

    # ---- primitives ---------------------------------------------------------------------------
    def fill(self, a: Pos, b: Pos, block: str | Block | None) -> "Build":
        blk = self._coerce(block)
        for p in _box(a, b):
            self.set(*p, blk)
        return self

    def clear(self, a: Pos, b: Pos) -> "Build":
        return self.fill(a, b, None)

    def hollow(self, a: Pos, b: Pos, block: str | Block, *, clear_inside: bool = True) -> "Build":
        """Six-sided shell (floor, ceiling, walls)."""
        blk = self._coerce(block)
        lo = tuple(min(a[i], b[i]) for i in range(3))
        hi = tuple(max(a[i], b[i]) for i in range(3))
        for p in _box(lo, hi):
            on_edge = any(p[i] in (lo[i], hi[i]) for i in range(3))
            if on_edge:
                self.set(*p, blk)
            elif clear_inside:
                self.set(*p, None)
        return self

    def walls(self, a: Pos, b: Pos, block: str | Block) -> "Build":
        """Four vertical walls of the box (no floor/ceiling)."""
        blk = self._coerce(block)
        lo = tuple(min(a[i], b[i]) for i in range(3))
        hi = tuple(max(a[i], b[i]) for i in range(3))
        for x, y, z in _box(lo, hi):
            if x in (lo[0], hi[0]) or z in (lo[2], hi[2]):
                self.set(x, y, z, blk)
        return self

    def outline(self, a: Pos, b: Pos, block: str | Block) -> "Build":
        """The 12 edges of a box (frames, pillars + beams)."""
        blk = self._coerce(block)
        lo = tuple(min(a[i], b[i]) for i in range(3))
        hi = tuple(max(a[i], b[i]) for i in range(3))
        for p in _box(lo, hi):
            if sum(p[i] in (lo[i], hi[i]) for i in range(3)) >= 2:
                self.set(*p, blk)
        return self

    def line(self, a: Pos, b: Pos, block: str | Block) -> "Build":
        """3D Bresenham-style line (inclusive)."""
        blk = self._coerce(block)
        n = max(abs(b[i] - a[i]) for i in range(3))
        for t in range(n + 1):
            f = t / n if n else 0.0
            self.set(*(round(a[i] + (b[i] - a[i]) * f) for i in range(3)), blk)
        return self

    def cylinder(self, base: Pos, radius: float, height: int, block: str | Block, *, hollow: bool = False,
                 axis: str = "y", thickness: float = 1.0) -> "Build":
        """Cylinder whose base-centre is `base`, extending `height` blocks along +axis."""
        blk = self._coerce(block)
        r = int(math.ceil(radius))
        for u in range(-r, r + 1):
            for v in range(-r, r + 1):
                d = math.hypot(u, v)
                if d > radius + 0.5 or (hollow and d <= radius + 0.5 - thickness):
                    continue
                for h in range(height):
                    off = {"y": (u, h, v), "x": (h, u, v), "z": (u, v, h)}[axis]
                    self.set(base[0] + off[0], base[1] + off[1], base[2] + off[2], blk)
        return self

    def sphere(self, center: Pos, radius: float, block: str | Block, *, hollow: bool = False,
               thickness: float = 1.0, half: str | None = None) -> "Build":
        """Sphere; half='top' or 'bottom' for a dome/bowl (cut plane through the centre is kept)."""
        blk = self._coerce(block)
        r = int(math.ceil(radius))
        for dx, dy, dz in _box((-r, -r, -r), (r, r, r)):
            if half == "top" and dy < 0 or half == "bottom" and dy > 0:
                continue
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d > radius + 0.5 or (hollow and d <= radius + 0.5 - thickness):
                continue
            self.set(center[0] + dx, center[1] + dy, center[2] + dz, blk)
        return self

    def where(self, pred: Callable[[Pos, Block], bool]) -> list[Pos]:
        return [p for p, b in self.blocks.items() if pred(p, b)]

    def replace(self, old: str | Block, new: str | Block | None, a: Pos | None = None, b: Pos | None = None) -> "Build":
        """Swap every `old` (registry name, or exact Block when meta matters) for `new` in an optional box."""
        new_b = self._coerce(new)
        match_name = old if isinstance(old, str) and ":" in old and self.palette.known(old) else None
        old_b = None if match_name else self._coerce(old)
        lo = hi = None
        if a is not None and b is not None:
            lo = tuple(min(a[i], b[i]) for i in range(3))
            hi = tuple(max(a[i], b[i]) for i in range(3))
        for p, blk in list(self.blocks.items()):
            if lo and not all(lo[i] <= p[i] <= hi[i] for i in range(3)):
                continue
            if (match_name and blk.name == match_name) or (old_b is not None and blk == old_b):
                self.set(*p, new_b)
        return self

    def gradient(self, a: Pos, b: Pos, waypoints: list[str | Block], *, pool: list[str | Block] | None = None,
                 steps: int | None = None, axis: str = "y", style: str = "bands", seed: int = 0,
                 scale: float = 6.0, face: str = "side", hollow: bool = False,
                 only: Callable[[Pos, Block | None], bool] | None = None) -> list[Block]:
        """Fill a..b with blocks stepping in colour through `waypoints` (see gradient.py): `pool` adds
        in-between candidates (else the waypoints alone), `style` bands | dither | noise | patches,
        `axis` x/y/z or -x/-y/-z, `face` side | top | all picks which faces' colour counts. Returns the
        strip used, low end first."""
        from . import gradient

        wps = [self._coerce(w) for w in waypoints]
        cands = [self._coerce(p) for p in pool] if pool is not None else None
        blocks = gradient.strip(self.palette, wps, cands, steps, face)
        gradient.apply(self, a, b, blocks, axis=axis, style=style, seed=seed, scale=scale, hollow=hollow, only=only)
        return blocks

    # ---- roofs --------------------------------------------------------------------------------
    def gable_roof(self, a: Pos, b: Pos, stairs: str, *, ridge_axis: str = "x", fill: str | Block | None = None,
                   overhang: int = 1, slab: str | None = None) -> "Build":
        """Stair gable roof over the footprint a..b (y = a[1] is the eave level).

        ridge_axis 'x' → ridge runs east-west, slopes face north and south. `fill` closes the gable
        ends (and the space under the roof is filled only at the end walls). `slab` caps an odd ridge."""
        (x0, x1), (z0, z1) = sorted((a[0], b[0])), sorted((a[2], b[2]))
        y = a[1]
        if ridge_axis == "z":  # work in a rotated frame: swap roles of x and z
            x0, x1, z0, z1 = z0, z1, x0, x1
        x0 -= overhang
        x1 += overhang
        z0 -= overhang
        z1 += overhang
        width = z1 - z0 + 1
        fill_b = self._coerce(fill) if fill else None

        def put(u: int, yy: int, v: int, blk: Block | None) -> None:
            if ridge_axis == "z":
                self.set(v, yy, u, blk)
            else:
                self.set(u, yy, v, blk)

        north, south = ("n", "s") if ridge_axis == "x" else ("w", "e")
        for i in range(width // 2):
            yy = y + i
            for u in range(x0, x1 + 1):
                put(u, yy, z0 + i, self.stairs(stairs, ascend=south))
                put(u, yy, z1 - i, self.stairs(stairs, ascend=north))
            if fill_b:
                for v in range(z0 + i + 1, z1 - i):
                    put(x0 + overhang, yy, v, fill_b)
                    put(x1 - overhang, yy, v, fill_b)
        if width % 2:
            cap = self.slab(slab) if slab else (fill_b or self.block(stairs))
            for u in range(x0, x1 + 1):
                put(u, y + width // 2, z0 + width // 2, cap)
        return self

    # ---- composition --------------------------------------------------------------------------
    def paste(self, other: "Build", offset: Pos = (0, 0, 0), *, rotate: int = 0, mirror: str | None = None,
              skip_air_overwrite: bool = True) -> "Build":
        """Copy `other` in, after optional mirror ('x' flips east-west, 'z' north-south) then rotate
        (quarter turns clockwise seen from above), translated by offset."""
        src = other.transformed(rotate=rotate, mirror=mirror)
        for (x, y, z), b in src.blocks.items():
            self.blocks[(x + offset[0], y + offset[1], z + offset[2])] = b
        return self

    def transformed(self, *, rotate: int = 0, mirror: str | None = None) -> "Build":
        """New build: mirror then rotate about (0,0,0); block orientations are rewritten too
        (see orient.rotate_block / mirror_block for what is understood)."""
        out = Build(self.name, self.palette)
        ax, ay, az = self.anchor
        if mirror == "x":
            ax = -ax
        elif mirror == "z":
            az = -az
        for _ in range(rotate % 4):
            ax, az = -az, ax
        out.anchor = (ax, ay, az)
        turns = rotate % 4
        for (x, y, z), b in self.blocks.items():
            if mirror == "x":
                x = -x
                b = orient.mirror_block(b, "x", self.palette)
            elif mirror == "z":
                z = -z
                b = orient.mirror_block(b, "z", self.palette)
            for _ in range(turns):
                x, z = -z, x
            b = orient.rotate_block(b, turns, self.palette)
            out.blocks[(x, y, z)] = b
        return out

    def translate(self, dx: int, dy: int, dz: int) -> "Build":
        self.blocks = {(x + dx, y + dy, z + dz): b for (x, y, z), b in self.blocks.items()}
        self.anchor = (self.anchor[0] + dx, self.anchor[1] + dy, self.anchor[2] + dz)
        return self

    # ---- reports ------------------------------------------------------------------------------
    def item_of(self, name: str, meta: int) -> tuple[str, int]:
        """The item variant a placed state comes from (oriented stairs/logs collapse to their item)."""
        info = self.palette.info(name, meta)
        return (info.registry, info.meta) if info else (name, meta)

    def bom(self) -> list[tuple[Block, int, str]]:
        """Bill of materials: (item block, count, label), most used first. Orientation metas are merged;
        tile-entity blocks are split by what they are (shape + material, cover; see modblocks.describe)."""
        from .microblocks import NAMES, _decode, is_fmp, parts_of
        from .modblocks import describe

        counts: Counter = Counter()
        for b in self.blocks.values():
            if is_fmp(b):  # count each part, not each cell
                for p in parts_of(b):
                    kind, _, size, mat = _decode(p)
                    counts[(b.name, 0), f"Microblock {NAMES.get((kind, size), f'{kind} {size}/8')} of {mat}"] += 1
                continue
            desc = describe(b, orientation=False)
            counts[self.item_of(b.name, b.meta), desc] += 1
        out = []
        for ((name, meta), desc), n in counts.most_common():
            info = self.palette.info(name, meta)
            label = info.name if info else ("" if desc else name)
            if desc:
                label = f"{label} [{desc}]" if label else desc
            out.append((Block(name, meta), n, label))
        return out

    def check(self) -> list[str]:
        """Problems that would load badly in game: unknown registries, unsupported metas."""
        from .microblocks import FMP_BLOCK, known_materials, parts_of

        issues = []
        seen = set()
        for b in self.design().blocks.values():
            for p in parts_of(b):
                mat = p["material"]
                if mat not in known_materials() and ("mat", mat) not in seen:
                    seen.add(("mat", mat))
                    issues.append(f"microblock material {mat} is not in FMP defaults or microblocks.cfg "
                                  "(only valid if a mod registers it over IMC)")
            key = (b.name, b.meta)
            if key in seen:
                continue
            seen.add(key)
            if b.name != FMP_BLOCK and not self.palette.known(b.name):
                issues.append(f"unknown block {b.name}")
            elif not 0 <= b.meta <= 0xFFFF:
                issues.append(f"{b.name}: meta {b.meta} outside 0..65535")
            elif b.meta > 255 and ("meta>255", b.name) not in seen:
                seen.add(("meta>255", b.name))
                issues.append(f"{b.name}: metas above 255 load only in WorldEdit (Schematica reads one byte)")
        return issues

    # ---- output -------------------------------------------------------------------------------
    def save(self, path=None):
        """Write <name>.schematic to the Threshold Schematica and WorldEdit folders (or to `path`)."""
        from .schematic import save

        return save(self, path)

    def preview(self, prefix: str = "out/preview", *, views=("se", "nw"), scale: int = 16, slices: bool = True,
                html: bool = True, cell: int = 16) -> dict[str, str]:
        """Write <prefix>-iso.png (+ -slices.png, -bom.txt, -layers.txt, .html); returns {kind: path}."""
        from pathlib import Path

        from . import render, viewer

        base = Path(prefix)
        base.parent.mkdir(parents=True, exist_ok=True)
        out = {}
        view = self.design() if self.base is not None else self
        render.iso_sheet(view, scale=scale, views=views).save(f"{base}-iso.png")
        out["iso"] = f"{base}-iso.png"
        if slices:
            render.slices_sheet(view, cell=cell).save(f"{base}-slices.png")
            out["slices"] = f"{base}-slices.png"
        Path(f"{base}-layers.txt").write_text(render.ascii_layers(view))
        out["layers"] = f"{base}-layers.txt"
        Path(f"{base}-bom.txt").write_text(format_bom(self))
        out["bom"] = f"{base}-bom.txt"
        from .lighting import light_sheet, report

        Path(f"{base}-light.txt").write_text(report(self))
        out["light"] = f"{base}-light.txt"
        sheet = light_sheet(self)
        if sheet is not None:
            sheet.save(f"{base}-light.png")
            out["light_png"] = f"{base}-light.png"
        if html:
            out["html"] = str(viewer.write_html(view, f"{base}.html"))
        return out

    def __repr__(self) -> str:
        return f"<Build {self.name!r} {len(self.blocks)} blocks, size {self.size()}>"


def format_bom(build: Build) -> str:
    """Placed blocks, then raw materials: ArchitectureCraft shapes converted through the Sawbench
    (materialUsed per itemsProduced), Carpenter's blocks split into carrier block + cover,
    microblocks converted to block-equivalents of their material (saw/glue recipe chain)."""
    from .microblocks import is_fmp, raw_materials
    from .modblocks import SHAPES, _ac_fields, _cb_cover, is_ac, is_cb

    pal = build.palette
    lines = [f"{build.name}: {len(build)} blocks, size {build.size()} (x*y*z)"]
    if build.base is not None:
        cleared = sum(1 for p in build.changed() if p not in build.blocks)
        build = build.design()
        lines.append(f"carved into terrain: {len(build)} blocks placed or replaced, {cleared} cleared to air")
    lines += ["", "placed:"]
    for blk, n, label in build.bom():
        info = pal.info(blk.name, blk.meta)
        lines.append(f"{n:>7}  {label}  [{info.gtnh_item if info else blk.name}]")
    raw: Counter = Counter()
    shapes: Counter = Counter()
    micro_frac: Counter = Counter()
    for b in build.blocks.values():
        if is_fmp(b):
            for mat, amount in raw_materials(b, pal.known):
                micro_frac[mat] += amount
        elif is_ac(b):
            sid, base, data, _, _ = _ac_fields(b)
            shapes[(sid, base, data)] += 1
        elif is_cb(b):
            raw[(b.name, 0)] += 1
            cover = _cb_cover(b)
            if cover:
                raw[cover] += 1
        else:
            raw[build.item_of(b.name, b.meta)] += 1
    for (sid, base, data), n in shapes.items():
        used, produced = SHAPES.get(sid, ("", "", "", "", 1, 1))[4:6]
        raw[(base, data)] += math.ceil(n / produced) * used
    for mat, amount in micro_frac.items():
        raw[mat] += math.ceil(amount - 1e-9)
    lines += ["", "raw materials (Sawbench, Carpenter's covers and microblocks resolved):"]
    for (name, meta), n in raw.most_common():
        info = pal.info(name, meta)
        lines.append(f"{n:>7}  {info.name if info else name}  [{info.gtnh_item if info else name}]"
                     f"  ({n // 64} stacks + {n % 64})")
    return "\n".join(lines) + "\n"
