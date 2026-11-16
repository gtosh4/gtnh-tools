"""Forge Multipart (ForgeMultipart-1.7.18, GTNH fork) microblocks.

A microblock cell is block `ForgeMultipart:block` with tile entity `savedMultipart` holding a `parts`
list; each microblock part is {id, shape, material} (codechicken.microblock.Microblock.save):
  id        mcr_face (covers/panels/slabs), mcr_hllw (hollow), mcr_cnr (corners), mcr_edge (strips),
            mcr_post (centre posts)
  shape     byte size << 4 | slot-in-class (size in 1/8 block; posts 2/4/6)
  material  registry name + "_<meta>" when meta > 0 (BlockMicroMaterial.materialKey)

Bounds below reproduce FaceMicroClass / HollowMicroClass / CornerMicroClass / EdgeMicroClass /
PostMicroClass with CodeChickenLib's Rotation.sideRotations and AxisCycle.cycles matrices.
Valid materials: DefaultContent + config/microblocks.cfg; mods may add more over IMC (not listed).
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from . import nbt

if TYPE_CHECKING:
    from .build import Block
    from .geometry import Face
    from .palette import Palette

FMP_BLOCK = "ForgeMultipart:block"
FMP_TE = "savedMultipart"
MICROBLOCKS_CFG = Path(os.environ.get(
    "GTNH_MICROBLOCKS_CFG",
    "/var/mnt/mercury/Minecraft/Instances/GTNH Threshold/.minecraft/config/microblocks.cfg"))

Box = tuple[float, float, float, float, float, float]
Mat3 = tuple[tuple[int, int, int], ...]

# CodeChickenLib Rotation.sideRotations[s]: maps the bottom face onto side s (row-major 3x3).
_SIDE_ROT: tuple[Mat3, ...] = (
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((1, 0, 0), (0, -1, 0), (0, 0, -1)),
    ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    ((1, 0, 0), (0, 0, 1), (0, -1, 0)),
    ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
)
# AxisCycle.cycles
_CYCLE: tuple[Mat3, ...] = (
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
)


def _xf(box: Box, m: Mat3, scale=(1, 1, 1)) -> Box:
    """Scale then rotate a box about the block centre (CCL `.at(center)`)."""
    pts = []
    for x in (box[0], box[3]):
        for y in (box[1], box[4]):
            for z in (box[2], box[5]):
                p = ((x - .5) * scale[0], (y - .5) * scale[1], (z - .5) * scale[2])
                pts.append(tuple(sum(m[i][k] * p[k] for k in range(3)) + .5 for i in range(3)))
    xs, ys, zs = zip(*pts)
    return tuple(round(v, 6) for v in (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))


@lru_cache(maxsize=None)
def part_boxes(kind: str, slot: int, size: int) -> tuple[Box, ...]:
    """Collision boxes of one part. slot = low nibble of `shape`."""
    d = size / 8
    if kind == "mcr_face":
        return (_xf((0, 0, 0, 1, d, 1), _SIDE_ROT[slot]),)
    if kind == "mcr_hllw":  # default hollow size 8/16: a 1/2 x 1/2 hole (HollowMicroblock.getHollowSize)
        h1, h2 = .25, .75
        return tuple(_xf(b, _SIDE_ROT[slot]) for b in
                     ((0, 0, 0, 1, d, h1), (0, 0, h2, 1, d, 1), (0, 0, h1, h1, d, h2), (h2, 0, h1, 1, d, h2)))
    if kind == "mcr_cnr":
        scale = (-1 if slot & 4 else 1, -1 if slot & 1 else 1, -1 if slot & 2 else 1)
        return (_xf((0, 0, 0, d, d, d), _SIDE_ROT[0], scale),)
    if kind == "mcr_edge":
        scale = (-1 if slot & 2 else 1, 1, -1 if slot & 1 else 1)
        return (_xf((0, 0, 0, d, 1, d), _CYCLE[slot >> 2], scale),)
    if kind == "mcr_post":
        a, b = .5 - size / 16, .5 + size / 16
        return (_xf((a, 0, a, b, 1, b), _SIDE_ROT[slot << 1]),)
    raise ValueError(f"unknown microblock part {kind!r}")


_SLOTS = {"mcr_face": range(6), "mcr_hllw": range(6), "mcr_cnr": range(8), "mcr_edge": range(12), "mcr_post": range(3)}
# PartMap slot numbers (faces/hollows 0-5, corners 7-14, edges 15-26) for the one-part-per-slot rule
_SLOT_BASE = {"mcr_face": 0, "mcr_hllw": 0, "mcr_cnr": 7, "mcr_edge": 15}
NAMES = {("mcr_face", 1): "Cover", ("mcr_face", 2): "Panel", ("mcr_face", 4): "Slab",
         ("mcr_hllw", 1): "Hollow Cover", ("mcr_hllw", 2): "Hollow Panel", ("mcr_hllw", 4): "Hollow Slab",
         ("mcr_cnr", 1): "Nook", ("mcr_cnr", 2): "Corner", ("mcr_cnr", 4): "Notch",
         ("mcr_edge", 1): "Strip", ("mcr_edge", 2): "Post", ("mcr_edge", 4): "Pillar",
         ("mcr_post", 2): "Centre Post", ("mcr_post", 4): "Centre Post", ("mcr_post", 6): "Centre Post"}
# block-equivalents per part (MicroRecipe: 2 edges glue to a face, 4 corners to a face, 8 faces -> 8 hollows)
_COST = {"mcr_face": 1 / 8, "mcr_hllw": 1 / 8, "mcr_edge": 1 / 16, "mcr_cnr": 1 / 32, "mcr_post": 1 / 16}


def _touching(box: Box) -> set[str]:
    out = set()
    if box[0] == 0: out.add("w")
    if box[3] == 1: out.add("e")
    if box[1] == 0: out.add("d")
    if box[4] == 1: out.add("u")
    if box[2] == 0: out.add("n")
    if box[5] == 1: out.add("s")
    return out


_LETTER = {"n": "n", "north": "n", "s": "s", "south": "s", "e": "e", "east": "e", "w": "w", "west": "w",
           "u": "u", "up": "u", "d": "d", "down": "d"}


def _letters(spec: str) -> set[str]:
    parts = re.findall(r"north|south|east|west|up|down|[nsewud]", spec.lower())
    return {_LETTER[p] for p in parts}


def material_key(block: "Block") -> str:
    return block.name + (f"_{block.meta}" if block.meta > 0 else "")


def parse_material(key: str, known: Callable[[str], bool]) -> tuple[str, int]:
    m = re.fullmatch(r"(.+)_(\d+)", key)
    if m and known(m.group(1)):
        return m.group(1), int(m.group(2))
    return key, 0


_DEFAULT = ("stone", "dirt:0-2", "cobblestone", "planks:0-5", "log:0-3", "log2:0-1", "leaves:0-3", "leaves2:0-1",
            "sponge", "glass", "lapis_block", "sandstone:0-2", "wool:0-15", "gold_block", "iron_block", "brick_block",
            "bookshelf", "mossy_cobblestone", "obsidian", "diamond_block", "ice", "snow", "clay", "netherrack",
            "soul_sand", "glowstone", "stonebrick:0-3", "nether_brick", "end_stone", "emerald_block",
            "redstone_block", "quartz_block", "stained_hardened_clay:0-15", "hardened_clay", "coal_block",
            "packed_ice", "stained_glass:0-15", "grass", "mycelium")


def _expand(name: str, metas: str | None) -> set[str]:
    out = set()
    for part in (metas or "0").split(","):
        lo, _, hi = part.partition("-")
        for m in range(int(lo), int(hi or lo) + 1):
            out.add(name + (f"_{m}" if m > 0 else ""))
    return out


# Materials registered by other mods at init (found by scanning the Threshold mod jars for
# MicroMaterialRegistry / "microMaterial" IMC):
# - chisel CarvableHelper.registerAll -> FMPIMC.registerFMP for every carvable variation (incl. antiBlock)
# - ExtraUtilities FMPRegisterPassThroughInterfaces: greenscreen (Lapis Caelestis, full-bright),
#   decorativeBlock1/2, cobblestone_compressed, colour blocks, ethereal glass, trading post, thermic pump
# - ProjectRed Illumination LightMicroMaterial: inverted lamps, lamp metas 16..31 only
# Other mods (BoP, Botania, Blood Arsenal, Natura, TConstruct, AE2, Railcraft, Galacticraft, ...) also
# register some blocks that this list does not enumerate.
_IMC_PREFIXES = ("chisel:",)
_IMC_REGISTRIES = {"ExtraUtilities:greenscreen", "ExtraUtilities:decorativeBlock1", "ExtraUtilities:decorativeBlock2",
                   "ExtraUtilities:cobblestone_compressed", "ExtraUtilities:colorStoneBrick",
                   "ExtraUtilities:colorWoodPlanks", "ExtraUtilities:etherealglass", "ExtraUtilities:trading_post",
                   "ExtraUtilities:enderThermicPump"}
PR_LAMP = "ProjRed|Illumination:projectred.illumination.lamp"


@lru_cache(maxsize=1)
def known_materials() -> frozenset[str]:
    """Material keys from FMP DefaultContent, the instance's microblocks.cfg, and the IMC registrations above."""
    from .palette import default

    keys: set[str] = set()
    for entry in _DEFAULT:
        name, _, metas = entry.partition(":")
        keys |= _expand(f"minecraft:{name}", metas or None)
    if MICROBLOCKS_CFG.exists():
        for line in MICROBLOCKS_CFG.read_text().splitlines():
            m = re.match(r'\s*"([^"]+)"(?::([\d,\-]+))?', line)
            if m:
                name = m.group(1) if (":" in m.group(1) or "." in m.group(1)) else f"minecraft:{m.group(1)}"
                keys |= _expand(name, m.group(2))
    for reg, meta in default().db.execute("SELECT registry_name, meta FROM block"):
        if reg.startswith(_IMC_PREFIXES) or reg in _IMC_REGISTRIES or reg.startswith("ExtraUtilities:color_"):
            keys.add(reg + (f"_{meta}" if meta > 0 else ""))
    keys |= _expand(PR_LAMP, "16-31")
    return frozenset(keys)


