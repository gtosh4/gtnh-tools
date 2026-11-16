"""Real terrain: read a 1.7.10 Anvil world (EndlessIDs chunk layout, as GTNH 2.9 saves it) into a Build
in world coordinates, so designs can be carved into the actual ground and exported with it.

A schematic is a full box: every cell is written on paste, so cells the design leaves alone must carry
the real terrain or WorldEdit would replace them with air. Load the box from a fresh copy of the
server world (`sync`) right before exporting, and paste soon after: anything changed in game between
the two is reverted inside the box.

Section layout (EndlessIDs): block id = Blocks | Add<<8 | BlocksB2Hi<<12 | BlocksB3<<16 (nibble arrays
for Add/BlocksB2Hi), metadata = Data | Data1High<<4 | Data2<<8. Ids map to registry names through the
world's own level.dat FML ItemData, so a copy of the server's level.dat must sit next to its regions.
"""
from __future__ import annotations

import os
import subprocess
import zlib
from functools import lru_cache
from pathlib import Path

from . import nbt
from .build import Block, Build
from .palette import Palette, default as default_palette

# Local copy of the Threshold server world (level.dat + region/), filled by `sync`.
WORLD = Path(os.environ.get("GTNH_WORLD", Path.home() / ".cache/gtnhbuild/threshold"))
# scp source for `sync`: host:path of the server's world folder.
SERVER_WORLD = os.environ.get(
    "GTNH_SERVER_WORLD",
    "192.168.4.118:/silenus/minecraft/servers/ba68f64e-3802-4c5c-890d-4535e409e181/World")

Pos = tuple[int, int, int]


def _regions(a: Pos, b: Pos) -> list[tuple[int, int]]:
    xs = range(min(a[0], b[0]) >> 9, (max(a[0], b[0]) >> 9) + 1)
    zs = range(min(a[2], b[2]) >> 9, (max(a[2], b[2]) >> 9) + 1)
    return [(rx, rz) for rx in xs for rz in zs]


def sync(a: Pos, b: Pos, *, world: Path = WORLD, server: str = SERVER_WORLD) -> list[Path]:
    """Copy level.dat and the region files covering box a..b from the server (scp, BatchMode)."""
    (world / "region").mkdir(parents=True, exist_ok=True)
    pairs = [("level.dat", world / "level.dat")]
    pairs += [(f"region/r.{rx}.{rz}.mca", world / "region" / f"r.{rx}.{rz}.mca") for rx, rz in _regions(a, b)]
    for rel, dst in pairs:
        subprocess.run(["scp", "-q", "-o", "BatchMode=yes", f"{server}/{rel}", str(dst)], check=True)
    open_world.cache_clear()
    return [dst for _, dst in pairs]


def _nibble(arr: bytes, i: int) -> int:
    v = arr[i >> 1]
    return (v >> 4) & 0xF if i & 1 else v & 0xF


class World:
    """One world folder. Chunks are decoded on demand and cached per instance."""

    def __init__(self, path: Path = WORLD):
        self.path = Path(path)
        _, root = nbt.load(self.path / "level.dat")
        self.names: dict[int, str] = {}
        self.items: dict[str, int] = {}
        for e in root["FML"]["ItemData"].items:
            key = e["K"]
            if key.startswith("\x01"):  # \x01 = block, \x02 = item
                self.names[e["V"].v] = key[1:]
            elif key.startswith("\x02"):
                self.items[key[1:]] = e["V"].v
        self._chunks: dict[tuple[int, int], dict | None] = {}

    def chunk(self, cx: int, cz: int) -> dict | None:
        key = (cx, cz)
        if key not in self._chunks:
            self._chunks[key] = self._read_chunk(cx, cz)
        return self._chunks[key]

    def _read_chunk(self, cx: int, cz: int) -> dict | None:
        path = self.path / "region" / f"r.{cx >> 5}.{cz >> 5}.mca"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing: run terrain.sync() for this area first")
        with open(path, "rb") as fh:
            fh.seek(4 * ((cx & 31) + (cz & 31) * 32))
            loc = int.from_bytes(fh.read(4), "big")
            if loc == 0:
                return None  # never generated
            fh.seek((loc >> 8) * 4096)
            length = int.from_bytes(fh.read(4), "big")
            compression = fh.read(1)[0]
            raw = fh.read(length - 1)
        if compression != 2:
            raise ValueError(f"chunk {cx},{cz}: unsupported compression {compression}")
        _, root = nbt.loads(zlib.decompress(raw))
        level = root["Level"]
        sections = {}
        for s in level["Sections"].items:
            if "Data16" in s:
                raise ValueError(f"chunk {cx},{cz}: 16-bit Data16 sections are not understood")
            sections[s["Y"].v] = s
        tiles = {}
        for te in level.get("TileEntities", nbt.List(nbt.COMPOUND)).items:
            tiles[(te["x"].v, te["y"].v, te["z"].v)] = {k: v for k, v in te.items() if k not in ("x", "y", "z")}
        return {"sections": sections, "tiles": tiles}

    def get(self, x: int, y: int, z: int) -> Block | None:
        """Block at a world position (None = air or ungenerated)."""
        ch = self.chunk(x >> 4, z >> 4)
        if ch is None or not 0 <= y < 256:
            return None
        s = ch["sections"].get(y >> 4)
        if s is None:
            return None
        i = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
        bid = s["Blocks"][i]
        if "Add" in s:
            bid |= _nibble(s["Add"], i) << 8
        if "BlocksB2Hi" in s:
            bid |= _nibble(s["BlocksB2Hi"], i) << 12
        if "BlocksB3" in s:
            bid |= s["BlocksB3"][i] << 16
        if bid == 0:
            return None
        meta = _nibble(s["Data"], i)
        if "Data1High" in s:
            meta |= _nibble(s["Data1High"], i) << 4
        if "Data2" in s:
            meta |= s["Data2"][i] << 8
        name = self.names.get(bid)
        if name is None:
            raise KeyError(f"block id {bid} at {(x, y, z)} not in level.dat ItemData")
        return Block(name, meta, ch["tiles"].get((x, y, z)))

    def load(self, a: Pos, b: Pos, name: str = "terrain", palette: Palette | None = None) -> Build:
        """Every non-air block in box a..b (inclusive), tile entities included, in world coordinates."""
        out = Build(name, palette or default_palette())
        (x0, x1), (y0, y1), (z0, z1) = (sorted((a[i], b[i])) for i in range(3))
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(y0, y1 + 1):
                    blk = self.get(x, y, z)
                    if blk is not None:
                        out.blocks[(x, y, z)] = blk
        out.base = dict(out.blocks)
        out.box = ((x0, y0, z0), (x1, y1, z1))
        out.item_registry = self.items
        return out

    def height(self, x: int, z: int, *, solid=lambda b: True) -> int | None:
        """Highest y whose block passes `solid` (default: any non-air block)."""
        for y in range(255, -1, -1):
            blk = self.get(x, y, z)
            if blk is not None and solid(blk):
                return y
        return None


@lru_cache(maxsize=4)
def open_world(path: str | os.PathLike = WORLD) -> World:
    """Cached World for a folder (decoded chunks are kept between loads)."""
    return World(Path(path))
