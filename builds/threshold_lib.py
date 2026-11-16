"""Shared by the Threshold base stages: palette V1 "Observatory Verdigris" and the carving helpers
(rooms lined where they meet rock, grate-covered cable trenches, knock-out panels, lamp posts, exposed
ore cleanup). Stage scripts import it after putting builds/ on sys.path."""
from __future__ import annotations

import zlib
from collections import Counter
from dataclasses import dataclass

from gtnhbuild import Build, nbt
from gtnhbuild.build import Block

_v = Build("palette")
WALL = _v.block("gregtech:gt.blockstones:3")      # marble bricks
SMOOTH = _v.block("gregtech:gt.blockstones:7")    # smooth marble
CHIS = _v.block("gregtech:gt.blockstones:6")      # chiseled marble
GRAN = _v.block("gregtech:gt.blockgranites:7")    # smooth black granite
GRANB = _v.block("gregtech:gt.blockgranites:3")   # black granite bricks
COPPER = _v.block("etfuturum:copper_block:15")    # waxed oxidized cut copper
GRATE = _v.block("etfuturum:copper_grate:7")      # waxed oxidized copper grate
GLASS = _v.block("minecraft:glass")
LAMP = _v.block("chisel:froglight:0")
CHAIN = _v.block("etfuturum:chain")
STONE = _v.block("minecraft:stone")
WATER = _v.block("minecraft:water")
LEAVES = (_v.block("minecraft:leaves:4"), _v.block("minecraft:leaves:6"))   # oak / birch, no decay
GRASS = _v.block("minecraft:grass")
PLANTS = [_v.block(s) for s in ("minecraft:tallgrass:2", "minecraft:red_flower:1", "minecraft:tallgrass:2",
                                "minecraft:red_flower:3", "minecraft:yellow_flower", "minecraft:red_flower:8")]
DIRS = {"n": (0, -1), "s": (0, 1), "w": (-1, 0), "e": (1, 0)}
OPPOSITE = {"n": "s", "s": "n", "w": "e", "e": "w"}
VINE_META = {"s": 1, "w": 2, "n": 4, "e": 8}   # vine meta bit = side its supporting wall is on
SOFT = ("leaves", "log", "tallgrass", "flower", "vine", "sapling", "snow_layer", "double_plant",
        "foliage", "Foliage", "reeds", "water", "deadbush", "mushroom")
NEIGHBOURS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
Pos = tuple[int, int, int]


def h(*k) -> int:
    """Deterministic scatter in 0..9999 (stable lengths for hanging leaves and vines)."""
    return zlib.crc32(repr(k).encode()) % 10000


def box(lo: Pos, hi: Pos):
    for x in range(lo[0], hi[0] + 1):
        for y in range(lo[1], hi[1] + 1):
            for z in range(lo[2], hi[2] + 1):
                yield x, y, z


def checker(x: int, z: int) -> Block:
    return GRAN if (x + z) % 2 == 0 else SMOOTH


def solid_top(world, x: int, z: int) -> int:
    """Highest block of the live world column that isn't foliage, plants or water."""
    return world.height(x, z, solid=lambda blk: not any(s in blk.name for s in SOFT))


@dataclass
class Space:
    """A carved room. `kind`: "room" (checker floor, marble walls with black-granite pilasters every 4,
    skirting and cornice) or "service" (granite-brick floor, plain marble walls). `ceiling`: lamp grid
    every 4 blocks, "pendant" (chain + lamp 4 above `floor`) or "flush", or None. `sconces`: floor
    levels whose +3 row puts a lamp in each pilaster."""
    boxes: list[tuple[Pos, Pos]]
    kind: str = "room"
    ceiling: str | None = None
    floor: int | None = None
    sconces: tuple[int, ...] = ()
    ceiling_block: Block = SMOOTH