def material_light(key: str, palette: "Palette") -> int:
    """Light a microblock of this material emits (FMP: material block's light; a cell emits its brightest part)."""
    from .lighting import block_light

    reg, meta = parse_material(key, palette.known)
    if reg == PR_LAMP:
        return 15 if meta >= 16 else 0  # LightMicroMaterial: inverted lamps, always lit
    return block_light(reg, meta, palette)


def part(kind: str, material: "Block", where: str = "", size: int = 1) -> dict:
    """One microblock part.

    kind: 'face' (cover 1 / panel 2 / slab 4), 'hollow', 'corner' (nook 1 / corner 2 / notch 4),
          'edge' (strip 1 / post 2 / pillar 4), 'post' (centre post, size 2/4/6, `where` = axis x/y/z).
    where: face/hollow -> the side it lies against ('down', 'n', ...); corner -> three sides ('dnw');
           edge -> the two sides it runs between ('dn' = bottom-north edge, runs east-west)."""
    kind_id = {"face": "mcr_face", "cover": "mcr_face", "hollow": "mcr_hllw", "corner": "mcr_cnr",
               "edge": "mcr_edge", "strip": "mcr_edge", "post": "mcr_post"}[kind]
    if kind_id == "mcr_post":
        if size not in (2, 4, 6):
            raise ValueError("centre post size must be 2, 4 or 6")
        slot = {"y": 0, "z": 1, "x": 2}[where or "y"]
    else:
        if not 1 <= size <= 7:
            raise ValueError("microblock size is 1..7 eighths (items come as 1, 2, 4)")
        want = _letters(where)
        slots = [s for s in _SLOTS[kind_id] if _sides(kind_id, s) == want]
        if len(slots) != 1:
            raise ValueError(f"{kind} at {where!r}: give "
                             + {"mcr_face": "one side", "mcr_hllw": "one side", "mcr_cnr": "three sides on different axes",
                                "mcr_edge": "two sides on different axes"}[kind_id])
        slot = slots[0]
    return {"id": kind_id, "shape": nbt.Byte(size << 4 | slot), "material": material_key(material)}


