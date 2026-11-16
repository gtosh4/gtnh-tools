"""Block palette: blocks.db lookups, face textures, and the world's numeric ID table."""
from __future__ import annotations

import io
import os
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image

from . import nbt

ROOT = Path(__file__).resolve().parent.parent
BLOCKS_DB = Path(os.environ.get("GTNH_BLOCKS_DB", ROOT / "blocks.db"))
TEXTURES_ZIP = Path(os.environ.get("GTNH_TEXTURES_ZIP", ROOT / "block-textures.zip"))
# Any GTNH 2.9 world's level.dat: its FML ItemData holds the numeric block/item ids. Only matters for
# numeric item ids inside tile-entity NBT (Carpenter's covers) when loaded through Schematica; WorldEdit
# and Schematica both remap block ids by name.
LEVEL_DAT = Path(os.environ.get(
    "GTNH_LEVEL_DAT",
    "/var/mnt/mercury/Minecraft/Instances/GTNH Threshold/.minecraft/saves/export/level.dat"))

SIDES = ("down", "up", "north", "south", "west", "east")  # ForgeDirection order 0..5
# Vanilla blocks with no item of their own (blocks.db lists item-placeable blocks): valid in builds by
# block name, drawn by the previews as their collision box or not at all.
ITEMLESS = frozenset({"minecraft:standing_sign", "minecraft:wall_sign"})


@dataclass(frozen=True)
class BlockInfo:
    id: str            # "<registry>~<meta>" (blocks.db primary key)
    registry: str      # "mod:name" as WorldEdit/Schematica use it
    meta: int
    item_id: str       # nesql.db item id ("i~mod~name~meta")
    name: str          # localized name
    opaque: bool       # opaque_cube: hides neighbour faces, blocks light
    normal: bool       # normal_block: full solid cube
    render_type: int
    render_pass: int   # 1 = translucent pass (glass, ice, water)
    light: int
    bounds: tuple[float, float, float, float, float, float]

    @property
    def gtnh_item(self) -> str:
        """Item id in the `./gtnh` CLI format (`i:mod:name:meta`)."""
        return self.item_id.replace("~", ":")


_COLS = ("id, registry_name, meta, item_id, localized_name, opaque_cube, normal_block, render_type, "
         "render_pass, light_value, min_x, min_y, min_z, max_x, max_y, max_z")


def _info(row) -> BlockInfo:
    b = tuple(1.0 if v is None and i >= 3 else (0.0 if v is None else v) for i, v in enumerate(row[10:16]))
    return BlockInfo(row[0], row[1], row[2], row[3], row[4], bool(row[5]), bool(row[6]), row[7], row[8], row[9], b)


def parse_spec(spec: str) -> tuple[str, int | None]:
    """'mod:name', 'mod:name:3', 'mod:name~3' -> (registry, meta or None)."""
    if "~" in spec:
        reg, meta = spec.rsplit("~", 1)
        return reg, int(meta)
    parts = spec.split(":")
    if len(parts) == 3 and parts[2].isdigit():
        return f"{parts[0]}:{parts[1]}", int(parts[2])
    return spec, None