def carve(b: Build, spaces: dict[str, Space], doors: list[tuple[str, list[Pos]]] = ()) -> tuple[set, dict]:
    """Clear every space's interior and line each face that isn't open to another space. Earlier spaces
    win overlapping cells; `doors` (space name, cells) are carved last and belong to that space.
    Returns (interior cells, cell -> space name)."""
    zone: dict[Pos, str] = {}
    for name, sp in spaces.items():
        for lo, hi in sp.boxes:
            for p in box(lo, hi):
                zone.setdefault(p, name)
    for name, cells in doors:
        for p in cells:
            zone[p] = name
    interior = set(zone)
    shell: dict = {}
    for (x, y, z), zn in zone.items():
        for d, q in (("floor", (x, y - 1, z)), ("ceil", (x, y + 1, z)), ("n", (x, y, z - 1)), ("s", (x, y, z + 1)),
                     ("w", (x - 1, y, z)), ("e", (x + 1, y, z))):
            if q not in interior and b.inside(q):   # beyond the box belongs to another stage
                rank = {"floor": 0, "ceil": 1}.get(d, 2)
                if q not in shell or rank < shell[q][2]:
                    shell[q] = (zn, d, rank, (x, y, z))
    for p in interior:
        b.blocks.pop(p, None)
    pendants = []
    for (x, y, z), (zn, d, _, (ix, iy, iz)) in shell.items():
        sp = spaces[zn]
        if d == "floor":
            blk = GRANB if sp.kind == "service" else checker(x, z)
        elif d == "ceil":
            lamp = sp.ceiling is not None and x % 4 == 2 and z % 4 == 3
            if lamp and sp.ceiling == "pendant":
                pendants.append((x, y, z, sp.floor))
            blk = LAMP if lamp and sp.ceiling == "flush" else sp.ceiling_block
        else:
            along = z if d in ("w", "e") else x
            if sp.kind == "service":
                blk = WALL
            elif along % 4 == 0:
                blk = LAMP if (iy - 3) in sp.sconces else GRANB
            elif (ix, iy + 1, iz) not in interior:
                blk = CHIS
            elif (ix, iy - 1, iz) not in interior:
                blk = GRANB
            else:
                blk = WALL
        b.blocks[(x, y, z)] = blk
    for x, y, z, floor in pendants:
        for cy in range(y - 1, floor + 4, -1):
            b.set(x, cy, z, CHAIN)
        b.set(x, floor + 4, z, LAMP)
    return interior, zone


def trench(b: Build, cells, y: int) -> None:
    """Copper-grate covered cable channel: grate at y, open channel at y-1, granite under it."""
    cells = set(cells)
    for x, z in cells:
        b.set(x, y, z, GRATE)
        b.set(x, y - 1, z, None)
        b.set(x, y - 2, z, GRANB)
    for x, z in cells:                # close the channel sides where they hit air or a void; leave junctions
        for dx, dz in DIRS.values():  # with an existing trench and cells outside the box (another stage's
            q = (x + dx, z + dz)      # trench may continue there) open
            if q not in cells and b.inside((q[0], y - 1, q[1])) and b.get(q[0], y - 1, q[1]) is None \
                    and b.get(q[0], y, q[1]) != GRATE:
                b.set(q[0], y - 1, q[1], GRANB)


def knockout(b: Build, face: str, a: int, b_: int, y0: int, y1: int, plane: int) -> None:
    """Framed panel marking a future doorway: copper frame, granite-brick infill."""
    for u in range(a - 1, b_ + 2):
        for y in range(y0, y1 + 2):
            edge = u in (a - 1, b_ + 1) or y == y1 + 1
            pos = (u, y, plane) if face in "ns" else (plane, y, u)
            b.set(*pos, COPPER if edge else GRANB)


def doorway(b: Build, face: str, a: int, b_: int, y0: int, y1: int, planes: tuple[int, ...]) -> None:
    """Open a doorway a..b_ x y0..y1 through wall planes (z planes for face n/s, x for e/w) with a
    copper frame on the first plane. Floor cells under the opening still holding raw terrain become a
    granite-brick threshold (designed floor there, e.g. a trench grate, stays)."""
    for plane in planes:
        for u in range(a, b_ + 1):
            for y in range(y0, y1 + 1):
                b.set(*((u, y, plane) if face in "ns" else (plane, y, u)), None)
            sill = (u, y0 - 1, plane) if face in "ns" else (plane, y0 - 1, u)
            if b.base is None or b.blocks.get(sill) == b.base.get(sill):
                b.set(*sill, GRANB)
    plane = planes[0]
    for y in range(y0, y1 + 2):
        for u in (a - 1, b_ + 1):
            b.set(*((u, y, plane) if face in "ns" else (plane, y, u)), COPPER)
    for u in range(a - 1, b_ + 2):
        b.set(*((u, y1 + 1, plane) if face in "ns" else (plane, y1 + 1, u)), COPPER)


