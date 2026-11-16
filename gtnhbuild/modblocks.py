"""Tile-entity blocks: ArchitectureCraft shapes and Carpenter's Blocks.

Both store their look in tile-entity NBT; the block itself is a generic carrier. Sources (GTNH forks):
- ArchitectureCraft 1.12.19: TileShape/TileArchitecture NBT (`Shape`, `BaseName`, `BaseData`, `side`,
  `turn`, `Name2`/`Data2`), Shape enum, Matrix3.sideTurnRotations, RenderRoof slope geometry.
- Carpenter's Blocks 3.7.3-GTNH: TEBase NBT (`cbMetadata`, `cbAttrList` covers), data/Slope + Stairs ids.

Orientation model for ArchitectureCraft: world = M(side, turn) · local, M = sideRotations[side] · rotY(90·turn).
Shapes are authored "front" = local north (-z): a roof tile's slope faces its front (low edge there), and
every modelled shape has its back (the wall side: a balustrade's rail, a cornice's wall face) at local
south (+z). Model shapes are drawn from the mod's own .objson files in the ArchitectureCraft jar.
"""
from __future__ import annotations

import json
import os
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from . import microblocks, nbt
from .orient import DIR_NAMES, E, FORGE_DIRS, N, S, U, W, D, Vec, vec

if TYPE_CHECKING:
    from .build import Block
    from .geometry import Face
    from .palette import Palette

# =============================================================================================
# ArchitectureCraft
# =============================================================================================
AC_BLOCK = "ArchitectureCraft:shape"
AC_BLOCK_GLOW = "ArchitectureCraft:shapeSE"
AC_TE = "gcewing.shape"

