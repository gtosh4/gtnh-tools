"""Previews: textured isometric PNGs, top-down layer slices, and ASCII layer maps."""
from __future__ import annotations

import math
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from .build import Block, Build
from .geometry import Face, faces_for, is_full_opaque
from .orient import DIR_NAMES, E, N, S, W, scheme_for
from .palette import Palette

COS30 = math.cos(math.radians(30))
VIEWS = {"se": 0, "ne": 1, "nw": 2, "sw": 3}  # camera position; build is rotated so camera stays SE
BG = (0, 0, 0, 0)


def _font(size: int = 11):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _shade(n: tuple[float, float, float]) -> float:
    # brighter from above, south a bit brighter than east, like vanilla's 1.0 / 0.8 / 0.6 / 0.5
    return max(0.45, min(1.0, 0.72 + 0.28 * n[1] + 0.1 * n[2] - 0.05 * n[0]))


def _affine(src: list[tuple[float, float]], dst: list[tuple[float, float]]):
    """Coefficients (a,b,c,d,e,f) so that src = M * dst (PIL's inverse mapping)."""
    (x0, y0), (x1, y1), (x2, y2) = dst
    (u0, v0), (u1, v1), (u2, v2) = src
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-9:
        return None
    a = ((u1 - u0) * (y2 - y0) - (u2 - u0) * (y1 - y0)) / det
    b = ((u2 - u0) * (x1 - x0) - (u1 - u0) * (x2 - x0)) / det
    d = ((v1 - v0) * (y2 - y0) - (v2 - v0) * (y1 - y0)) / det
    e = ((v2 - v0) * (x1 - x0) - (v1 - v0) * (x2 - x0)) / det
    return (a, b, u0 - a * x0 - b * y0, d, e, v0 - d * x0 - e * y0)


class FacePainter:
    """Rasterises faces into small sprites with a given projection; caches padded textures."""

    def __init__(self, palette: Palette):
        self.palette = palette
        self._padded: dict[str, Image.Image | None] = {}

    def padded(self, name: str | None) -> Image.Image | None:
        if name not in self._padded:
            tex = self.palette.texture(name)
            if tex is None:
                self._padded[name] = None
            else:
                n = tex.width
                pad = Image.new("RGBA", (n + 2, n + 2))
                pad.paste(tex.resize((n + 2, n + 2), Image.NEAREST), (0, 0))
                pad.paste(tex, (1, 1))
                self._padded[name] = pad
        return self._padded[name]

    def draw(self, canvas: Image.Image, f: Face, pts2d: list[tuple[float, float]], tint: float = 1.0) -> None:
        shade = (1.0 if f.bright else _shade(f.normal)) * tint
        tex = self.padded(f.tex)
        xs = [p[0] for p in pts2d]
        ys = [p[1] for p in pts2d]
        x0, y0 = math.floor(min(xs)), math.floor(min(ys))
        w, h = math.ceil(max(xs)) - x0 + 1, math.ceil(max(ys)) - y0 + 1
        if w <= 0 or h <= 0:
            return
        local = [(x - x0, y - y0) for x, y in pts2d]
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).polygon(local, fill=255)
        if tex is None:
            color = f.color or self.palette.texture_color(f.tex) or "#808080"
            rgb = tuple(int(int(color.lstrip("#")[i:i + 2], 16) * shade) for i in (0, 2, 4))
            patch = Image.new("RGBA", (w, h), rgb + (255,))
        else:
            n = tex.width - 2
            src = [(1 + u * n, 1 + v * n) for u, v in f.uvs[:3]]
            coeffs = _affine(src, local[:3])
            if coeffs is None:
                return
            patch = tex.transform((w, h), Image.AFFINE, coeffs, resample=Image.NEAREST)
            if shade < 0.999:
                r, g, b, a = patch.split()
                lut = [min(255, int(i * shade)) for i in range(256)]
                patch = Image.merge("RGBA", (r.point(lut), g.point(lut), b.point(lut), a))
        alpha = patch.getchannel("A")
        patch.putalpha(Image.composite(alpha, Image.new("L", (w, h), 0), mask))
        canvas.alpha_composite(patch, (x0, y0))