def lamp_post(b: Build, x: int, y: int, z: int, height: int = 2) -> None:
    """Granite-brick post standing on the floor block at y, froglight on top."""
    for k in range(1, height + 1):
        b.set(x, y + k, z, GRANB)
    b.set(x, y + height + 1, z, LAMP)


def hanging_vine(b: Build, x: int, z: int, top: int, bottom: int, side: str) -> None:
    """Vines on the wall toward `side`, from y=top down to y=bottom, capped underneath by a glow-lichen
    tuft on the same wall. Vines grow down into any air below them until they reach the floor; the
    tuft fills that cell, and lichen itself only spreads with bone meal. Cells already holding
    something are skipped."""
    vine = Block("minecraft:vine", VINE_META[side])
    for y in range(top, bottom - 1, -1):
        if b.get(x, y, z) is None:
            b.set(x, y, z, vine)
    if b.get(x, bottom - 1, z) is None:              # EtFuturum glow lichen: State = side bitmap,
        d = FORGE_DIR[side]                         # bit = ForgeDirection toward the support
        b.set(x, bottom - 1, z, Block("etfuturum:glow_lichen", d, {"id": "etfuturum.glow_lichen",
                                                                    "State": nbt.Int(1 << d)}))


def is_ore(blk) -> bool:
    return blk is not None and ("blockores" in blk.name or blk.name.endswith("_ore"))


def clean_ores(b: Build) -> None:
    """Ores left showing on any carved or outdoor face become the rock around them."""
    def see_through(blk) -> bool:
        if blk is None:
            return True
        info = b.palette.info(blk.name, blk.meta)
        return info is None or not info.opaque

    for (x, y, z), blk in list(b.blocks.items()):
        if not is_ore(blk):
            continue
        near = [((x + dx, y + dy, z + dz), b.get(x + dx, y + dy, z + dz)) for dx, dy, dz in NEIGHBOURS]
        if not any(see_through(n) for _, n in near):
            continue
        hosts = [n for p, n in near if n is not None and n.te is None and not is_ore(n) and not see_through(n)
                 and b.base.get(p) == n]            # natural rock around it, not the build's own blocks
        b.set(x, y, z, Counter(hosts).most_common(1)[0][0] if hosts else STONE)


# ---- labels -------------------------------------------------------------------------------------------
FORGE_DIR = {"n": 2, "s": 3, "w": 4, "e": 5}
NC_BLOCK = "IC2NuclearControl:blockNuclearControlMain"
NC_CORE, NC_EXTENDER = 9, 10                        # Advanced Information Panel / Advanced Panel Extender
NC_POWER_ON = 2                                     # TileEntityAdvancedInfoPanel.POWER_ON (always shown)
# Nuclear Control colour index = dye damage order, 0..14 only: there is no white (TileEntityInfoPanel.COLORS_HEX
# has 15 entries; text colour 15 crashes the client renderer). light_gray (0xcbcbcb) is the lightest.
DYE = {"black": 0, "red": 1, "green": 2, "brown": 3, "blue": 4, "purple": 5, "cyan": 6, "light_gray": 7,
       "gray": 8, "pink": 9, "lime": 10, "yellow": 11, "light_blue": 12, "magenta": 13, "orange": 14}