# id: (constant, title, kind, symmetry, material used, items produced, occlusion mask)
SHAPES: dict[int, tuple[str, str, str, str, int, int, int]] = {
    0: ("RoofTile", "Roof Tile", "Roof", "Bilateral", 1, 2, 0xcf),
    1: ("RoofOuterCorner", "Roof Outer Corner", "Roof", "Unilateral", 1, 3, 0x4f),
    2: ("RoofInnerCorner", "Roof Inner Corner", "Roof", "Unilateral", 2, 3, 0xdf),
    3: ("RoofRidge", "Gabled Roof Ridge", "Roof", "Bilateral", 1, 4, 0x0f),
    4: ("RoofSmartRidge", "Hip Roof Ridge", "Roof", "Quadrilateral", 1, 2, 0x0f),
    5: ("RoofValley", "Gabled Roof Valley", "Roof", "Bilateral", 1, 2, 0xff),
    6: ("RoofSmartValley", "Hip Roof Valley", "Roof", "Quadrilateral", 1, 1, 0xff),
    7: ("RoofOverhang", "Roof Overhang", "Model", "Bilateral", 1, 2, 0xcf),
    8: ("RoofOverhangOuterCorner", "Roof Overhang Outer Corner", "Model", "Unilateral", 1, 3, 0x4f),
    9: ("RoofOverhangInnerCorner", "Roof Overhang Inner Corner", "Model", "Unilateral", 2, 3, 0xdf),
    10: ("Cylinder", "Cylinder", "Model", "Quadrilateral", 1, 1, 0xff),
    11: ("CylinderHalf", "Half Cylinder", "Model", "Bilateral", 1, 1, 0xcc),
    12: ("CylinderQuarter", "Quarter Cylinder", "Model", "Unilateral", 1, 1, 0x44),
    13: ("CylinderLargeQuarter", "Round Outer Corner", "Model", "Unilateral", 1, 1, 0xff),
    14: ("AnticylinderLargeQuarter", "Round Inner Corner", "Model", "Unilateral", 1, 2, 0xdd),
    15: ("Pillar", "Round Pillar", "Model", "Quadrilateral", 1, 1, 0x106),
    16: ("Post", "Round Post", "Model", "Quadrilateral", 1, 4, 0x104),
    17: ("Pole", "Round Pole", "Model", "Quadrilateral", 1, 16, 0x102),
    18: ("BevelledOuterCorner", "Bevelled Outer Corner", "Model", "Unilateral", 1, 3, 0x4f),
    19: ("BevelledInnerCorner", "Bevelled Inner Corner", "Model", "Unilateral", 1, 1, 0xdf),
    20: ("PillarBase", "Round Pillar Base", "Model", "Quadrilateral", 1, 1, 0xff),
    21: ("DoricCapital", "Doric Capital", "Model", "Quadrilateral", 1, 1, 0xff),
    22: ("IonicCapital", "Ionic capital", "Model", "Bilateral", 1, 1, 0xff),
    23: ("CorinthianCapital", "Corinthian capital", "Model", "Quadrilateral", 1, 1, 0xff),
    24: ("DoricTriglyph", "Triglyph", "Model", "Bilateral", 1, 1, 0xff),
    25: ("DoricTriglyphCorner", "Triglyph Corner", "Model", "Bilateral", 1, 1, 0xff),
    26: ("DoricMetope", "Metope", "Model", "Bilateral", 1, 1, 0xff),
    27: ("Architrave", "Architrave", "Model", "Bilateral", 1, 1, 0xff),
    28: ("ArchitraveCorner", "Architrave Corner", "Model", "Unilateral", 1, 1, 0xff),
    30: ("WindowFrame", "Window Frame", "Window", "Bilateral", 1, 4, 0x202),
    31: ("WindowCorner", "Window Corner", "Window", "Unilateral", 1, 2, 0x202),
    32: ("WindowMullion", "Window Mullion", "Window", "Bilateral", 1, 2, 0x202),
    33: ("SphereFull", "Sphere", "Model", "Quadrilateral", 1, 1, 0xff),
    34: ("SphereHalf", "Hemisphere", "Model", "Quadrilateral", 1, 2, 0x0f),
    35: ("SphereQuarter", "Quarter Sphere", "Model", "Bilateral", 1, 4, 0x0c),
    36: ("SphereEighth", "Quarter Hemisphere", "Model", "Unilateral", 1, 8, 0x04),
    37: ("SphereEighthLarge", "Round Outer Corner Cap", "Model", "Unilateral", 1, 1, 0xff),
    38: ("SphereEighthLargeRev", "Round Inner Corner Cap", "Model", "Unilateral", 1, 1, 0xdf),
    40: ("RoofOverhangGableLH", "Gable Overhang LH", "Model", "Bilateral", 1, 4, 0x48),
    41: ("RoofOverhangGableRH", "Gable Overhang RH", "Model", "Bilateral", 1, 4, 0x84),
    42: ("RoofOverhangGableEndLH", "Gable Overhang LH End", "Model", "Bilateral", 1, 4, 0x48),
    43: ("RoofOverhangGableEndRH", "Gable Overhang RH End", "Model", "Bilateral", 1, 4, 0x48),
    44: ("RoofOverhangRidge", "Ridge Overhang", "Model", "Bilateral", 1, 4, 0x0c),
    45: ("RoofOverhangValley", "Valley Overhang", "Model", "Bilateral", 1, 4, 0xcc),
    50: ("CorniceLH", "Cornice LH", "Model", "Bilateral", 1, 4, 0x48),
    51: ("CorniceRH", "Cornice RH", "Model", "Bilateral", 1, 4, 0x84),
    52: ("CorniceEndLH", "Cornice LH End", "Model", "Bilateral", 1, 4, 0x48),
    53: ("CorniceEndRH", "Cornice RH End", "Model", "Bilateral", 1, 4, 0x48),
    54: ("CorniceRidge", "Cornice Ridge", "Model", "Bilateral", 1, 4, 0x0c),
    55: ("CorniceValley", "Cornice Valley", "Model", "Bilateral", 1, 4, 0xcc),
    56: ("CorniceBottom", "Cornice Bottom", "Model", "Bilateral", 1, 4, 0x0c),
    60: ("CladdingSheet", "Cladding", "Model", "None", 1, 1, 0x0c),
    61: ("ArchD1", "Arch Diameter 1", "Model", "Bilateral", 1, 1, 0xff),
    62: ("ArchD2", "Arch Diameter 2", "Model", "Bilateral", 1, 2, 0xfc),
    63: ("ArchD3A", "Arch Diameter 3 Part A", "Model", "Bilateral", 1, 2, 0xcc),
    64: ("ArchD3B", "Arch Diameter 3 Part B", "Model", "Bilateral", 1, 1, 0xfc),
    65: ("ArchD3C", "Arch Diameter 3 Part C", "Model", "Bilateral", 1, 1, 0xff),
    66: ("ArchD4A", "Arch Diameter 4 Part A", "Model", "Bilateral", 1, 2, 0xcc),
    67: ("ArchD4B", "Arch Diameter 4 Part B", "Model", "Bilateral", 1, 1, 0xfc),
    68: ("ArchD4C", "Arch Diameter 4 Part C", "Model", "Bilateral", 1, 2, 0x0),
    70: ("BanisterPlainBottom", "Plain Banister Bottom Transition", "Banister", "Bilateral", 1, 10, 0x0),
    71: ("BanisterPlain", "Plain Banister", "Banister", "Bilateral", 1, 10, 0x0),
    72: ("BanisterPlainTop", "Plain Banister Top Transition", "Banister", "Bilateral", 1, 10, 0x0),
    73: ("BalustradeFancy", "Fancy Balustrade", "Model", "Bilateral", 1, 5, 0x0),
    74: ("BalustradeFancyCorner", "Fancy Corner Balustrade", "Model", "Unilateral", 1, 2, 0x0),
    75: ("BalustradeFancyWithNewel", "Fancy Balustrade with Newel", "Model", "Bilateral", 1, 3, 0x0),
    76: ("BalustradeFancyNewel", "Fancy Newel", "Model", "Unilateral", 1, 4, 0x0),
    77: ("BalustradePlain", "Plain Balustrade", "Model", "Bilateral", 1, 10, 0x0),
    78: ("BalustradePlainOuterCorner", "Plain Outer Corner Balustrade", "Model", "Unilateral", 1, 4, 0x0),
    79: ("BalustradePlainWithNewel", "Plain Balustrade with Newel", "Model", "Bilateral", 1, 6, 0x0),
    80: ("BanisterPlainEnd", "Plain Banister End", "Banister", "Bilateral", 1, 8, 0x0),
    81: ("BanisterFancyNewelTall", "Tall Fancy Newel", "Model", "Unilateral", 1, 2, 0x0),
    82: ("BalustradePlainInnerCorner", "Plain Inner Corner Balustrade", "Model", "Unilateral", 1, 8, 0x0),
    83: ("BalustradePlainEnd", "Plain Balustrade End", "Banister", "Bilateral", 1, 8, 0x0),
    84: ("BanisterFancyBottom", "Fancy Banister Bottom Transition", "Banister", "Bilateral", 1, 5, 0x0),
    85: ("BanisterFancy", "Fancy Banister", "Banister", "Bilateral", 1, 5, 0x0),
    86: ("BanisterFancyTop", "Fancy Banister Top Transition", "Banister", "Bilateral", 1, 5, 0x0),
    87: ("BanisterFancyEnd", "Fancy Banister End", "Banister", "Bilateral", 1, 2, 0x0),
    88: ("BanisterPlainInnerCorner", "Plain Banister Inner Corner", "Model", "Unilateral", 1, 6, 0x0),
    90: ("Slab", "Slab", "Model", "Quadrilateral", 1, 2, 0x0f),
    91: ("Stairs", "Stairs", "Model", "Bilateral", 3, 4, 0xcf),
    92: ("StairsOuterCorner", "Stairs Outer Corner", "Model", "Unilateral", 2, 3, 0x4f),
    93: ("StairsInnerCorner", "Stairs Inner Corner", "Model", "Unilateral", 1, 1, 0xdf),
    94: ("SlopeTileA1", "Slope A Start", "Roof", "Bilateral", 1, 1, 0xcf),
    95: ("SlopeTileA2", "Slope A End", "Roof", "Bilateral", 1, 3, 0x0f),
    96: ("SlopeTileB1", "Slope B Start", "Roof", "Bilateral", 1, 1, 0xff),
    97: ("SlopeTileB2", "Slope B Middle", "Roof", "Bilateral", 1, 2, 0xcf),
    98: ("SlopeTileB3", "Slope B End", "Roof", "Bilateral", 1, 3, 0x0f),
    99: ("SlopeTileC1", "Slope C 1", "Roof", "Bilateral", 1, 1, 0xff),
    100: ("SlopeTileC2", "Slope C 2", "Roof", "Bilateral", 1, 2, 0xcf),
    101: ("SlopeTileC3", "Slope C 3", "Roof", "Bilateral", 1, 3, 0x0f),
    102: ("SlopeTileC4", "Slope C 4", "Roof", "Bilateral", 1, 4, 0x0f),
    112: ("RoofTileSE", "Roof Tile(Glow)", "Roof", "Bilateral", 1, 2, 0xcf),
    113: ("SquareSE", "Square(Glow)", "Model", "Quadrilateral", 1, 1, 0xff),
    114: ("SlabSE", "Slab(Glow)", "Model", "Quadrilateral", 1, 2, 0x0f),
    115: ("AngledRoofRidge", "Angled Roof Ridge", "Model", "Bilateral", 1, 4, 0x0f),
    116: ("DoubleRoofTile", "Double Roof Tile", "Model", "Bilateral", 1, 2, 0xcf),
}