# ---- isometric -------------------------------------------------------------------------------
CAM = (1 / math.sqrt(3),) * 3


def _iso(scale: float) -> Callable[[tuple[float, float, float]], tuple[float, float]]:
    def p(pt):
        x, y, z = pt
        return ((x - z) * COS30 * scale, ((x + z) * 0.5 - y) * scale)
    return p


def _neighbour_fn(build: Build, pos):
    x, y, z = pos
    return lambda d: build.blocks.get((x + d[0], y + d[1], z + d[2]))


def _conn_key(build: Build, pos, block: Block, palette: Palette):
    info = palette.info(block.name, block.meta)
    if not info or info.render_type not in (11, 18, 32, 41) and "pane" not in block.name.lower():
        return None
    nb = _neighbour_fn(build, pos)
    return tuple(b.name if (b := nb(d)) else None for d in (N, S, W, E))


def _te_key(b: Block):
    return repr(sorted(b.te.items())) if b.te else None


def iso(build: Build, *, view: str = "se", scale: int = 16, palette: Palette | None = None,
        label: bool = True, frame: tuple | None = None) -> Image.Image:
    """Isometric render from the given compass side (camera above that corner).

    frame=(lo, hi) fixes the canvas to that box (build coordinates) instead of the build's bounds, so
    several builds rendered with the same frame line up pixel for pixel and can be composited."""
    palette = palette or build.palette
    turns = VIEWS[view]
    b = build.transformed(rotate=turns) if turns else build
    painter = FacePainter(palette)
    proj = _iso(scale)
    cw, ch = math.ceil(COS30 * scale) + 2, scale + 2
    sprites: dict = {}
    if frame is not None:
        pts = []
        for fx in (frame[0][0], frame[1][0]):
            for fz in (frame[0][2], frame[1][2]):
                x, z = fx, fz
                for _ in range(turns):
                    x, z = -z, x
                pts.append((x, z))
        lo = (min(p[0] for p in pts), frame[0][1], min(p[1] for p in pts))
        hi = (max(p[0] for p in pts), frame[1][1], max(p[1] for p in pts))
    else:
        lo, hi = b.bounds()
    corners = [proj((x, y, z)) for x in (lo[0], hi[0] + 1) for y in (lo[1], hi[1] + 1) for z in (lo[2], hi[2] + 1)]
    minx, miny = min(c[0] for c in corners), min(c[1] for c in corners)
    maxx, maxy = max(c[0] for c in corners), max(c[1] for c in corners)
    pad = 8
    top = 18 if label else 0
    canvas = Image.new("RGBA", (int(maxx - minx) + 2 * pad, int(maxy - miny) + 2 * pad + top), BG)
    order = sorted(b.blocks.items(), key=lambda kv: (kv[0][0] + kv[0][1] + kv[0][2], kv[0][1]))
    for pos, blk in order:
        x, y, z = pos
        if all(is_full_opaque(b.blocks.get(q), palette) for q in ((x + 1, y, z), (x, y + 1, z), (x, y, z + 1))):
            continue
        key = (blk.name, blk.meta, _te_key(blk), _conn_key(b, pos, blk, palette))
        sprite = sprites.get(key)
        if sprite is None:
            sprite = Image.new("RGBA", (2 * cw, 2 * ch), BG)
            faces = [f for f in faces_for(blk, palette, _neighbour_fn(b, pos))
                     if sum(f.normal[i] * CAM[i] for i in range(3)) > 1e-6]
            faces.sort(key=lambda f: sum(sum(p[i] for p in f.pts) / len(f.pts) * CAM[i] for i in range(3)))
            for f in faces:
                painter.draw(sprite, f, [(px + cw, py + ch) for px, py in map(proj, f.pts)])
            sprites[key] = sprite
        ox, oy = proj((x, y, z))
        canvas.alpha_composite(sprite, (int(round(ox - minx + pad - cw)), int(round(oy - miny + pad + top - ch))))
    if label:
        d = ImageDraw.Draw(canvas)
        sx, sy, sz = build.size()
        d.text((4, 2), f"from {view.upper()}  {sx}x{sy}x{sz}", fill=(230, 230, 230, 255), font=_font(12),
               stroke_width=2, stroke_fill=(0, 0, 0, 255))
    return canvas