def _sides(kind_id: str, slot: int) -> set[str] | str:
    """The block sides a part hugs: face/hollow 1, edge 2, corner 3; posts report their axis."""
    if kind_id == "mcr_post":
        return "yzx"[slot]
    box = part_boxes("mcr_face" if kind_id == "mcr_hllw" else kind_id, slot, 1)[0]
    t = _touching(box)
    for axis, letters in enumerate(("we", "du", "ns")):  # axes the part spans fully are not "sides"
        if box[axis + 3] - box[axis] >= 1:
            t -= set(letters)
    return t


def _decode(p: dict) -> tuple[str, int, int, str]:
    shape = p["shape"].v & 0xFF
    return p["id"], shape & 0xF, shape >> 4, p["material"]


def is_fmp(b: "Block") -> bool:
    return b.te is not None and b.te.get("id") == FMP_TE


def micro(parts: list[dict]) -> "Block":
    """A ForgeMultipart cell holding `parts`; at most one part per face/corner/edge slot."""
    from .build import Block

    seen: set[int] = set()
    for p in parts:
        kind, slot, _, _ = _decode(p)
        if kind in _SLOT_BASE:
            key = _SLOT_BASE[kind] + slot
            if key in seen:
                raise ValueError(f"two microblocks in one slot ({kind} {''.join(sorted(_sides(kind, slot)))})")
            seen.add(key)
    return Block(FMP_BLOCK, 0, {"id": FMP_TE, "parts": nbt.List(nbt.COMPOUND, list(parts))})