# Shapes the mod draws from assets/architecturecraft/models/shape/<name>.objson (Shape.java Model(...) /
# Banister(...)); roofs and windows are procedural and stay approximated in geometry below.
AC_MODELS: dict[int, str] = {
    7: "roof_overhang", 8: "roof_overhang_outer_corner", 9: "roof_overhang_inner_corner",
    10: "cylinder_full_r8h16", 11: "cylinder_half_r8h16", 12: "cylinder_quarter_r8h16",
    13: "cylinder_quarter_r16h16", 14: "round_inner_corner", 15: "cylinder_r6h16", 16: "cylinder_r4h16",
    17: "cylinder_r2h16", 18: "bevelled_outer_corner", 19: "bevelled_inner_corner", 20: "pillar_base",
    21: "doric_capital", 22: "ionic_capital", 23: "corinthian_capital", 24: "doric_triglyph",
    25: "doric_triglyph_corner", 26: "doric_metope", 27: "architrave", 28: "architrave_corner",
    33: "sphere_full_r8", 34: "sphere_half_r8", 35: "sphere_quarter_r8", 36: "sphere_eighth_r8",
    37: "sphere_eighth_r16", 38: "sphere_eighth_r16_rev", 40: "roof_overhang_gable_lh",
    41: "roof_overhang_gable_rh", 42: "roof_overhang_gable_end_lh", 43: "roof_overhang_gable_end_rh",
    44: "roof_overhang_gable_ridge", 45: "roof_overhang_gable_valley", 50: "cornice_lh", 51: "cornice_rh",
    52: "cornice_end_lh", 53: "cornice_end_rh", 54: "cornice_ridge", 55: "cornice_valley",
    56: "cornice_bottom", 60: "cladding", 61: "arch_d1", 62: "arch_d2", 63: "arch_d3a", 64: "arch_d3b",
    65: "arch_d3c", 66: "arch_d4a", 67: "arch_d4b", 68: "arch_d4c", 70: "balustrade_stair_plain_bottom",
    71: "balustrade_stair_plain", 72: "balustrade_stair_plain_top", 73: "balustrade_fancy",
    74: "balustrade_fancy_corner", 75: "balustrade_fancy_with_newel", 76: "balustrade_fancy_newel",
    77: "balustrade_plain", 78: "balustrade_plain_outer_corner", 79: "balustrade_plain_with_newel",
    80: "balustrade_stair_plain_end", 81: "balustrade_fancy_newel_tall", 82: "balustrade_plain_inner_corner",
    83: "balustrade_plain_end", 84: "balustrade_stair_fancy_bottom", 85: "balustrade_stair_fancy",
    86: "balustrade_stair_fancy_top", 87: "balustrade_stair_fancy_end",
    88: "balustrade_stair_plain_inner_corner", 90: "slab", 91: "stairs", 92: "stairs_outer_corner",
    93: "stairs_inner_corner", 113: "square", 114: "slab", 115: "angled_roof_ridge", 116: "double_roof_tile",
}
_INSTANCE_MODS = Path("/var/mnt/mercury/Minecraft/Instances/GTNH Threshold/.minecraft/mods")


@lru_cache(maxsize=1)
def ac_jar() -> Path | None:
    """The ArchitectureCraft jar the models are read from: GTNH_AC_JAR, else the Threshold instance's.
    Without it, model shapes preview as their collision boxes."""
    env = os.environ.get("GTNH_AC_JAR")
    if env:
        return Path(env)
    jars = sorted(_INSTANCE_MODS.glob("ArchitectureCraft-*.jar")) if _INSTANCE_MODS.is_dir() else []
    return jars[-1] if jars else None


@lru_cache(maxsize=None)
def model_triangles(name: str) -> tuple[tuple[tuple[float, float, float], ...], ...] | None:
    """Triangles of a shape model in local block coordinates (0..1, back toward +z), outward
    counter-clockwise; degenerate triangles dropped. None when the jar is unavailable."""
    jar = ac_jar()
    if jar is None or not jar.exists():
        return None
    with zipfile.ZipFile(jar) as z:
        model = json.loads(z.read(f"assets/architecturecraft/models/shape/{name}.objson"))
    out = []
    for f in model["faces"]:
        pts = [(v[0] + 0.5, v[1] + 0.5, v[2] + 0.5) for v in f["vertices"]]
        for i, j, k in f["triangles"]:
            a, b, c = pts[i], pts[j], pts[k]
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if n[0] ** 2 + n[1] ** 2 + n[2] ** 2 > 1e-12:
                out.append((a, b, c))
    return tuple(out)


