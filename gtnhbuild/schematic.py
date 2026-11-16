"""MCEdit/WorldEdit `.schematic` I/O with name-based block mappings.

Written files carry both `BlockMapping` (WorldEdit-GTNH) and `SchematicaMapping` (Schematica-GTNH), so
the local numeric ids inside are remapped by registry name on load, in any world. Ids stay < 256 so no
`AddBlocks` array is needed (WorldEdit and Schematica disagree on its nibble order). Metadata above 255
(EndlessIDs: GT ores, terrain carried along by terrain.py) goes in WorldEdit's `AddData` high byte.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import nbt
from .build import Block, Build
from .palette import Palette, default as default_palette

# Threshold instance: Schematica reads .minecraft/schematics; Forge WorldEdit resolves its
# schematicSaveDir ("schematics") against config/worldedit/. Default saves go to both.
_INSTANCE = Path("/var/mnt/mercury/Minecraft/Instances/GTNH Threshold/.minecraft")
SCHEMATICS_DIRS = [Path(p) for p in os.environ.get(
    "GTNH_SCHEMATICS_DIRS", f"{_INSTANCE / 'schematics'}{os.pathsep}{_INSTANCE / 'config/worldedit/schematics'}"
).split(os.pathsep) if p]
# The Threshold server runs WorldEdit server-side: `//schem load` reads the server's own
# config/worldedit/schematics. Default saves are also copied there (scp); set it to "" to skip.
SERVER_SCHEMATICS = os.environ.get(
    "GTNH_SERVER_SCHEMATICS",
    "192.168.4.118:/silenus/minecraft/servers/ba68f64e-3802-4c5c-890d-4535e409e181/config/worldedit/schematics")


def to_nbt(build: Build) -> dict:
    if not build.blocks:
        raise ValueError("empty build")
    lo, hi = build.bounds()
    w, h, l = (hi[i] - lo[i] + 1 for i in range(3))
    if max(w, h, l) > 32767:
        raise ValueError("schematic dimension exceeds 32767")
    ids: dict[str, int] = {}
    blocks = bytearray(w * h * l)
    data = bytearray(w * h * l)
    add_data = bytearray(w * h * l)
    tiles: list[dict] = []
    for (x, y, z), b in sorted(build.blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        local = ids.setdefault(b.name, len(ids) + 1)
        if local > 255:
            raise ValueError("more than 255 distinct block registry names in one schematic; split the build")
        if not 0 <= b.meta <= 0xFFFF:
            raise ValueError(f"{b} at {(x, y, z)}: meta must be 0..65535")
        rx, ry, rz = x - lo[0], y - lo[1], z - lo[2]
        i = (ry * l + rz) * w + rx
        blocks[i] = local
        data[i] = b.meta & 0xFF
        add_data[i] = b.meta >> 8
        if b.te is not None:
            te = dict(b.te)
            te["x"], te["y"], te["z"] = nbt.Int(rx), nbt.Int(ry), nbt.Int(rz)
            tiles.append(te)
    mapping = {name: nbt.Short(i) for name, i in ids.items()}
    anchor = build.anchor
    out = {
        "Width": nbt.Short(w), "Height": nbt.Short(h), "Length": nbt.Short(l),
        "Materials": "Alpha",
        "Blocks": bytes(blocks), "Data": bytes(data),
        "Entities": nbt.List(nbt.COMPOUND, []),
        "TileEntities": nbt.List(nbt.COMPOUND, tiles),
        # Clipboard region min = WEOrigin; paste anchor = WEOrigin - WEOffset = build.anchor. In
        # world-coordinate builds `//paste -o` therefore lands every block on its own coordinates.
        "WEOriginX": nbt.Int(lo[0]), "WEOriginY": nbt.Int(lo[1]), "WEOriginZ": nbt.Int(lo[2]),
        "WEOffsetX": nbt.Int(lo[0] - anchor[0]), "WEOffsetY": nbt.Int(lo[1] - anchor[1]),
        "WEOffsetZ": nbt.Int(lo[2] - anchor[2]),
        "BlockMapping": mapping,
        "SchematicaMapping": dict(mapping),
    }
    if any(add_data):
        out["AddData"] = bytes(add_data)
    items = _item_mapping(build, tiles)
    if items:
        out["ItemMapping"] = items
    return out


def _item_mapping(build: Build, tiles: list[dict]) -> dict:
    """name -> Short(id) for every item stack in the tile entities (compounds WorldEdit treats as items:
    id+Count+Damage or Item+Count+Meta). WorldEdit remaps those ids by name on load, so inventories
    and info-panel cards survive a world with different item ids."""
    reg = build.item_registry or build.palette.numeric_ids()[1]
    names = {v: k for k, v in reg.items()}
    found: dict = {}

    def walk(v) -> None:
        if isinstance(v, dict):
            for key, extra in (("id", ("Count", "Damage")), ("Item", ("Count", "Meta"))):
                tag = v.get(key)
                if isinstance(tag, (nbt.Short, nbt.Int)) and all(k in v for k in extra):
                    name = names.get(tag.v & 0xFFFF)
                    if name is not None:
                        found[name] = nbt.Short(tag.v & 0xFFFF)
            for child in v.values():
                walk(child)
        elif isinstance(v, nbt.List):
            for child in v.items:
                walk(child)

    for te in tiles:
        walk(te)
    return found


def save(build: Build, path: str | os.PathLike | None = None) -> list[str]:
    """Write gzip NBT to `path`, or by default <dir>/<build.name>.schematic in every SCHEMATICS_DIRS
    plus a copy to SERVER_SCHEMATICS. A failed server copy is reported on stderr, not raised."""
    targets = [Path(path)] if path else [d / f"{build.name}.schematic" for d in SCHEMATICS_DIRS]
    data = to_nbt(build)
    out: list[str] = []
    for target in targets:
        if target.suffix != ".schematic":
            target = target.with_suffix(".schematic")
        target.parent.mkdir(parents=True, exist_ok=True)
        nbt.save(target, data, "Schematic")
        out.append(str(target))
    if not path and SERVER_SCHEMATICS:
        host, _, remote_dir = SERVER_SCHEMATICS.partition(":")
        remote = f"{remote_dir}/{targets[0].stem}.schematic"
        try:
            subprocess.run(["ssh", "-o", "BatchMode=yes", host, "mkdir", "-p", remote_dir], check=True,
                           capture_output=True, timeout=30)
            subprocess.run(["scp", "-q", "-o", "BatchMode=yes", out[0], f"{host}:{remote}"], check=True,
                           capture_output=True, timeout=120)
            out.append(f"{host}:{remote}")
        except (subprocess.SubprocessError, OSError) as e:
            print(f"server copy to {SERVER_SCHEMATICS} failed: {e}", file=sys.stderr)
    return out


def load(path: str | os.PathLike, palette: Palette | None = None) -> Build:
    """Read any Alpha schematic (ours, WorldEdit's, Schematica's) into a Build.

    Block names come from BlockMapping / SchematicaMapping; files without either fall back to the
    level.dat id table (correct only for schematics saved from a world with the same ids)."""
    palette = palette or default_palette()
    _, root = nbt.load(path)
    w, h, l = root["Width"].v, root["Height"].v, root["Length"].v
    names: dict[int, str] = {}
    for key in ("SchematicaMapping", "BlockMapping"):
        for name, sid in root.get(key, {}).items():
            names[sid.v & 0xFFFF] = name
    if not names:
        names = {v: k for k, v in palette.numeric_ids()[0].items()}
    raw, meta = root["Blocks"], root["Data"]
    add = root.get("AddBlocks", b"")
    add_data = root.get("AddData")
    tiles = {}
    for te in root.get("TileEntities", nbt.List(nbt.COMPOUND)).items:
        pos = (te["x"].v, te["y"].v, te["z"].v)
        tiles[pos] = {k: v for k, v in te.items() if k not in ("x", "y", "z")}
    origin = [root[f"WEOrigin{a}"].v if f"WEOrigin{a}" in root else 0 for a in "XYZ"]
    offset = [root[f"WEOffset{a}"].v if f"WEOffset{a}" in root else 0 for a in "XYZ"]
    # Keep WorldEdit's coordinates: blocks at WEOrigin + local, anchor where the paste anchor was.
    out = Build(Path(path).stem, palette, anchor=tuple(origin[i] - offset[i] for i in range(3)))
    for y in range(h):
        for z in range(l):
            for x in range(w):
                i = (y * l + z) * w + x
                bid = raw[i]
                if add and (i >> 1) < len(add):  # WorldEdit nibble order
                    bid |= ((add[i >> 1] & 0x0F) << 8) if i & 1 == 0 else ((add[i >> 1] & 0xF0) << 4)
                if bid == 0:
                    continue
                m = meta[i] | ((add_data[i] << 8) if add_data else 0)
                name = names.get(bid, f"unknown:{bid}")
                pos = (origin[0] + x, origin[1] + y, origin[2] + z)
                out.blocks[pos] = Block(name, m, tiles.get((x, y, z)))
    return out