class Palette:
    """Read-only view of blocks.db + block-textures.zip + level.dat id table."""

    def __init__(self, db: Path = BLOCKS_DB, textures: Path = TEXTURES_ZIP, level_dat: Path = LEVEL_DAT):
        self.db = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        self.textures_path = textures
        self.level_dat = level_dat
        self._zip: zipfile.ZipFile | None = None
        self._ids: tuple[dict[str, int], dict[str, int]] | None = None

    # ---- lookups -----------------------------------------------------------------------------
    @lru_cache(maxsize=None)
    def info(self, registry: str, meta: int = 0) -> BlockInfo | None:
        """Exact row, else the closest variant row (meta & 3/7/0) so oriented metas still resolve."""
        for m in dict.fromkeys((meta, meta & 7, meta & 3, 0)):
            row = self.db.execute(f"SELECT {_COLS} FROM block WHERE id = ?", (f"{registry}~{m}",)).fetchone()
            if row:
                return _info(row)
        return None

    def known(self, registry: str) -> bool:
        return registry in ITEMLESS or self.db.execute(
            "SELECT 1 FROM block WHERE registry_name = ? LIMIT 1", (registry,)).fetchone() is not None

    def resolve(self, spec: str) -> tuple[str, int]:
        """Block spec or exact localized name -> (registry, meta). Raises on unknown/ambiguous."""
        reg, meta = parse_spec(spec)
        if self.known(reg):
            return reg, meta or 0
        rows = self.db.execute(f"SELECT {_COLS} FROM block WHERE localized_name = ? COLLATE NOCASE", (spec,)).fetchall()
        if len(rows) == 1:
            return rows[0][1], rows[0][2]
        if rows:
            raise KeyError(f"{spec!r} is ambiguous: " + ", ".join(r[0] for r in rows[:8]))
        raise KeyError(f"unknown block {spec!r} (try `python -m gtnhbuild search`)")

    def search(self, query: str = "", *, mod: str | None = None, regex: bool = False, solid: bool | None = None,
               color: str | None = None, limit: int = 30) -> list[tuple[BlockInfo, str | None]]:
        """Search by localized name / registry name. `color` ('#rrggbb') sorts by nearest top-face colour.

        Returns (block, average colour of its top face)."""
        sql = (f"SELECT {_COLS}, t.average_color FROM block b LEFT JOIN block_face f ON f.block_id = b.id AND f.side = 1 "
               "LEFT JOIN texture t ON t.name = f.texture WHERE 1=1")
        args: list = []
        if mod:
            sql += " AND b.registry_name LIKE ?"
            args.append(f"{mod}:%")
        if solid is not None:
            sql += " AND b.opaque_cube = ?"
            args.append(int(solid))
        rows = self.db.execute(sql, args).fetchall()
        if query:
            if regex:
                rx = re.compile(query, re.I)
                rows = [r for r in rows if rx.search(r[4]) or rx.search(r[0])]
            else:
                q = query.lower()
                rows = [r for r in rows if q in r[4].lower() or q in r[0].lower()]
        if color:
            target = _rgb(color)
            rows = [r for r in rows if r[16]]
            rows.sort(key=lambda r: sum((a - b) ** 2 for a, b in zip(_rgb(r[16]), target)))
        return [(_info(r), r[16]) for r in rows[:limit]]

    def variants(self, registry: str) -> list[BlockInfo]:
        return [_info(r) for r in self.db.execute(f"SELECT {_COLS} FROM block WHERE registry_name = ? ORDER BY meta",
                                                  (registry,))]

    # ---- textures ----------------------------------------------------------------------------
    @lru_cache(maxsize=None)
    def face_textures(self, registry: str, meta: int = 0) -> tuple[str | None, ...]:
        """Texture name per side (down, up, north, south, west, east)."""
        info = self.info(registry, meta)
        out: list[str | None] = [None] * 6
        if info:
            for side, tex in self.db.execute("SELECT side, texture FROM block_face WHERE block_id = ?", (info.id,)):
                out[side] = tex
        return tuple(out)

    @lru_cache(maxsize=None)
    def texture_color(self, name: str | None) -> str | None:
        if not name:
            return None
        row = self.db.execute("SELECT average_color FROM texture WHERE name = ?", (name,)).fetchone()
        return row[0] if row else None

    @lru_cache(maxsize=None)
    def texture(self, name: str | None) -> Image.Image | None:
        """RGBA square image (first animation frame), biome tint applied for greyscale foliage."""
        if not name:
            return None
        row = self.db.execute("SELECT file FROM texture WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        if self._zip is None:
            self._zip = zipfile.ZipFile(self.textures_path)
        try:
            img = Image.open(io.BytesIO(self._zip.read(row[0]))).convert("RGBA")
        except KeyError:
            return None
        if img.height > img.width:  # animated strip
            img = img.crop((0, 0, img.width, img.width))
        tint = _TINTS.get(name)
        if tint:
            img = _tint(img, tint)
        return img

    # ---- numeric ids -------------------------------------------------------------------------
    def numeric_ids(self) -> tuple[dict[str, int], dict[str, int]]:
        """(block name -> id, item name -> id) from level.dat FML ItemData; empty if unavailable."""
        if self._ids is None:
            blocks: dict[str, int] = {}
            items: dict[str, int] = {}
            if self.level_dat.exists():
                _, root = nbt.load(self.level_dat)
                for entry in root.get("FML", {}).get("ItemData", nbt.List(nbt.COMPOUND)).items:
                    key, val = entry["K"], entry["V"].v
                    (blocks if key[0] == "\x01" else items)[key[1:]] = val
            self._ids = (blocks, items)
        return self._ids


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# Vanilla greyscale textures that the game tints by biome; plains-ish defaults.
_GRASS = (0x7C, 0xBD, 0x6B)
_FOLIAGE = (0x59, 0xAE, 0x30)
_TINTS = {
    "grass_top": _GRASS, "tallgrass": _GRASS, "fern": _GRASS, "double_plant_grass_top": _GRASS,
    "double_plant_grass_bottom": _GRASS, "double_plant_fern_top": _GRASS, "double_plant_fern_bottom": _GRASS,
    "leaves_oak": _FOLIAGE, "leaves_jungle": _FOLIAGE, "leaves_acacia": _FOLIAGE, "leaves_big_oak": _FOLIAGE,
    "leaves_birch": (0x80, 0xA7, 0x55), "leaves_spruce": (0x61, 0x99, 0x61), "vine": _FOLIAGE,
    "waterlily": (0x20, 0x80, 0x30), "water_still": (0x3F, 0x76, 0xE4), "water_flow": (0x3F, 0x76, 0xE4),
}


def _tint(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
    r, g, b, a = img.split()
    return Image.merge("RGBA", (r.point(lambda v: v * rgb[0] // 255), g.point(lambda v: v * rgb[1] // 255),
                                b.point(lambda v: v * rgb[2] // 255), a))


_default: Palette | None = None


def default() -> Palette:
    global _default
    if _default is None:
        _default = Palette()
    return _default