def info_panel(b: Build, a: Pos, c: Pos, mount: str, *lines: str, text: str = "light_gray", background: str = "green",
               transparent: bool = True, thickness: int = 2) -> None:
    """Nuclear Control Advanced Information Panel over the flat rectangle a..c (one horizontal axis
    constant), fixed to the wall that lies toward `mount`; the screen faces away from it. Defaults
    give the low-profile overlay (2/16 thick, transparent background) that sits in the open cells in
    front of a lintel or frame so the decoration shows through. One Text Card holds `lines` (up to
    10); the core is the middle cell, the rest extenders; always powered."""
    cells = sorted(box(tuple(min(a[i], c[i]) for i in range(3)), tuple(max(a[i], c[i]) for i in range(3))))
    plane_axis = 0 if a[0] == c[0] else 2 if a[2] == c[2] else None
    if plane_axis is None or FORGE_DIR[mount] // 2 != (2 if plane_axis == 0 else 1):
        raise ValueError(f"panel {a}..{c} must lie flat against the wall toward {mount!r}")
    core = cells[len(cells) // 2]
    lo = tuple(min(p[i] for p in cells) for i in range(3))
    hi = tuple(max(p[i] for p in cells) for i in range(3))
    face = nbt.Short(FORGE_DIR[mount])               # NBT "facing" = the side the panel is fixed to
    card_tag = {"state": nbt.Int(1), "title": ""}
    for i in range(10):
        card_tag[f"line_{i}"] = lines[i] if i < len(lines) else ""
    empty = lambda: nbt.List(nbt.END, [])  # noqa: E731
    core_te = {
        "id": "IC2NCAdvancedInfoPanel", "facing": face, "rotation": nbt.Int(0),
        "rotateHor": nbt.Byte(0), "rotateVert": nbt.Byte(0), "textRotation": nbt.Byte(0),
        "thickness": nbt.Byte(thickness), "powerMode": nbt.Byte(NC_POWER_ON), "showLabels": nbt.Byte(1),
        "colorText": nbt.Int(DYE[text]), "colorBackground": nbt.Int(DYE[background]),
        "transparencyMode": nbt.Byte(1 if transparent else 0),
        "dSettings1": empty(), "dSettings2": empty(), "dSettings3": empty(),
        "dataSorters": {"0": empty(), "1": empty(), "2": empty()},
        "screenData": {"minX": nbt.Int(lo[0]), "minY": nbt.Int(lo[1]), "minZ": nbt.Int(lo[2]),
                       "maxX": nbt.Int(hi[0]), "maxY": nbt.Int(hi[1]), "maxZ": nbt.Int(hi[2])},
        "Items": nbt.List(nbt.COMPOUND, [{
            "Slot": nbt.Byte(0), "id": nbt.Short(b.item_id("IC2NuclearControl:ItemTextCard")),
            "Count": nbt.Byte(1), "Damage": nbt.Short(0), "tag": card_tag}]),
    }
    for p in cells:
        if p == core:
            b.blocks[p] = Block(NC_BLOCK, NC_CORE, core_te)
        else:
            b.blocks[p] = Block(NC_BLOCK, NC_EXTENDER, {
                "id": "IC2NCAdvancedInfoPanelExtender", "facing": face, "partOfScreen": nbt.Byte(1),
                "coreX": nbt.Int(core[0]), "coreY": nbt.Int(core[1]), "coreZ": nbt.Int(core[2])})


def aisle_lights(b: Build, lo: Pos, hi: Pos, y: int, reserved: set, *, spacing: int = 4, reach: int = 5,
                 clearance: int = 0) -> list:
    """Froglights set into the floor (layer y) of the room lo..hi, only in open aisles: never in
    `reserved` (the (x, z) cells kept for machines, trenches, planters) nor within `clearance` of it.
    Lamps go on a regular `spacing` grid, at the grid offset that lights the most floor, then single
    lamps fill any aisle still more than `reach` steps from one (light at walking height = 14 - steps).
    Returns the lamp cells."""
    free = {(x, z) for x in range(lo[0], hi[0] + 1) for z in range(lo[2], hi[2] + 1) if (x, z) not in reserved}
    ok = [p for p in sorted(free) if all((p[0] + dx, p[1] + dz) in free
                                         for dx in range(-clearance, clearance + 1)
                                         for dz in range(-clearance, clearance + 1))]
    reach_of = {p: {q for q in free if abs(q[0] - p[0]) + abs(q[1] - p[1]) <= reach} for p in ok}

    def grid(ox: int, oz: int) -> list:
        return [p for p in ok if (p[0] - ox) % spacing == 0 and (p[1] - oz) % spacing == 0]

    def lit(lamps) -> int:
        return len(set().union(*(reach_of[p] for p in lamps))) if lamps else 0

    best = max(((ox, oz) for ox in range(spacing) for oz in range(spacing)),
               key=lambda o: (lit(grid(*o)), -len(grid(*o)), -o[0], -o[1]))
    lamps = grid(*best)
    reachable = set().union(*reach_of.values()) if reach_of else set()
    uncovered = reachable - set().union(*(reach_of[p] for p in lamps)) if lamps else set(reachable)
    while uncovered:
        extra = max(ok, key=lambda p: (len(reach_of[p] & uncovered), -p[0], -p[1]))
        lamps.append(extra)
        uncovered -= reach_of[extra]
    for x, z in lamps:
        b.set(x, y, z, LAMP)
    return lamps


SIGN_ROT = {"s": 0, "w": 4, "n": 8, "e": 12}        # standing sign rotation: side the text faces


def sign(b: Build, x: int, y: int, z: int, facing: str, *lines: str) -> None:
    """Standing sign at (x, y, z), text toward `facing`, up to 4 lines of 15 characters."""
    te = {"id": "Sign"}
    for i in range(4):
        te[f"Text{i + 1}"] = (lines[i] if i < len(lines) else "")[:15]
    b.blocks[(x, y, z)] = Block("minecraft:standing_sign", SIGN_ROT[facing], te)


# ---- machine pads ---------------------------------------------------------------------------------------
# A pad is a machine footprint in smooth black granite with a copper line along its front (the aisle
# side). Neighbouring pads touch and back rows sit against the walls, so multiblocks can be built side
# by side. Both helpers add what they cover to `reserved` (for aisle_lights).
def pad(b: Build, reserved: set, x0: int, z0: int, w: int, d: int, front: str, y: int) -> None:
    cells = {(x, z) for x in range(x0, x0 + w) for z in range(z0, z0 + d)}
    dx, dz = DIRS[front]
    line = {(x + dx, z + dz) for x, z in cells} - cells
    for x, z in cells:
        b.set(x, y, z, GRAN)
    for x, z in line:
        b.set(x, y, z, COPPER)
    reserved |= cells | line


def trench_run(b: Build, reserved: set, cells, y: int, work: str | None = None) -> None:
    """Trench row; `work` reserves the cells beside it on that side (machines stand on the grate)."""
    cells = list(cells)
    trench(b, cells, y)
    reserved |= set(cells)
    if work:
        dx, dz = DIRS[work]
        reserved |= {(x + dx, z + dz) for x, z in cells}


# ---- stages -----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Stage:
    """One schematic of the base. `marker`: a cell only this stage changes, holding `marker_block` once
    the stage is in the world (needed when a later stage's box overlaps this one)."""
    script: str
    box: tuple[Pos, Pos]
    marker: Pos | None = None
    marker_block: Block | None = None


STAGES = {
    "gate_atrium": Stage("threshold_gate_atrium.py", ((-605, 66, -288), (-468, 165, -205)), (-593, 90, -269), WALL),
    "industry": Stage("threshold_industry.py", ((-626, 77, -307), (-545, 109, -268)), (-622, 100, -284), GRATE),
    "works": Stage("threshold_works.py", ((-597, 95, -324), (-549, 116, -301))),
    "core": Stage("threshold_core.py", ((-624, 109, -300), (-563, 128, -268))),
    "gardens": Stage("threshold_gardens.py", ((-607, 93, -254), (-579, 111, -224))),
    "crop_link": Stage("threshold_crop_link.py", ((-585, 93, -266), (-583, 99, -255))),
}


def lay_stages(b: Build, world, box_: tuple[Pos, Pos], names) -> None:
    """Carry earlier stages in this build's overlap with their boxes: every named stage whose marker
    isn't in the live world yet is run and its result laid into the overlap, so pasting this stage
    never reverts it. The result becomes `b.base` (the world as those stages leave it)."""
    import runpy
    from pathlib import Path

    laid = False
    for name in names:
        st = STAGES[name]
        lo = tuple(max(box_[0][i], st.box[0][i]) for i in range(3))
        hi = tuple(min(box_[1][i], st.box[1][i]) for i in range(3))
        if any(lo[i] > hi[i] for i in range(3)):
            continue
        m = world.get(*st.marker)
        if m is not None and (m.name, m.meta) == (st.marker_block.name, st.marker_block.meta):
            continue
        earlier = runpy.run_path(str(Path(__file__).with_name(st.script)), run_name="__gtnhbuild__")["build"]
        for p in box(lo, hi):
            blk = earlier.blocks.get(p)
            if blk is None:
                b.blocks.pop(p, None)
            else:
                b.blocks[p] = blk
        laid = True
    if laid:
        b.base = dict(b.blocks)
