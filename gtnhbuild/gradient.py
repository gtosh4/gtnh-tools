"""Colour gradients between blocks.

A *strip* is a run of blocks whose colours step evenly from one waypoint block to the next: the target
colours are interpolated in CIELAB (where straight-line distance roughly matches how different two
colours look) and each step takes the closest block from a pool. A *field* then lays the strip across a
box along an axis as clean bands, ordered-dithered bands, noise-wobbled bands, or map-like patches that
ignore the axis. Everything is seeded and deterministic: the same arguments give the same blocks.

Block colour = mean of the CIELAB colours of the faces you look at (`face`: "side", "top" or "all"),
from blocks.db `texture.average_color` (the active resource pack's textures).
"""
from __future__ import annotations

import math
import zlib
from typing import TYPE_CHECKING, Callable, Iterable

if TYPE_CHECKING:
    from .build import Block, Build
    from .palette import Palette

Lab = tuple[float, float, float]
Pos = tuple[int, int, int]
STYLES = ("bands", "dither", "noise", "patches")
_FACES = {"side": (2, 3, 4, 5), "top": (1,), "all": (0, 1, 2, 3, 4, 5)}
# 4x4 Bayer matrix, thresholds in (0, 1)
_BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def hex_lab(color: str) -> Lab:
    """'#rrggbb' -> CIELAB (D65)."""
    n = int(color.lstrip("#"), 16)

    def lin(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in ((n >> 16) & 255, (n >> 8) & 255, n & 255))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def block_lab(palette: "Palette", block: "Block", face: str = "side") -> Lab | None:
    """Mean CIELAB colour of the block's chosen faces; None if it has no textured face."""
    tex = palette.face_textures(block.name, block.meta)
    labs = [hex_lab(c) for c in (palette.texture_color(tex[i]) for i in _FACES[face]) if c]
    if not labs:
        return None
    return tuple(sum(v[i] for v in labs) / len(labs) for i in range(3))


def strip(palette: "Palette", waypoints: list["Block"], pool: Iterable["Block"] | None = None,
          steps: int | None = None, face: str = "side") -> list["Block"]:
    """`steps` blocks stepping from the first waypoint to the last through the others. Without a pool
    the strip is just the waypoints; with one, each step is the pool block (waypoints included) nearest
    to the interpolated target colour. Default steps: two in-between blocks per waypoint pair."""
    if len(waypoints) < 2:
        raise ValueError("a gradient needs at least two waypoint blocks")
    if pool is None:
        return list(waypoints)
    labs = [block_lab(palette, w, face) for w in waypoints]
    if any(v is None for v in labs):
        raise ValueError("every waypoint needs a textured face")
    cands = []
    for blk in list(waypoints) + [b for b in pool if b not in waypoints]:
        lab = block_lab(palette, blk, face)
        if lab is not None:
            cands.append((blk, lab))
    steps = steps or 3 * (len(waypoints) - 1) + 1
    out = []
    for i in range(steps):
        t = i / (steps - 1) * (len(waypoints) - 1)
        k = min(int(t), len(waypoints) - 2)
        u = t - k
        target = tuple(labs[k][j] + (labs[k + 1][j] - labs[k][j]) * u for j in range(3))
        out.append(min(cands, key=lambda c: sum((c[1][j] - target[j]) ** 2 for j in range(3)))[0])
    return out


def _hash01(seed: int, x: int, y: int, z: int) -> float:
    return zlib.crc32(f"{seed},{x},{y},{z}".encode()) / 0xFFFFFFFF


def value_noise(x: float, y: float, z: float, seed: int = 0, scale: float = 6.0) -> float:
    """Smooth 3D value noise in 0..1 with features about `scale` blocks across."""
    x, y, z = x / scale, y / scale, z / scale
    xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = (t - math.floor(t) for t in (x, y, z))
    sx, sy, sz = (t * t * (3 - 2 * t) for t in (fx, fy, fz))

    def lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    c = {(i, j, k): _hash01(seed, xi + i, yi + j, zi + k) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    x00 = lerp(c[0, 0, 0], c[1, 0, 0], sx)
    x10 = lerp(c[0, 1, 0], c[1, 1, 0], sx)
    x01 = lerp(c[0, 0, 1], c[1, 0, 1], sx)
    x11 = lerp(c[0, 1, 1], c[1, 1, 1], sx)
    return lerp(lerp(x00, x10, sy), lerp(x01, x11, sy), sz)


def field(lo: Pos, hi: Pos, n: int, *, axis: str = "y", style: str = "bands", seed: int = 0,
          scale: float = 6.0) -> Callable[[Pos], int]:
    """Position -> strip index (0..n-1) over the box lo..hi. `axis` 'x'/'y'/'z' runs the strip from
    the low to the high end; '-x'/'-y'/'-z' runs it the other way."""
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}")
    rev = axis.startswith("-")
    a = "xyz".index(axis.lstrip("-"))
    u_ax, v_ax = [i for i in range(3) if i != a]
    span = hi[a] - lo[a]

    def t_of(p: Pos) -> float:
        t = (p[a] - lo[a]) / span if span else 0.5
        return 1 - t if rev else t

    def index(p: Pos) -> int:
        if style == "patches":
            t = value_noise(*p, seed=seed, scale=scale)
        elif style == "noise":
            t = t_of(p) + (value_noise(*p, seed=seed, scale=scale) - 0.5) * 2.0 / n
        else:
            t = t_of(p)
        t = min(max(t, 0.0), 1.0)
        if style == "dither":
            f = t * (n - 1)
            i = math.floor(f)
            thr = (_BAYER[p[u_ax] % 4][p[v_ax] % 4] + 0.5) / 16
            return min(i + (1 if f - i > thr else 0), n - 1)
        return min(int(t * n), n - 1)

    return index


def apply(build: "Build", a: Pos, b: Pos, blocks: list["Block"], *, axis: str = "y", style: str = "bands",
          seed: int = 0, scale: float = 6.0, hollow: bool = False,
          only: Callable[[Pos, "Block | None"], bool] | None = None) -> "Build":
    """Fill box a..b with the strip `blocks` laid out by `field`. `hollow` paints only the box's shell;
    `only(pos, current_block)` restricts it further (e.g. recolour existing walls only)."""
    lo = tuple(min(a[i], b[i]) for i in range(3))
    hi = tuple(max(a[i], b[i]) for i in range(3))
    idx = field(lo, hi, len(blocks), axis=axis, style=style, seed=seed, scale=scale)
    for x in range(lo[0], hi[0] + 1):
        for y in range(lo[1], hi[1] + 1):
            for z in range(lo[2], hi[2] + 1):
                p = (x, y, z)
                if hollow and not (x in (lo[0], hi[0]) or y in (lo[1], hi[1]) or z in (lo[2], hi[2])):
                    continue
                if only is not None and not only(p, build.blocks.get(p)):
                    continue
                build.blocks[p] = blocks[idx(p)]
    return build