_SHAPE_BY_NAME = {}
for _i, _s in SHAPES.items():
    _SHAPE_BY_NAME[_s[0].lower()] = _i
    _SHAPE_BY_NAME[_s[1].lower()] = _i


def shape_id(shape: int | str) -> int:
    if isinstance(shape, int):
        if shape not in SHAPES:
            raise KeyError(f"unknown ArchitectureCraft shape id {shape}")
        return shape
    key = shape.lower()
    if key not in _SHAPE_BY_NAME:
        raise KeyError(f"unknown ArchitectureCraft shape {shape!r}; see modblocks.SHAPES")
    return _SHAPE_BY_NAME[key]


# ---- orientation matrices --------------------------------------------------------------------
Mat = tuple[tuple[int, int, int], ...]


def _mul(a: Mat, b: Mat) -> Mat:
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _rot(deg: int, i: int, j: int) -> Mat:
    c = {0: 1, 90: 0, 180: -1, 270: 0, -90: 0}[deg]
    s = {0: 0, 90: 1, 180: 0, 270: -1, -90: -1}[deg]
    r = [[1 if a == b else 0 for b in range(3)] for a in range(3)]
    r[i][i], r[i][j], r[j][i], r[j][j] = c, -s, s, c
    return tuple(tuple(row) for row in r)


_I: Mat = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
_SIDE_ROT: tuple[Mat, ...] = (
    _I, _rot(180, 1, 2), _rot(90, 1, 2), _mul(_rot(-90, 1, 2), _rot(180, 2, 0)),
    _mul(_rot(-90, 0, 1), _rot(90, 2, 0)), _mul(_rot(90, 0, 1), _rot(-90, 2, 0)))


@lru_cache(maxsize=None)
def ac_matrix(side: int, turn: int) -> Mat:
    """Local -> world rotation (Matrix3.sideTurnRotations[side][turn])."""
    return _mul(_SIDE_ROT[side], _rot(90 * (turn % 4), 2, 0))