def parts_of(b: "Block") -> list[dict]:
    return list(b.te.get("parts", nbt.List(nbt.COMPOUND)).items) if is_fmp(b) else []


def describe(b: "Block", orientation: bool = True) -> str:
    labels = []
    for p in parts_of(b):
        kind, slot, size, mat = _decode(p)
        name = NAMES.get((kind, size), f"{kind} {size}/8")
        if orientation:
            sides = _sides(kind, slot)
            name += "@" + (f"axis {sides}" if isinstance(sides, str) else "".join(sorted(sides)))
        labels.append(f"{name} of {mat}")
    return "Microblocks: " + " + ".join(labels)


def raw_materials(b: "Block", known: Callable[[str], bool]) -> list[tuple[tuple[str, int], float]]:
    """(material block, block-equivalents) per part, following the saw/glue recipes."""
    out = []
    for p in parts_of(b):
        kind, _, size, mat = _decode(p)
        out.append((parse_material(mat, known), _COST[kind] * size))
    return out


def transform(b: "Block", f: Callable[[tuple[int, int, int]], tuple[int, int, int]]) -> "Block":
    from .build import Block

    cols = [f(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    m = tuple(tuple(cols[j][i] for j in range(3)) for i in range(3))
    out = []
    for p in parts_of(b):
        kind, slot, size, mat = _decode(p)
        ref = "mcr_face" if kind == "mcr_hllw" else kind  # a hollow's slot follows its outer plate
        target = _xf(part_boxes(ref, slot, size)[0], m)
        new = next((s for s in _SLOTS[kind] if part_boxes(ref, s, size)[0] == target), slot)
        q = dict(p)
        q["shape"] = nbt.Byte(size << 4 | new)
        out.append(q)
    te = dict(b.te)
    te["parts"] = nbt.List(nbt.COMPOUND, out)
    return Block(b.name, b.meta, te)


def geometry(b: "Block", palette: "Palette") -> list["Face"]:
    from .geometry import box, with_material_look

    faces = []
    for p in parts_of(b):
        kind, slot, size, mat = _decode(p)
        reg, meta = parse_material(mat, palette.known)
        tex = palette.face_textures(reg, meta)
        part_faces = []
        for bx in part_boxes(kind, slot, size):
            part_faces += box(*bx, tex)
        faces += with_material_look(part_faces, reg, meta)
    return faces