def iso_sheet(build: Build, *, scale: int = 16, views=("se", "sw", "nw", "ne"), palette: Palette | None = None) -> Image.Image:
    imgs = [iso(build, view=v, scale=scale, palette=palette) for v in views]
    cols = 2 if len(imgs) > 1 else 1
    rows = math.ceil(len(imgs) / cols)
    w = max(i.width for i in imgs)
    h = max(i.height for i in imgs)
    sheet = Image.new("RGBA", (w * cols, h * rows), BG)
    for k, im in enumerate(imgs):
        sheet.alpha_composite(im, ((k % cols) * w, (k // cols) * h))
    return sheet


# ---- top-down slices -------------------------------------------------------------------------
_ARROW_DIRS = {N: (0, -1), S: (0, 1), E: (1, 0), W: (-1, 0)}


def block_direction(b: Block, palette: Palette):
    """Horizontal direction a block points (stairs: ascend side; furnace: front; etc.), if any."""
    from . import modblocks

    d = modblocks.direction(b)
    if d is not None:
        return d
    sch = scheme_for(b.name, b.meta, palette)
    if sch is None or sch.axis:
        return None
    v = sch.table.get(b.meta & sch.mask)
    return v if v in _ARROW_DIRS else None


def _arrow(draw: ImageDraw.ImageDraw, cx: float, cy: float, d, size: float) -> None:
    dx, dy = _ARROW_DIRS[d]
    tip = (cx + dx * size * 0.38, cy + dy * size * 0.38)
    tail = (cx - dx * size * 0.3, cy - dy * size * 0.3)
    draw.line([tail, tip], fill=(255, 255, 255, 230), width=max(1, int(size / 10)))
    px, py = -dy, dx
    wing = size * 0.18
    draw.polygon([tip, (tip[0] - dx * wing + px * wing, tip[1] - dy * wing + py * wing),
                  (tip[0] - dx * wing - px * wing, tip[1] - dy * wing - py * wing)], fill=(255, 255, 255, 230))


def slice_image(build: Build, y: int, *, cell: int = 16, palette: Palette | None = None, ghost: bool = True,
                arrows: bool = True) -> Image.Image:
    """Top-down view of layer y (north up, east right). The layer below is drawn dimmed."""
    palette = palette or build.palette
    lo, hi = build.bounds()
    w, l = hi[0] - lo[0] + 1, hi[2] - lo[2] + 1
    margin, top = 22, 16
    img = Image.new("RGBA", (w * cell + margin + 2, l * cell + margin + top + 2), (24, 24, 28, 255))
    painter = FacePainter(palette)
    ox, oy = margin, margin + top

    def draw_layer(yy: int, tint: float) -> None:
        cells = [(p, b) for p, b in build.blocks.items() if p[1] == yy]
        for (x, _, z), b in cells:
            faces = [f for f in faces_for(b, palette, _neighbour_fn(build, (x, yy, z))) if f.normal[1] > 1e-6]
            faces.sort(key=lambda f: sum(p[1] for p in f.pts) / len(f.pts))
            bx, bz = ox + (x - lo[0]) * cell, oy + (z - lo[2]) * cell
            for f in faces:
                painter.draw(img, f, [(bx + p[0] * cell, bz + p[2] * cell) for p in f.pts], tint)

    if ghost:
        draw_layer(y - 1, 0.35)
    draw_layer(y, 1.0)
    d = ImageDraw.Draw(img)
    font = _font(10)
    for i in range(w + 1):
        X = ox + i * cell
        d.line([(X, oy), (X, oy + l * cell)], fill=(255, 255, 255, 40))
        if i < w and (lo[0] + i) % 5 == 0:
            d.text((X + 1, oy - 12), str(lo[0] + i), fill=(200, 200, 200, 255), font=font)
    for j in range(l + 1):
        Z = oy + j * cell
        d.line([(ox, Z), (ox + w * cell, Z)], fill=(255, 255, 255, 40))
        if j < l and (lo[2] + j) % 5 == 0:
            d.text((2, Z + 1), str(lo[2] + j), fill=(200, 200, 200, 255), font=font)
    if arrows:
        for (x, yy, z), b in build.blocks.items():
            if yy != y:
                continue
            dvec = block_direction(b, palette)
            if dvec is not None:
                _arrow(d, ox + (x - lo[0] + 0.5) * cell, oy + (z - lo[2] + 0.5) * cell, dvec, cell)
    d.text((2, 1), f"y={y}  (x right/east, z down/south)", fill=(255, 255, 255, 255), font=_font(11))
    return img


def slices_sheet(build: Build, *, cell: int = 16, layers: list[int] | None = None, cols: int | None = None,
                 palette: Palette | None = None) -> Image.Image:
    lo, hi = build.bounds()
    ys = layers if layers is not None else list(range(lo[1], hi[1] + 1))
    imgs = [slice_image(build, y, cell=cell, palette=palette) for y in ys]
    cols = cols or min(len(imgs), max(1, int(math.ceil(math.sqrt(len(imgs))))))
    rows = math.ceil(len(imgs) / cols)
    w, h = imgs[0].width, imgs[0].height
    sheet = Image.new("RGBA", (cols * (w + 6), rows * (h + 6)), (10, 10, 12, 255))
    for k, im in enumerate(imgs):
        sheet.alpha_composite(im, ((k % cols) * (w + 6), (k // cols) * (h + 6)))
    return sheet


# ---- ASCII -----------------------------------------------------------------------------------
_GLYPHS = "#@%&*+=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$?!<>~^"


def describe(b: Block, palette: Palette) -> str:
    from . import modblocks
    from .lighting import emission

    info = palette.info(b.name, b.meta)
    name = info.name if info else b.name
    extra = modblocks.describe(b)
    light = emission(b, palette)
    suffix = f" (light {light})" if light else ""
    if info is None and extra:  # carrier blocks without an item row (ForgeMultipart:block)
        return extra + suffix
    parts = [f"{name} ({b.name}:{b.meta})"]
    if extra:
        parts.append(extra)
    d = block_direction(b, palette)
    if d is not None and not extra:
        if info and info.render_type == 10:
            parts.append(f"ascends {DIR_NAMES[d]}" + (" (upside-down)" if b.meta & 4 else ""))
        else:
            parts.append(f"facing {DIR_NAMES[d]}")
    elif info and "slab" in b.name.lower() and not extra:
        parts.append("top half" if b.meta & 8 else "bottom half")
    elif not extra and (sch := scheme_for(b.name, b.meta, palette)) is not None and sch.axis:
        axis = sch.table.get(b.meta & sch.mask)
        if axis is not None:
            parts.append("along " + "xyz"[[abs(c) for c in axis].index(1)])
    return " ".join(parts) + suffix


def ascii_layers(build: Build, layers: list[int] | None = None, palette: Palette | None = None) -> str:
    """Text map per layer, north at top, x increasing to the right; legend maps glyph -> block state."""
    palette = palette or build.palette
    lo, hi = build.bounds()
    states: dict = {}
    for b in build.blocks.values():
        key = (b.name, b.meta, _te_key(b))
        if key not in states:
            states[key] = (_GLYPHS[len(states)] if len(states) < len(_GLYPHS) else "?", b)
    out = []
    used = set()
    ys = layers if layers is not None else range(lo[1], hi[1] + 1)
    header = "".join(str(x % 10) for x in range(lo[0], hi[0] + 1))
    for y in ys:
        out.append(f"y={y}   x={lo[0]}..{hi[0]}")
        out.append(f"{'':>5} {header}")
        for z in range(lo[2], hi[2] + 1):
            row = []
            for x in range(lo[0], hi[0] + 1):
                b = build.blocks.get((x, y, z))
                glyph = states[(b.name, b.meta, _te_key(b))][0] if b else "."
                used.add(glyph)
                row.append(glyph)
            out.append(f"{z:>5} {''.join(row)}")
        out.append("")
    out.append("legend:")
    for glyph, b in states.values():
        if glyph in used:
            out.append(f"  {glyph}  {describe(b, palette)}")
    return "\n".join(out)