def _apply(m: Mat, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def ac_orientation(front: str | Vec = "n", up: str | Vec = "u") -> tuple[int, int]:
    """(side, turn) that points the shape's local north ("front") and local up as given.

    Roof tile: front = the side the slope faces (its low edge). Corners: front and front-rotated-
    clockwise are the two sloped sides (outer corner at front=n slopes north and east, peak in the
    south-west). up='d' places it upside down (ceiling / underside)."""
    f, u = vec(front), vec(up)
    for side in range(6):
        for turn in range(4):
            m = ac_matrix(side, turn)
            if _apply(m, (0, 0, -1)) == f and _apply(m, (0, 1, 0)) == u:
                return side, turn
    raise ValueError(f"front {front!r} must be perpendicular to up {up!r}")


def ac_shape(shape: int | str, material: "Block", *, front: str | Vec = "n", up: str | Vec = "u",
             secondary: "Block | None" = None, glow: bool = False) -> "Block":
    """An ArchitectureCraft shape block made of `material` (any block; BaseName = its registry name).
    `secondary`: window glass pane (windows) or cladding block (roofs)."""
    from .build import Block

    sid = shape_id(shape)
    side, turn = ac_orientation(front, up)
    te = {"id": AC_TE, "Shape": nbt.Int(sid), "BaseName": material.name, "BaseData": nbt.Int(material.meta),
          "side": nbt.Byte(side), "turn": nbt.Byte(turn)}
    if secondary is not None:
        te["Name2"], te["Data2"] = secondary.name, nbt.Int(secondary.meta)
    return Block(AC_BLOCK_GLOW if glow else AC_BLOCK, 0, te)


def _ac_fields(b: "Block"):
    te = b.te
    return (te["Shape"].v, te.get("BaseName", "minecraft:planks"), te.get("BaseData", nbt.Int(0)).v,
            te.get("side", nbt.Byte(0)).v, te.get("turn", nbt.Byte(0)).v)


# =============================================================================================
# Carpenter's Blocks
# =============================================================================================
CB_PREFIX = "CarpentersBlocks:"
CB_TE = "TileEntityCarpentersBlock"
CB_TE_IDS = {"blockCarpentersTorch": "TileEntityCarpentersTorch", "blockCarpentersSafe": "TileEntityCarpentersSafe",
             "blockCarpentersFlowerPot": "TileEntityCarpentersFlowerPot",
             "blockCarpentersGarageDoor": "TileEntityCarpentersGarageDoor",
             "blockCarpentersDaylightSensor": "TileEntityCarpentersDaylightSensor"}

# Slope ids (data/Slope.java): (type, facings). Facings name where the sloped surface faces; a
# POS wedge facing N has its low edge north and full south/bottom faces (player facing north places 9).
_F = {"N": N, "S": S, "E": E, "W": W, "UP": U, "DOWN": D}
_SLOPE_ROWS = """0 WEDGE_SIDE S,E|1 WEDGE_SIDE N,W|2 WEDGE_SIDE N,E|3 WEDGE_SIDE S,W|4 WEDGE DOWN,N|5 WEDGE DOWN,S|
6 WEDGE DOWN,W|7 WEDGE DOWN,E|8 WEDGE UP,N|9 WEDGE UP,S|10 WEDGE UP,W|11 WEDGE UP,E|12 WEDGE_INT DOWN,S,E|
13 WEDGE_INT DOWN,N,W|14 WEDGE_INT DOWN,N,E|15 WEDGE_INT DOWN,S,W|16 WEDGE_INT UP,S,E|17 WEDGE_INT UP,N,W|
18 WEDGE_INT UP,N,E|19 WEDGE_INT UP,S,W|20 WEDGE_EXT DOWN,S,E|21 WEDGE_EXT DOWN,N,W|22 WEDGE_EXT DOWN,N,E|
23 WEDGE_EXT DOWN,S,W|24 WEDGE_EXT UP,S,E|25 WEDGE_EXT UP,N,W|26 WEDGE_EXT UP,N,E|27 WEDGE_EXT UP,S,W|
28 OBLIQUE_INT DOWN,S,E|29 OBLIQUE_INT DOWN,N,W|30 OBLIQUE_INT DOWN,N,E|31 OBLIQUE_INT DOWN,S,W|
32 OBLIQUE_INT UP,S,E|33 OBLIQUE_INT UP,N,W|34 OBLIQUE_INT UP,N,E|35 OBLIQUE_INT UP,S,W|36 OBLIQUE_EXT DOWN,S,E|
37 OBLIQUE_EXT DOWN,N,W|38 OBLIQUE_EXT DOWN,N,E|39 OBLIQUE_EXT DOWN,S,W|40 OBLIQUE_EXT UP,S,E|
41 OBLIQUE_EXT UP,N,W|42 OBLIQUE_EXT UP,N,E|43 OBLIQUE_EXT UP,S,W|44 PRISM DOWN|45 PRISM UP|46 PRISM_1P UP,N|
47 PRISM_1P UP,S|48 PRISM_1P UP,W|49 PRISM_1P UP,E|50 PRISM_2P UP,N,S|51 PRISM_2P UP,W,E|52 PRISM_2P UP,S,E|
53 PRISM_2P UP,N,W|54 PRISM_2P UP,N,E|55 PRISM_2P UP,S,W|56 PRISM_3P UP,N,W,E|57 PRISM_3P UP,S,W,E|
58 PRISM_3P UP,N,S,W|59 PRISM_3P UP,N,S,E|60 PRISM_4P UP,N,S,W,E|61 PRISM_WEDGE UP,N|62 PRISM_WEDGE UP,S|
63 PRISM_WEDGE UP,W|64 PRISM_WEDGE UP,E"""
SLOPES: dict[int, tuple[str, frozenset]] = {}
for _row in _SLOPE_ROWS.replace("\n", "").split("|"):
    _id, _type, _facings = _row.split()
    SLOPES[int(_id)] = (_type, frozenset(_F[f] for f in _facings.split(",")))

# Stairs ids (data/Stairs.java): same naming. NORMAL POS_N (8) has its tall half south (StairsUtil).
_STAIRS_ROWS = ("0 NORMAL_SIDE S,E|1 NORMAL_SIDE N,W|2 NORMAL_SIDE N,E|3 NORMAL_SIDE S,W|4 NORMAL DOWN,N|"
                "5 NORMAL DOWN,S|6 NORMAL DOWN,W|7 NORMAL DOWN,E|8 NORMAL UP,N|9 NORMAL UP,S|10 NORMAL UP,W|"
                "11 NORMAL UP,E|12 INT DOWN,S,E|13 INT DOWN,N,W|14 INT DOWN,N,E|15 INT DOWN,S,W|16 INT UP,S,E|"
                "17 INT UP,N,W|18 INT UP,N,E|19 INT UP,S,W|20 EXT DOWN,S,E|21 EXT DOWN,N,W|22 EXT DOWN,N,E|"
                "23 EXT DOWN,S,W|24 EXT UP,S,E|25 EXT UP,N,W|26 EXT UP,N,E|27 EXT UP,S,W")
CB_STAIRS: dict[int, tuple[str, frozenset]] = {}
for _row in _STAIRS_ROWS.split("|"):
    _id, _type, _facings = _row.split()
    CB_STAIRS[int(_id)] = (_type, frozenset(_F[f] for f in _facings.split(",")))


def _find(table: dict, kind: str, facings: frozenset) -> int:
    for i, (t, f) in table.items():
        if t == kind and f == facings:
            return i
    raise ValueError(f"no {kind} with facings {sorted(DIR_NAMES[d] for d in facings)}")


def _cover_attr(cover: "Block", attr: int = 6) -> dict:
    # No numeric item "id": ItemStack.loadItemStackFromNBT then yields null and Carpenter's Attribute
    # resolves the cover by cbUniqueId, which works in any world (numeric ids are per-world).
    return {"Count": nbt.Byte(1), "Damage": nbt.Short(cover.meta), "cbUniqueId": cover.name,
            "cbAttribute": nbt.Byte(attr)}


def carpenters(kind: str, cover: "Block | None", data: int = 0) -> "Block":
    """Raw Carpenter's block: kind = registry suffix ('blockCarpentersSlope', 'Slope', ...),
    data = cbMetadata. The block meta mirrors the cover's damage, as TEBase.addAttribute does."""
    from .build import Block

    reg = kind if kind.startswith("blockCarpenters") else f"blockCarpenters{kind}"
    te = {"id": CB_TE_IDS.get(reg, CB_TE), "cbMetadata": nbt.Int(data),
          "cbAttrList": nbt.List(nbt.COMPOUND, [_cover_attr(cover)] if cover else []),
          "cbDesign": "", "cbOwner": ""}
    return Block(CB_PREFIX + reg, cover.meta & 15 if cover else 0, te)


def cb_block(cover: "Block", slab: str | None = None) -> "Block":
    """Carpenter's Block, full or as a slab: slab = 'down'/'up'/'north'/... = the half it fills."""
    half = {None: 0, "w": 1, "west": 1, "e": 2, "east": 2, "d": 3, "down": 3, "u": 4, "up": 4,
            "n": 5, "north": 5, "s": 6, "south": 6}[slab]
    return carpenters("Block", cover, half)


def cb_slope(cover: "Block", faces: str = "n", kind: str = "wedge", upside_down: bool = False) -> "Block":
    """Carpenter's Slope. `faces`: horizontal direction(s) the sloped surface faces, e.g. 'n' or 'ne'.
    kind: wedge (1 dir), wedge_int / wedge_ext / oblique_int / oblique_ext (2 dirs), wedge_side
    (vertical diagonal; 2 dirs, upside_down ignored), prism_wedge (1 dir).
    A 'wedge' facing n is a ramp rising toward the south (low edge north)."""
    dirs = frozenset(vec(c) for c in faces.replace(",", "")) if len(faces) <= 2 else frozenset({vec(faces)})
    k = kind.upper()
    if k != "WEDGE_SIDE":
        dirs = dirs | {D if upside_down else U}
    return carpenters("Slope", cover, _find(SLOPES, k, dirs))


def cb_stairs(cover: "Block", faces: str = "n", kind: str = "normal", upside_down: bool = False) -> "Block":
    """Carpenter's Stairs. A normal stair 'facing' n has its low step north and tall half south — you
    walk up toward the south (like a vanilla stair placed by a player facing south)."""
    dirs = frozenset(vec(c) for c in faces) if len(faces) <= 2 else frozenset({vec(faces)})
    k = kind.upper()
    if k != "NORMAL_SIDE":
        dirs = dirs | {D if upside_down else U}
    return carpenters("Stairs", cover, _find(CB_STAIRS, k, dirs))


def _cb_cover(b: "Block") -> tuple[str, int] | None:
    for attr in b.te.get("cbAttrList", nbt.List(nbt.COMPOUND)).items:
        if attr.get("cbAttribute", nbt.Byte(-1)).v == 6:
            return attr.get("cbUniqueId", "minecraft:planks"), attr.get("Damage", nbt.Short(0)).v
    return None


# =============================================================================================
# hooks used by build / orient / render
# =============================================================================================
def is_ac(b: "Block") -> bool:
    return b.te is not None and b.te.get("id") == AC_TE


def is_cb(b: "Block") -> bool:
    return b.te is not None and b.name.startswith(CB_PREFIX)


def material_of(b: "Block") -> tuple[str, int] | None:
    """The block an ArchitectureCraft shape is made of / a Carpenter's block is covered with."""
    if is_ac(b):
        _, base, data, _, _ = _ac_fields(b)
        return base, data
    if is_cb(b):
        return _cb_cover(b)
    return None


def describe(b: "Block", orientation: bool = True) -> str | None:
    """Short label for legends (and, without orientation, for BOM grouping); None for plain blocks."""
    if microblocks.is_fmp(b):
        return microblocks.describe(b, orientation)
    if is_ac(b):
        sid, base, data, side, turn = _ac_fields(b)
        label = f"{SHAPES.get(sid, ('?', f'shape {sid}'))[1]} of {base}:{data}"
        if not orientation:
            return label
        m = ac_matrix(side, turn)
        front = DIR_NAMES.get(_apply(m, (0, 0, -1)), "?")
        up = "" if _apply(m, (0, 1, 0)) == U else f" up={DIR_NAMES.get(_apply(m, (0, 1, 0)), '?')}"
        return f"{label} front={front}{up}"
    if is_cb(b):
        kind = b.name[len(CB_PREFIX) + len("blockCarpenters"):]
        cover = _cb_cover(b)
        data = b.te.get("cbMetadata", nbt.Int(0)).v
        detail = ""
        table = SLOPES if kind == "Slope" else CB_STAIRS if kind == "Stairs" else None
        if table and data in table:
            t, f = table[data]
            detail = f" {t.lower()}" + (f" faces {'+'.join(DIR_NAMES[d] for d in sorted(f))}" if orientation else "")
        elif data and orientation:
            detail = f" data={data}"
        return f"{kind}{detail} cover={cover[0]}:{cover[1]}" if cover else f"{kind}{detail}"
    return None


def direction(b: "Block") -> Vec | None:
    """Horizontal direction for slice arrows: the side a slope/roof descends toward."""
    if is_ac(b):
        sid, _, _, side, turn = _ac_fields(b)
        d = _apply(ac_matrix(side, turn), (0, 0, -1))
        return d if d in (N, S, E, W) else None
    if is_cb(b):
        data = b.te.get("cbMetadata", nbt.Int(0)).v
        table = SLOPES if b.name.endswith("Slope") else CB_STAIRS if b.name.endswith("Stairs") else None
        if table and data in table and table[data][0] in ("WEDGE", "NORMAL", "PRISM_WEDGE"):
            hz = [d for d in table[data][1] if d in (N, S, E, W)]
            return hz[0] if hz else None
    return None


def transform_te(b: "Block", f: Callable[[Vec], Vec]) -> "Block | None":
    """Rotate/mirror a tile-entity block; None if this module does not handle it."""
    from .build import Block

    if microblocks.is_fmp(b):
        return microblocks.transform(b, f)

    if is_ac(b):
        sid, _, _, side, turn = _ac_fields(b)
        r = tuple(tuple(c) for c in zip(*(f(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))))  # columns
        target = _mul(r, ac_matrix(side, turn))
        det = sum(r[0][i] * (r[1][(i + 1) % 3] * r[2][(i + 2) % 3] - r[1][(i + 2) % 3] * r[2][(i + 1) % 3])
                  for i in range(3))
        if det < 0:  # reflection: compose with the shape's own mirror symmetry
            sym = SHAPES.get(sid, ("", "", "", "Bilateral"))[3]
            if sym == "None":
                return b
            s = ((0, 0, -1), (0, 1, 0), (-1, 0, 0)) if sym == "Unilateral" else ((-1, 0, 0), (0, 1, 0), (0, 0, 1))
            target = _mul(target, s)
        for ns in range(6):
            for nt in range(4):
                if ac_matrix(ns, nt) == target:
                    te = dict(b.te)
                    te["side"], te["turn"] = nbt.Byte(ns), nbt.Byte(nt)
                    if "Disconnected" in te:
                        bits = te["Disconnected"].v
                        out = 0
                        for i, d in enumerate(FORGE_DIRS):
                            if bits & (1 << i):
                                out |= 1 << FORGE_DIRS.index(f(d))
                        te["Disconnected"] = nbt.Int(out)
                    return Block(b.name, b.meta, te)
        return b
    if is_cb(b):
        data = b.te.get("cbMetadata", nbt.Int(0)).v
        table = SLOPES if b.name.endswith("Slope") else CB_STAIRS if b.name.endswith("Stairs") else None
        te = dict(b.te)
        if table and data in table:
            kind, facings = table[data]
            te["cbMetadata"] = nbt.Int(_find(table, kind, frozenset(f(d) for d in facings)))
        elif b.name.endswith(("Torch", "Ladder")) and (data & 7) >= 2:
            te["cbMetadata"] = nbt.Int((data & ~7) | FORGE_DIRS.index(f(FORGE_DIRS[data & 7])))
        elif b.name.endswith("Block") and 1 <= data <= 6:
            halves = {1: W, 2: E, 3: D, 4: U, 5: N, 6: S}
            back = {v: k for k, v in halves.items()}
            te["cbMetadata"] = nbt.Int(back[f(halves[data])])
        return Block(b.name, b.meta, te)
    return None


# ---- geometry --------------------------------------------------------------------------------
def _textured(palette: "Palette", base: str, data: int):
    tex = palette.face_textures(base, data)
    return lambda normal: tex[_dominant_side(normal)]


def _dominant_side(n) -> int:
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 1:
        return 1 if n[1] > 0 else 0
    if ax == 2:
        return 3 if n[2] > 0 else 2
    return 5 if n[0] > 0 else 4


def _auto_uv(p, side: int):
    x, y, z = p
    if side in (0, 1):
        return (x, z)
    if side == 2:
        return (1 - x, 1 - y)
    if side == 3:
        return (x, 1 - y)
    if side == 4:
        return (z, 1 - y)
    return (1 - z, 1 - y)


def _poly(pts, texfn) -> "Face":
    from .geometry import face, normal_of

    n = normal_of(tuple(tuple(float(c) for c in p) for p in pts))
    side = _dominant_side(n)
    return face(pts, [_auto_uv(p, side) for p in pts], texfn(n))


def heightfield(h: dict[str, float], split: str, texfn) -> list["Face"]:
    """Solid under a top surface through corner heights h['nw'|'ne'|'sw'|'se'] (0..1), the top
    split into two triangles along diagonal `split` ('nw-se' or 'ne-sw')."""
    c = {"nw": (0, 0), "ne": (1, 0), "sw": (0, 1), "se": (1, 1)}
    P = {k: (c[k][0], h[k], c[k][1]) for k in c}
    B = {k: (c[k][0], 0, c[k][1]) for k in c}
    out = [_poly((B["sw"], B["nw"], B["ne"], B["se"]), texfn)]  # bottom
    tris = ((("nw", "sw", "se"), ("nw", "se", "ne")) if split == "nw-se" else (("nw", "sw", "ne"), ("ne", "sw", "se")))
    for t in tris:
        pts = [P[k] for k in t]
        if any(p[1] > 0 for p in pts):
            out.append(_poly(pts, texfn))
    for a, b in (("ne", "nw"), ("sw", "se"), ("nw", "sw"), ("se", "ne")):  # N, S, W, E sides (CCW from outside)
        pts = [P[a], B[a], B[b], P[b]]
        pts = [p for i, p in enumerate(pts) if not (i in (0, 3) and p[1] == 0)]
        if len(pts) >= 3:
            out.append(_poly(pts, texfn))
    return out


def _transform_faces(faces, fn) -> list["Face"]:
    from .geometry import face

    out = []
    for f in faces:
        pts = [fn(p) for p in f.pts]
        out.append(face(pts, f.uvs, f.tex, f.color))
    return out


def _orient(faces, m: Mat, texfn) -> list["Face"]:
    """Rotate local faces (0..1 cube) by m about the centre and re-texture by world-facing side."""
    rotated = []
    for f in faces:
        pts = [tuple(c + 0.5 for c in _apply(m, (p[0] - 0.5, p[1] - 0.5, p[2] - 0.5))) for p in f.pts]
        rotated.append(_poly(pts, texfn))
    return rotated


def _flip_y(faces, texfn) -> list["Face"]:
    return [_poly([(p[0], 1 - p[1], p[2]) for p in reversed(f.pts)], texfn) for f in faces]


def _boxes(mask: int, texfn) -> list["Face"]:
    from .geometry import box

    def b(x0, y0, z0, x1, y1, z1):
        return [_poly(f.pts, texfn) for f in box(x0, y0, z0, x1, y1, z1, (None,) * 6)]

    kind, p = mask & 0xFF00, mask & 0xFF
    if kind == 0:
        if p == 0:  # balustrades/banisters (no collision): a rail-height panel
            return b(0, 0, 7 / 16, 1, 15 / 16, 9 / 16)
        out = []
        for i in range(8):
            if p & (1 << i):
                x, y, z = (0.5 if i & 1 else 0), (0.5 if i & 4 else 0), (0.5 if i & 2 else 0)
                out += b(x, y, z, x + 0.5, y + 0.5, z + 0.5)
        return out
    if kind == 0x100:
        r = p / 16
        return b(0.5 - r, 0, 0.5 - r, 0.5 + r, 1, 0.5 + r)
    if kind == 0x200:
        r = p / 32
        return b(0, 0, 0.5 - r, 1, 1, 0.5 + r)
    return b(0, 0, 0, 1, 1, 1)


def _ac_local(sid: int, texfn) -> list["Face"]:
    tris = model_triangles(AC_MODELS[sid]) if sid in AC_MODELS else None
    if tris:
        return [_poly(t, texfn) for t in tris]
    const = SHAPES.get(sid, ("",))[0]
    if const in ("RoofTile", "RoofTileSE", "RoofOverhang", "SlopeTileA1", "SlopeTileB2", "SlopeTileC2", "DoubleRoofTile"):
        return heightfield({"nw": 0, "ne": 0, "sw": 1, "se": 1}, "nw-se", texfn)
    if const in ("RoofOuterCorner", "RoofOverhangOuterCorner", "BevelledOuterCorner"):
        return heightfield({"nw": 0, "ne": 0, "sw": 1, "se": 0}, "ne-sw", texfn)
    if const in ("RoofInnerCorner", "RoofOverhangInnerCorner", "BevelledInnerCorner"):
        return heightfield({"nw": 1, "ne": 0, "sw": 1, "se": 1}, "ne-sw", texfn)
    if const in ("RoofRidge", "RoofOverhangRidge", "AngledRoofRidge"):
        a = [_poly(f.pts, texfn) for f in heightfield({"nw": 0, "ne": 0, "sw": 0.5, "se": 0.5}, "nw-se", texfn)]
        return [_poly([(p[0], p[1], p[2] * 0.5) for p in f.pts], texfn) for f in a] + \
               [_poly([(p[0], p[1], 1 - p[2] * 0.5) for p in reversed(f.pts)], texfn) for f in a]
    if const == "RoofSmartRidge":
        apex = (0.5, 0.5, 0.5)
        c = [(0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0)]
        out = [_poly(list(reversed(c)), texfn)]
        for i in range(4):
            out.append(_poly([c[i], c[(i + 1) % 4], apex], texfn))
        return out
    if const == "Stairs":  # tall half at the back (south), step at the front
        from .geometry import box
        return [_poly(f.pts, texfn) for f in box(0, 0, 0, 1, 0.5, 1, (None,) * 6) + box(0, 0.5, 0.5, 1, 1, 1, (None,) * 6)]
    return _boxes(SHAPES.get(sid, ("", "", "", "", 1, 1, 0xff))[6], texfn)


def geometry(b: "Block", palette: "Palette") -> list["Face"] | None:
    if microblocks.is_fmp(b):
        return microblocks.geometry(b, palette)
    if is_ac(b):
        sid, base, data, side, turn = _ac_fields(b)
        texfn = _textured(palette, base, data)
        return _orient(_ac_local(sid, texfn), ac_matrix(side, turn), texfn)
    if is_cb(b):
        cover = _cb_cover(b) or ("minecraft:planks", 0)
        texfn = _textured(palette, *cover)
        data = b.te.get("cbMetadata", nbt.Int(0)).v
        kind = b.name[len(CB_PREFIX):]
        if kind == "blockCarpentersSlope" and data in SLOPES:
            return _cb_slope_faces(*SLOPES[data], texfn)
        if kind == "blockCarpentersStairs" and data in CB_STAIRS:
            t, facings = CB_STAIRS[data]
            if t == "NORMAL":
                hz = next(d for d in facings if d in (N, S, E, W))
                # local stairs: step at front (north), tall half south; rotate front onto hz
                turns = {N: 0, E: 1, S: 2, W: 3}[hz]
                m = _I
                for _ in range(turns):
                    m = _mul(((0, 0, -1), (0, 1, 0), (1, 0, 0)), m)
                faces = _orient(_ac_local(91, texfn), m, texfn)
                return _flip_y(faces, texfn) if D in facings else faces
        if kind == "blockCarpentersBlock" and 1 <= data <= 6:
            from .geometry import box
            half = {1: (0, 0, 0, .5, 1, 1), 2: (.5, 0, 0, 1, 1, 1), 3: (0, 0, 0, 1, .5, 1), 4: (0, .5, 0, 1, 1, 1),
                    5: (0, 0, 0, 1, 1, .5), 6: (0, 0, .5, 1, 1, 1)}[data]
            return [_poly(f.pts, texfn) for f in box(*half, (None,) * 6)]
        from .geometry import box
        return [_poly(f.pts, texfn) for f in box(0, 0, 0, 1, 1, 1, (None,) * 6)]
    return None


def _corner_heights(facings: frozenset, low_only_odd: bool) -> dict[str, float]:
    corners = {"nw": (-1, -1), "ne": (1, -1), "sw": (-1, 1), "se": (1, 1)}
    hz = [d for d in facings if d in (N, S, E, W)]
    out = {}
    for k, (cx, cz) in corners.items():
        dots = [cx * d[0] + cz * d[2] for d in hz]
        if low_only_odd:  # interior: everything high except the corner the faces point to
            out[k] = 0 if all(x > 0 for x in dots) else 1
        else:  # exterior / wedge: high only where every facing points away
            out[k] = 1 if all(x < 0 for x in dots) else 0
    return out


def _cb_slope_faces(kind: str, facings: frozenset, texfn) -> list["Face"]:
    if kind == "WEDGE_SIDE":
        # vertical wedge: full height, a right triangle in plan on the corners the facings point away from
        corners = {"nw": (0, 0), "ne": (1, 0), "sw": (0, 1), "se": (1, 1)}
        solid = [k for k, v in _corner_heights(facings, True).items() if v]
        tri = [corners[k] for k in ("nw", "ne", "se", "sw") if k in solid]  # clockwise seen from above
        out = [_poly([(x, 0, z) for x, z in tri], texfn), _poly([(x, 1, z) for x, z in reversed(tri)], texfn)]
        for i in range(len(tri)):
            (x0, z0), (x1, z1) = tri[i], tri[(i + 1) % len(tri)]
            out.append(_poly([(x1, 1, z1), (x1, 0, z1), (x0, 0, z0), (x0, 1, z0)], texfn))
        return out
    if kind in ("WEDGE", "PRISM_WEDGE"):
        faces = heightfield(_corner_heights(facings, False), "nw-se", texfn)
    elif kind in ("WEDGE_EXT", "OBLIQUE_EXT"):
        h = _corner_heights(facings, False)
        odd = next(k for k, v in h.items() if v)
        through = "nw-se" if odd in ("nw", "se") else "ne-sw"
        other = "ne-sw" if through == "nw-se" else "nw-se"
        faces = heightfield(h, through if kind == "WEDGE_EXT" else other, texfn)
    elif kind in ("WEDGE_INT", "OBLIQUE_INT"):
        h = _corner_heights(facings, True)
        odd = next(k for k, v in h.items() if not v)
        through = "nw-se" if odd in ("nw", "se") else "ne-sw"
        other = "ne-sw" if through == "nw-se" else "nw-se"
        faces = heightfield(h, through if kind == "WEDGE_INT" else other, texfn)
    else:  # PRISM family: approximated as a half-height block
        from .geometry import box
        faces = [_poly(f.pts, texfn) for f in box(0, 0, 0, 1, 0.5, 1, (None,) * 6)]
    return _flip_y(faces, texfn) if D in facings else faces
