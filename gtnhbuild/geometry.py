"""Approximate block models as textured faces, shared by the PNG renderer and the HTML viewer.

A face is a planar quad or triangle in block-local units (0..1, +x east, +y up, +z south) with texture
coordinates in 0..1 (u right, v down) and a texture name (or flat colour). Models are faithful for
cubes, slabs, stairs, logs, panes, fences, walls, plants and the mod shapes in modblocks; everything
else falls back to its collision box.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from .orient import D, E, N, S, U, W
from .palette import Palette

Pt = tuple[float, float, float]


@dataclass(frozen=True)
class Face:
    pts: tuple[Pt, ...]
    uvs: tuple[tuple[float, float], ...]
    tex: str | None
    color: str | None
    normal: Pt
    bright: bool = False  # full-bright (Lapis Caelestis, Anti Blocks, glow shapes): drawn unshaded


def _sub(a: Pt, b: Pt) -> Pt:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def normal_of(pts: tuple[Pt, ...]) -> Pt:
    a, b = _sub(pts[1], pts[0]), _sub(pts[2], pts[0])
    n = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    m = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
    return (n[0] / m, n[1] / m, n[2] / m)


def face(pts, uvs, tex, color=None) -> Face:
    pts = tuple(tuple(float(c) for c in p) for p in pts)
    return Face(pts, tuple(uvs), tex, color, normal_of(pts))


def box(x0, y0, z0, x1, y1, z1, tex: tuple, colors: tuple = (None,) * 6, sides=range(6)) -> list[Face]:
    """Axis-aligned box; tex/colors indexed by side (down, up, north, south, west, east). UVs follow
    world position like Minecraft, so a slab shows the matching half of its texture.
    Vertices are counter-clockwise seen from outside."""
    out = []
    for s in sides:
        if s == 0:  # down
            pts = ((x0, y0, z1), (x0, y0, z0), (x1, y0, z0), (x1, y0, z1))
            uvs = ((x0, z1), (x0, z0), (x1, z0), (x1, z1))
        elif s == 1:  # up
            pts = ((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))
            uvs = ((x0, z0), (x0, z1), (x1, z1), (x1, z0))
        elif s == 2:  # north (-z): seen from north, u runs east->west
            pts = ((x1, y1, z0), (x1, y0, z0), (x0, y0, z0), (x0, y1, z0))
            uvs = ((1 - x1, 1 - y1), (1 - x1, 1 - y0), (1 - x0, 1 - y0), (1 - x0, 1 - y1))
        elif s == 3:  # south (+z)
            pts = ((x0, y1, z1), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1))
            uvs = ((x0, 1 - y1), (x0, 1 - y0), (x1, 1 - y0), (x1, 1 - y1))
        elif s == 4:  # west (-x)
            pts = ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1))
            uvs = ((z0, 1 - y1), (z0, 1 - y0), (z1, 1 - y0), (z1, 1 - y1))
        else:  # east (+x)
            pts = ((x1, y1, z1), (x1, y0, z1), (x1, y0, z0), (x1, y1, z0))
            uvs = ((1 - z1, 1 - y1), (1 - z1, 1 - y0), (1 - z0, 1 - y0), (1 - z0, 1 - y1))
        out.append(face(pts, uvs, tex[s], colors[s]))
    return out


def _cross(tex: str | None, h: float = 1.0) -> list[Face]:
    a, b = 0.15, 0.85
    uv = ((0, 1 - h), (0, 1), (1, 1), (1, 1 - h))
    planes = [((a, h, a), (a, 0, a), (b, 0, b), (b, h, b)), ((a, h, b), (a, 0, b), (b, 0, a), (b, h, a))]
    out = []
    for p in planes:
        out.append(face(p, uv, tex))
        out.append(face(tuple(reversed(p)), tuple(reversed(uv)), tex))  # double-sided
    return out


def _stairs(meta: int, tex: tuple) -> list[Face]:
    top = bool(meta & 4)
    lo, hi = (0.5, 1.0) if top else (0.0, 0.5)
    sy0, sy1 = (0.0, 0.5) if top else (0.5, 1.0)
    out = box(0, lo, 0, 1, hi, 1, tex)
    d = meta & 3
    step = {0: (0.5, 0, 1, 1), 1: (0, 0, 0.5, 1), 2: (0, 0.5, 1, 1), 3: (0, 0, 1, 0.5)}[d]
    out += box(step[0], sy0, step[1], step[2], sy1, step[3], tex)
    return out


def _axis_textures(tex: tuple, axis: str) -> tuple:
    """Pillar-style block lying along `axis`: its end texture (up/down) moves to the faces on that axis."""
    end, side = tex[1], tex[2]
    if axis == "x":
        return (side, side, side, side, end, end)
    if axis == "z":
        return (side, side, end, end, side, side)
    return tex


Neighbour = Callable[[tuple[int, int, int]], "object | None"]


def _connects(nb, palette: Palette, kinds: set[int]) -> bool:
    if nb is None:
        return False
    info = palette.info(nb.name, nb.meta)
    return bool(info and (info.opaque or info.render_type in kinds or "pane" in nb.name.lower()))


def faces_for(block, palette: Palette, neighbour: Neighbour | None = None) -> list[Face]:
    """Faces of one block in local coordinates. `neighbour(dir)` returns the Block next to it (for
    fences/panes/walls). Full-bright blocks come back flagged (and Lapis Caelestis in its flat colour)."""
    faces = _faces_for(block, palette, neighbour)
    if block.te is None:
        return with_material_look(faces, block.name, block.meta)
    from .modblocks import material_of

    mat = material_of(block)
    if mat:
        faces = with_material_look(faces, *mat)
    if block.name == "ArchitectureCraft:shapeSE":
        return [replace(f, bright=True) for f in faces]
    return faces


def with_material_look(faces: list[Face], reg: str, meta: int) -> list[Face]:
    from .lighting import flat_color, full_bright

    if not full_bright(reg, meta):
        return faces
    color = flat_color(reg, meta)
    if color:
        return [replace(f, tex=None, color=color, bright=True) for f in faces]
    return [replace(f, bright=True) for f in faces]


def _faces_for(block, palette: Palette, neighbour: Neighbour | None = None) -> list[Face]:
    from . import modblocks

    custom = modblocks.geometry(block, palette)
    if custom is not None:
        return custom
    info = palette.info(block.name, block.meta)
    if info is None:
        return box(0, 0, 0, 1, 1, 1, (None,) * 6, ("#ff00ff",) * 6)
    tex = palette.face_textures(block.name, block.meta)
    colors = tuple(None if t else "#808080" for t in tex)
    rt = info.render_type
    nb = neighbour or (lambda d: None)
    if rt == 10:
        return _stairs(block.meta, tex)
    if rt == 31 or block.name == "minecraft:hay_block":
        return box(0, 0, 0, 1, 1, 1, _axis_textures(tex, {1: "x", 2: "z"}.get((block.meta >> 2) & 3, "y")))
    if block.name == "minecraft:quartz_block" and block.meta in (3, 4):
        return box(0, 0, 0, 1, 1, 1, _axis_textures(tex, "x" if block.meta == 3 else "z"))
    if rt in (1, 6, 40, 23) and not info.normal:
        return _cross(tex[2] or tex[1])
    if rt == 2:  # torch: stick
        return box(7 / 16, 0, 7 / 16, 9 / 16, 10 / 16, 9 / 16, tex)
    if rt == 4:  # liquid
        return box(0, 0, 0, 1, 14 / 16, 1, tex)
    if rt in (11, 32, 18, 41) or "pane" in block.name.lower() or block.name == "minecraft:iron_bars":
        if rt == 11:
            post, arm = (6 / 16, 10 / 16), (7 / 16, 9 / 16)
            arm_y = (6 / 16, 15 / 16)
            top = 1.0
        elif rt == 32:
            post, arm = (4 / 16, 12 / 16), (5 / 16, 11 / 16)
            arm_y = (0, 13 / 16)
            top = 1.0
        else:
            post, arm = (7 / 16, 9 / 16), (7 / 16, 9 / 16)
            arm_y = (0, 1)
            top = 1.0
        kinds = {rt, 21} if rt != 18 else {18, 41}
        out = box(post[0], 0, post[0], post[1], top, post[1], tex)
        for d, (x0, z0, x1, z1) in ((N, (arm[0], 0, arm[1], post[0])), (S, (arm[0], post[1], arm[1], 1)),
                                    (W, (0, arm[0], post[0], arm[1])), (E, (post[1], arm[0], 1, arm[1]))):
            if _connects(nb(d), palette, kinds):
                out += box(x0, arm_y[0], z0, x1, arm_y[1], z1, tex)
        return out
    if rt == 8:  # ladder: plate against the wall it hangs on
        d = block.meta & 7
        t = 1 / 16
        plate = {2: (0, 0, 1 - t, 1, 1, 1), 3: (0, 0, 0, 1, 1, t), 4: (1 - t, 0, 0, 1, 1, 1), 5: (0, 0, 0, t, 1, 1)}
        return box(*plate.get(d, (0, 0, 1 - t, 1, 1, 1)), tex)
    if rt == 7:  # door
        t = 3 / 16
        d = block.meta & 3
        plate = {0: (0, 0, 0, t, 1, 1), 1: (0, 0, 0, 1, 1, t), 2: (1 - t, 0, 0, 1, 1, 1), 3: (0, 0, 1 - t, 1, 1, 1)}
        return box(*plate[d], tex)
    if rt == 21:  # fence gate (closed): bar along its axis
        along_x = (block.meta & 1) == 0
        return box(0, 6 / 16, 7 / 16, 1, 15 / 16, 9 / 16, tex) if along_x else box(7 / 16, 6 / 16, 0, 9 / 16, 15 / 16, 1, tex)
    if rt in (9, 5):  # rails, redstone wire
        return box(0, 0, 0, 1, 1 / 16, 1, tex, sides=(1,))
    x0, y0, z0, x1, y1, z1 = info.bounds
    # A slab's meta & 8 means "top half" only when that meta is not itself an item variant
    # (chisel slabs use metas 8..15 as patterns and have separate *_top blocks).
    if (y1 - y0) <= 0.5 + 1e-6 and y0 == 0 and block.meta & 8 and info.meta != block.meta:
        y0, y1 = 0.5, 1.0
    return box(x0, y0, z0, x1, y1, z1, tex, colors)


def is_full_opaque(block, palette: Palette) -> bool:
    if block is None or block.te is not None:
        return False
    info = palette.info(block.name, block.meta)
    return bool(info and info.opaque and info.bounds == (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
                and info.render_type not in (10, 1, 2, 4, 7, 8, 9, 11, 18, 21, 32))

SIDE_DIRS = (D, U, N, S, W, E)
