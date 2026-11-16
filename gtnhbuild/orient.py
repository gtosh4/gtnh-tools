"""Block orientation: meta helpers, and rotate/mirror of metadata as direction vectors.

Every orientable meta scheme is a table {orientation bits -> direction vector}; rotating or mirroring a
block transforms its vector and picks the table entry pointing the same way (as WorldEdit does).
Sources: WorldEdit-GTNH BlockData.rotate90 / RotationUtils, and the per-mod rotation mappings WorldEdit
generates in config/worldedit/mappings/*.json (copied to gtnhbuild/data/we-mappings/).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .build import Block
    from .palette import Palette

Vec = tuple[int, int, int]
N, E, S, W, U, D = (0, 0, -1), (1, 0, 0), (0, 0, 1), (-1, 0, 0), (0, 1, 0), (0, -1, 0)
DIRS = {"n": N, "north": N, "e": E, "east": E, "s": S, "south": S, "w": W, "west": W, "u": U, "up": U,
        "d": D, "down": D}
DIR_NAMES = {N: "north", E: "east", S: "south", W: "west", U: "up", D: "down"}
FORGE_DIRS = (D, U, N, S, W, E)  # ForgeDirection ordinals 0..5


def vec(direction: str | Vec) -> Vec:
    if isinstance(direction, tuple):
        return direction
    try:
        return DIRS[direction.lower()]
    except KeyError:
        raise ValueError(f"direction {direction!r}: use n/e/s/w/u/d") from None


# ---- constructors ------------------------------------------------------------------------------
_STAIRS = {E: 0, W: 1, S: 2, N: 3}


def stairs_meta(ascend: str | Vec, upside_down: bool = False) -> int:
    """Vanilla stairs: meta&3 names the side holding the tall half (the direction you walk up)."""
    v = vec(ascend)
    if v not in _STAIRS:
        raise ValueError("stairs ascend must be horizontal")
    return _STAIRS[v] | (4 if upside_down else 0)


def pillar_meta(meta: int, axis: str) -> int:
    return (meta & 3) | {"y": 0, "x": 4, "z": 8}[axis]


_FACING_2_5 = {N: 2, S: 3, W: 4, E: 5}
_FACING_0_5 = {D: 0, U: 1, N: 2, S: 3, W: 4, E: 5}


def facing_meta(name: str, direction: str | Vec) -> int:
    """Front face toward `direction`. Furnace/chest/dispenser style (2..5, dispenser/piston also 0/1);
    for ladders and wall signs the direction is the side they face (away from the wall they hang on)."""
    v = vec(direction)
    table = _FACING_0_5 if name in _SIX_WAY else _FACING_2_5
    if v not in table:
        raise ValueError(f"{name} cannot face {DIR_NAMES[v]}")
    return table[v]


# ---- schemes -----------------------------------------------------------------------------------
class Scheme:
    """mask: bits holding orientation; table: orientation bits -> direction; axis: compare by |dot|."""

    def __init__(self, mask: int, table: dict[int, Vec], axis: bool = False):
        self.mask, self.table, self.axis = mask, table, axis

    def transform(self, meta: int, f: Callable[[Vec], Vec]) -> int:
        bits = meta & self.mask
        if bits not in self.table:
            return meta
        out = f(self.table[bits])
        if self.axis:
            out = tuple(abs(c) for c in out)
            match = [k for k, v in self.table.items() if tuple(abs(c) for c in v) == out]
        else:
            match = [k for k, v in self.table.items() if v == out]
        return (meta & ~self.mask) | match[0] if match else meta


def _four(metas: list[int], order=(N, E, S, W)) -> Scheme:
    mask = 0
    for m in metas:
        mask |= m
    return Scheme(mask, {m & mask: d for m, d in zip(metas, order)})


def _stairs_json(entry: dict) -> Scheme:
    table: dict[int, Vec] = {}
    mask = 0
    for key in ("bottom", "top"):
        for m in entry.get(key, []):
            mask |= m
    for key in ("bottom", "top"):
        for m, d in zip(entry.get(key, []), (N, E, S, W)):
            table[m & mask] = d
    return Scheme(mask, table)


def _pillar_groups(groups: list[list[int]], meta: int) -> Scheme | None:
    mask = -1
    for g in groups:
        mask &= g[0] | g[1] | g[2]
    for g in groups:
        if meta & mask in (g[0] & mask, g[1] & mask, g[2] & mask):
            return Scheme(mask, {g[0] & mask: U, g[1] & mask: E, g[2] & mask: S}, axis=True)
    return None


def _trapdoor(entry: dict) -> Scheme:
    mask = 0
    for k in ("bottom", "top"):
        for state in entry.get(k, {}).values():
            for m in state:
                mask |= m
    # attachment wall by orientation bits & 3: 0 south, 1 north, 2 east, 3 west (vanilla layout)
    return Scheme(3, {0: S, 1: N, 2: E, 3: W})


_VANILLA_STAIRS = Scheme(3, {0: E, 1: W, 2: S, 3: N})
_SIX_WAY = {"minecraft:dispenser", "minecraft:dropper", "minecraft:piston", "minecraft:sticky_piston",
            "minecraft:piston_head", "minecraft:hopper"}
_VANILLA: dict[str, Scheme] = {}
for _n in ("furnace", "lit_furnace", "chest", "trapped_chest", "ender_chest", "ladder", "wall_sign"):
    _VANILLA[f"minecraft:{_n}"] = Scheme(7, {2: N, 3: S, 4: W, 5: E})
for _n in _SIX_WAY:
    _VANILLA[_n] = Scheme(7, {0: D, 1: U, 2: N, 3: S, 4: W, 5: E})
for _n in ("torch", "redstone_torch", "unlit_redstone_torch", "stone_button", "wooden_button", "lever"):
    _VANILLA[f"minecraft:{_n}"] = Scheme(7, {1: E, 2: W, 3: S, 4: N})
for _n in ("pumpkin", "lit_pumpkin", "bed", "unpowered_repeater", "powered_repeater", "unpowered_comparator",
           "powered_comparator", "fence_gate", "tripwire_hook", "cocoa"):
    _VANILLA[f"minecraft:{_n}"] = Scheme(3, {0: S, 1: W, 2: N, 3: E})
for _n in ("wooden_door", "iron_door"):  # lower half only; upper half (meta & 8) carries the hinge bit
    _VANILLA[f"minecraft:{_n}"] = Scheme(3, {0: E, 1: S, 2: W, 3: N})
_VANILLA["minecraft:trapdoor"] = Scheme(3, {0: S, 1: N, 2: E, 3: W})
for _n in ("log", "log2", "hay_block"):
    _VANILLA[f"minecraft:{_n}"] = Scheme(12, {0: U, 4: E, 8: S}, axis=True)
_VANILLA["minecraft:quartz_block"] = Scheme(7, {2: U, 3: E, 4: S}, axis=True)


@lru_cache(maxsize=1)
def _we_mappings() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in sorted((Path(__file__).parent / "data" / "we-mappings").glob("*.json")):
        text = "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("//"))
        for reg, entry in json.loads(text).items():
            out[reg] = {"kind": f.stem, **entry}
    return out


def scheme_for(name: str, meta: int, palette: "Palette") -> Scheme | None:
    if name in _VANILLA:
        if name.endswith("_door") and meta & 8:
            return None
        return _VANILLA[name]
    entry = _we_mappings().get(name)
    if entry:
        kind = entry["kind"]
        if kind == "stairs":
            return _stairs_json(entry)
        if kind == "pillar":
            return _pillar_groups([g for g in entry["groups"].values()], meta)
        if kind in ("fence_gate", "other") and "metas" in entry:
            return _four(entry["metas"])
        if kind == "trap_door":
            return _trapdoor(entry)
    info = palette.info(name, meta)
    if info is None:
        return None
    if info.render_type == 10:
        return _VANILLA_STAIRS
    if info.render_type == 31:
        return Scheme(12, {0: U, 4: E, 8: S}, axis=True)
    if info.render_type == 21:
        return Scheme(3, {0: S, 1: W, 2: N, 3: E})
    return None


def _vine(meta: int, f: Callable[[Vec], Vec]) -> int:
    bits = {1: S, 2: W, 4: N, 8: E}
    back = {v: k for k, v in bits.items()}
    out = 0
    for bit, d in bits.items():
        if meta & bit:
            out |= back[f(d)]
    return out


def transform_block(b: "Block", f: Callable[[Vec], Vec], palette: "Palette", sign: Callable[[int], int]) -> "Block":
    from . import modblocks

    if b.te is not None:
        handled = modblocks.transform_te(b, f)
        if handled is not None:
            return handled
    if b.name == "minecraft:vine":
        return b.with_meta(_vine(b.meta, f))
    if b.name == "minecraft:standing_sign":
        return b.with_meta(sign(b.meta))
    sch = scheme_for(b.name, b.meta, palette)
    if sch is None:
        return b
    return b.with_meta(sch.transform(b.meta, f))


def rot_cw(v: Vec) -> Vec:
    """90° clockwise seen from above: north -> east -> south -> west."""
    return (-v[2], v[1], v[0])


def rotate_block(b: "Block", turns: int, palette: "Palette") -> "Block":
    turns %= 4
    if not turns:
        return b

    def f(v: Vec) -> Vec:
        for _ in range(turns):
            v = rot_cw(v)
        return v

    return transform_block(b, f, palette, lambda r: (r + 4 * turns) & 15)


def mirror_block(b: "Block", axis: str, palette: "Palette") -> "Block":
    """axis 'x' negates x (east <-> west); 'z' negates z (north <-> south)."""
    if axis == "x":
        return transform_block(b, lambda v: (-v[0], v[1], v[2]), palette, lambda r: (16 - r) & 15)
    if axis == "z":
        return transform_block(b, lambda v: (v[0], v[1], -v[2]), palette, lambda r: (8 - r) & 15)
    raise ValueError("mirror axis must be 'x' or 'z'")
