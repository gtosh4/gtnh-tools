> **Toolkit note (overrides this document):** the registry names in GTNH 2.9 are `ArchitectureCraft:shape` /
> `ArchitectureCraft:shapeSE` (mixed case) — confirmed in `blocks.db` and the Threshold `export` world's level.dat
> FML ItemData. Local geometry used by `gtnhbuild` comes from `client/render/RenderRoof.java` (RoofTile: slope
> rises from local north z=0,y=0 to south z=1,y=1) and `ShapeKind.addCollisionBoxesToList` (cubelet bit i:
> x=i&1, z=(i>>1)&1, y=(i>>2)&1). WorldEdit-GTNH rotates/flips these TEs itself (`ArchitectureCraftBlockTransformHook`).

# ArchitectureCraft (GTNH 2.9, `ArchitectureCraft-1.12.19.jar`) — TileShape NBT and Orientation Reference

Source: `GTNewHorizons/ArchitectureCraft` `master` (HEAD `220d7abd…`), compared against tag `1.12.19` (`172a307f…`).
Paths are relative to `src/main/java/gcewing/architecture/` unless stated otherwise.
`[INFERENCE]` marks anything not directly observed in source.

Verified this pass (raw master source): `common/shape/Shape.java` 1–312 (enum rows, `orientOnPlacement`, `orientFromHitPosition`, `offsetXForPlacementHit`, `turnForPlacementHit`); `common/shape/ShapeKind.java` 1–end of class body (`newStack`, `orientOnPlacement`, `chiselUsedOnCentre`, `newSecondaryMaterialStack`, `onHammerUse`, `zoneHit`, `acceptsCladding`, `isValidSecondaryMaterial`, `addCollisionBoxesToList`); `common/shape/Banister.java` (full); `common/shape/Window.java` (full); `common/item/ItemCladding.java` lines 1–300 of 851 only.
Earlier passes (tag `1.12.19` identical on the compared lines): `compat/Matrix3.java`, `common/tile/TileShape.java`, `compat/Trans3.java` header, `compat/Vector3.java` 90–130, `common/shape/ShapeKind.java` head.
Not read: `Model.java`, `Roof.java`, `Profile`, `TileArchitecture`, `ItemCladding.java` beyond line 300, `BlockArchitecture.createNewTileEntity`, `TileSawbench.java` beyond line 300, `Directions.java`, `Utils.java`, `Orient24WaysByTE.java`, `ItemShapeTransformer.java` on 1.12.19.

Coordinates: local shape geometry lives in `[-0.5, 0.5]^3` around the block centre. World: +X East, +Z South, −Z North, +Y Up.

---

## 1. Block registry, meta, and TE creation

Source: `ArchitectureCraft.java` (`MOD_ID`, `ASSET_KEY`); `ArchitectureContent.java` (`registerBlock`, `registerBlocks`, `registerTileEntities`).

| Item | Value | Source |
|---|---|---|
| `MOD_ID` | `"ArchitectureCraft"` | `ArchitectureCraft.java` (prior pass) |
| `ASSET_KEY` | `MOD_ID.toLowerCase()` = `"architecturecraft"` | `ArchitectureCraft.java` line 44 |
| Block `shape` | registered as `architecturecraft:shape`, ItemBlock `ShapeItem` | `ArchitectureContent.registerBlock` |
| Block `shapeSE` | `architecturecraft:shapeSE`, ItemBlock `ShapeItem` | `ArchitectureContent.registerBlocks` |
| TE id | `"gcewing.shape"` → `TileShape` | `ArchitectureContent.registerTileEntities` |
| Sawbench | block `architecturecraft:sawbench`, TE `"gcewing.sawbench"` → `TileSawbench` | `registerTileEntities` |

`[INFERENCE]` The GameData key uses the lowercased `ASSET_KEY`, as the unlocalized name does (`setBlockName(ASSET_KEY + ":" + name)`).

`BlockShape` (`common/block/BlockShape.java`):
- `shape` and `shapeSE` are both `BlockShape`. The only difference is `getLightValue`: 15 for `shapeSE`, else 0.
- Only block property: `LIGHT` (0–15). `getNumSubtypes()` = 16.
- Block meta = LIGHT index. Meta does not select shape, material, or orientation.
- Orientation handler = `Orientation.orient24WaysByTE` `[INFERENCE: TE carries side/turn]`.
- Use meta 0 for both block ids.

**TE from block alone:** `[INFERENCE]` `BlockArchitecture.createNewTileEntity` (not read) returns `new TileShape()`. `TileShape()` (no-arg) defaults to `RoofTile`, `minecraft:planks` meta 0, side 0, turn 0, offsetX 0. Shape, material, and orientation are carried in TE NBT; the TE is not derived from block meta.

Placement path: `ShapeItem.placeBlockAt` (`common/shape/ShapeItem.java`, prior pass) sets the block state, calls `te.readFromItemStack(stack)`, then computes side/turn (section 3). A schematic written by WorldEdit does **not** run this path `[INFERENCE: WorldEdit writes TE NBT raw]`, so side/turn must be in schematic TE NBT.

`shape` vs `shapeSE`: `ShapeKind.newStack(shape, materialBlock, materialMeta, stackSize, shaderEmissive)` picks `ArchitectureCraft.content.blockShapeSE` when `shaderEmissive`, else `blockShape` (`ShapeKind.java`, verified). Which callers pass `shaderEmissive` (e.g. Sawbench page 7 "Glow") is `[INFERENCE]`; the choice never appears in TE NBT.

---

## 2. Shape enum (`common/shape/Shape.java`)

Constructor: `Shape(int id, String title, ShapeKind kind, ShapeSymmetry sym, int materialUsed, int itemsProduced, int occlusionMask[, int flags])` (`Shape.java`, verified).
NBT stores `Shape` = `shape.id` (int). `Shape.forId` falls back to `RoofTile` on unknown id (`Shape.java`, verified).

Kind shorthand: `Roof` = `ShapeKind.Roof`; `Model:x` = `Model("x")`; `Banister:x` = `Banister("x")` (`ShapeKind.Banister`); `PlainWindow` / `CornerWindow` / `MullionWindow` = `WindowShapeKinds`; `CladdingSheet` = `Model:cladding`, symmetry `None`.
Flags (`ShapeFlags`): `placeUnderneath = 1`, `placeOffset = 2`.
Symmetry: `Unilateral`, `Bilateral`, `Quadrilateral`, `None`.

Python-dict form. Key = `id`; value = (enum constant, title, kind, symmetry, materialUsed, itemsProduced, occlusionMask, flags). Titles and numbers are verbatim from `Shape.java` lines 1–312.

```python
SHAPES = {
    0:   ("RoofTile", "Roof Tile", "Roof", "Bilateral", 1, 2, 0xcf, 0),
    1:   ("RoofOuterCorner", "Roof Outer Corner", "Roof", "Unilateral", 1, 3, 0x4f, 0),
    2:   ("RoofInnerCorner", "Roof Inner Corner", "Roof", "Unilateral", 2, 3, 0xdf, 0),
    3:   ("RoofRidge", "Gabled Roof Ridge", "Roof", "Bilateral", 1, 4, 0x0f, 0),
    4:   ("RoofSmartRidge", "Hip Roof Ridge", "Roof", "Quadrilateral", 1, 2, 0x0f, 0),
    5:   ("RoofValley", "Gabled Roof Valley", "Roof", "Bilateral", 1, 2, 0xff, 0),
    6:   ("RoofSmartValley", "Hip Roof Valley", "Roof", "Quadrilateral", 1, 1, 0xff, 0),
    7:   ("RoofOverhang", "Roof Overhang", "Model:roof_overhang", "Bilateral", 1, 2, 0xcf, 0),
    8:   ("RoofOverhangOuterCorner", "Roof Overhang Outer Corner", "Model:roof_overhang_outer_corner", "Unilateral", 1, 3, 0x4f, 0),
    9:   ("RoofOverhangInnerCorner", "Roof Overhang Inner Corner", "Model:roof_overhang_inner_corner", "Unilateral", 2, 3, 0xdf, 0),
    10:  ("Cylinder", "Cylinder", "Model:cylinder_full_r8h16", "Quadrilateral", 1, 1, 0xff, 0),
    11:  ("CylinderHalf", "Half Cylinder", "Model:cylinder_half_r8h16", "Bilateral", 1, 1, 0xcc, 0),
    12:  ("CylinderQuarter", "Quarter Cylinder", "Model:cylinder_quarter_r8h16", "Unilateral", 1, 1, 0x44, 0),
    13:  ("CylinderLargeQuarter", "Round Outer Corner", "Model:cylinder_quarter_r16h16", "Unilateral", 1, 1, 0xff, 0),
    14:  ("AnticylinderLargeQuarter", "Round Inner Corner", "Model:round_inner_corner", "Unilateral", 1, 2, 0xdd, 0),
    15:  ("Pillar", "Round Pillar", "Model:cylinder_r6h16", "Quadrilateral", 1, 1, 0x106, 0),
    16:  ("Post", "Round Post", "Model:cylinder_r4h16", "Quadrilateral", 1, 4, 0x104, 0),
    17:  ("Pole", "Round Pole", "Model:cylinder_r2h16", "Quadrilateral", 1, 16, 0x102, 0),
    18:  ("BevelledOuterCorner", "Bevelled Outer Corner", "Model:bevelled_outer_corner", "Unilateral", 1, 3, 0x4f, 0),
    19:  ("BevelledInnerCorner", "Bevelled Inner Corner", "Model:bevelled_inner_corner", "Unilateral", 1, 1, 0xdf, 0),
    20:  ("PillarBase", "Round Pillar Base", "Model:pillar_base", "Quadrilateral", 1, 1, 0xff, 0),
    21:  ("DoricCapital", "Doric Capital", "Model:doric_capital", "Quadrilateral", 1, 1, 0xff, 0),
    22:  ("IonicCapital", "Ionic capital", "Model:ionic_capital", "Bilateral", 1, 1, 0xff, 0),
    23:  ("CorinthianCapital", "Corinthian capital", "Model:corinthian_capital", "Quadrilateral", 1, 1, 0xff, 0),
    24:  ("DoricTriglyph", "Triglyph", "Model:doric_triglyph[lrStraight]", "Bilateral", 1, 1, 0xff, 0),
    25:  ("DoricTriglyphCorner", "Triglyph Corner", "Model:doric_triglyph_corner[lrCorner]", "Bilateral", 1, 1, 0xff, 0),
    26:  ("DoricMetope", "Metope", "Model:doric_metope[lrStraight]", "Bilateral", 1, 1, 0xff, 0),
    27:  ("Architrave", "Architrave", "Model:architrave[lrStraight]", "Bilateral", 1, 1, 0xff, 0),
    28:  ("ArchitraveCorner", "Architrave Corner", "Model:architrave_corner[lrCorner]", "Unilateral", 1, 1, 0xff, 0),
    30:  ("WindowFrame", "Window Frame", "PlainWindow", "Bilateral", 1, 4, 0x202, 0),
    31:  ("WindowCorner", "Window Corner", "CornerWindow", "Unilateral", 1, 2, 0x202, 0),
    32:  ("WindowMullion", "Window Mullion", "MullionWindow", "Bilateral", 1, 2, 0x202, 0),
    33:  ("SphereFull", "Sphere", "Model:sphere_full_r8", "Quadrilateral", 1, 1, 0xff, 0),
    34:  ("SphereHalf", "Hemisphere", "Model:sphere_half_r8", "Quadrilateral", 1, 2, 0x0f, 0),
    35:  ("SphereQuarter", "Quarter Sphere", "Model:sphere_quarter_r8", "Bilateral", 1, 4, 0x0c, 0),
    36:  ("SphereEighth", "Quarter Hemisphere", "Model:sphere_eighth_r8", "Unilateral", 1, 8, 0x04, 0),
    37:  ("SphereEighthLarge", "Round Outer Corner Cap", "Model:sphere_eighth_r16", "Unilateral", 1, 1, 0xff, 0),
    38:  ("SphereEighthLargeRev", "Round Inner Corner Cap", "Model:sphere_eighth_r16_rev", "Unilateral", 1, 1, 0xdf, 0),
    40:  ("RoofOverhangGableLH", "Gable Overhang LH", "Model:roof_overhang_gable_lh", "Bilateral", 1, 4, 0x48, 0),
    41:  ("RoofOverhangGableRH", "Gable Overhang RH", "Model:roof_overhang_gable_rh", "Bilateral", 1, 4, 0x84, 0),
    42:  ("RoofOverhangGableEndLH", "Gable Overhang LH End", "Model:roof_overhang_gable_end_lh", "Bilateral", 1, 4, 0x48, 0),
    43:  ("RoofOverhangGableEndRH", "Gable Overhang RH End", "Model:roof_overhang_gable_end_rh", "Bilateral", 1, 4, 0x48, 0),
    44:  ("RoofOverhangRidge", "Ridge Overhang", "Model:roof_overhang_gable_ridge", "Bilateral", 1, 4, 0x0c, 0),
    45:  ("RoofOverhangValley", "Valley Overhang", "Model:roof_overhang_gable_valley", "Bilateral", 1, 4, 0xcc, 0),
    50:  ("CorniceLH", "Cornice LH", "Model:cornice_lh", "Bilateral", 1, 4, 0x48, 0),
    51:  ("CorniceRH", "Cornice RH", "Model:cornice_rh", "Bilateral", 1, 4, 0x84, 0),
    52:  ("CorniceEndLH", "Cornice LH End", "Model:cornice_end_lh", "Bilateral", 1, 4, 0x48, 0),
    53:  ("CorniceEndRH", "Cornice RH End", "Model:cornice_end_rh", "Bilateral", 1, 4, 0x48, 0),
    54:  ("CorniceRidge", "Cornice Ridge", "Model:cornice_ridge", "Bilateral", 1, 4, 0x0c, 0),
    55:  ("CorniceValley", "Cornice Valley", "Model:cornice_valley", "Bilateral", 1, 4, 0xcc, 0),
    56:  ("CorniceBottom", "Cornice Bottom", "Model:cornice_bottom", "Bilateral", 1, 4, 0x0c, 0),
    60:  ("CladdingSheet", "Cladding", "Model:cladding", "None", 1, 1, 0x0c, 0),
    61:  ("ArchD1", "Arch Diameter 1", "Model:arch_d1", "Bilateral", 1, 1, 0xff, 1),
    62:  ("ArchD2", "Arch Diameter 2", "Model:arch_d2", "Bilateral", 1, 2, 0xfc, 1),
    63:  ("ArchD3A", "Arch Diameter 3 Part A", "Model:arch_d3a", "Bilateral", 1, 2, 0xcc, 1),
    64:  ("ArchD3B", "Arch Diameter 3 Part B", "Model:arch_d3b", "Bilateral", 1, 1, 0xfc, 1),
    65:  ("ArchD3C", "Arch Diameter 3 Part C", "Model:arch_d3c", "Bilateral", 1, 1, 0xff, 1),
    66:  ("ArchD4A", "Arch Diameter 4 Part A", "Model:arch_d4a", "Bilateral", 1, 2, 0xcc, 1),
    67:  ("ArchD4B", "Arch Diameter 4 Part B", "Model:arch_d4b", "Bilateral", 1, 1, 0xfc, 1),
    68:  ("ArchD4C", "Arch Diameter 4 Part C", "Model:arch_d4c", "Bilateral", 1, 2, 0x0, 1),
    70:  ("BanisterPlainBottom", "Plain Banister Bottom Transition", "Banister:balustrade_stair_plain_bottom", "Bilateral", 1, 10, 0x0, 2),
    71:  ("BanisterPlain", "Plain Banister", "Banister:balustrade_stair_plain", "Bilateral", 1, 10, 0x0, 2),
    72:  ("BanisterPlainTop", "Plain Banister Top Transition", "Banister:balustrade_stair_plain_top", "Bilateral", 1, 10, 0x0, 2),
    73:  ("BalustradeFancy", "Fancy Balustrade", "Model:balustrade_fancy", "Bilateral", 1, 5, 0x0, 0),
    74:  ("BalustradeFancyCorner", "Fancy Corner Balustrade", "Model:balustrade_fancy_corner", "Unilateral", 1, 2, 0x0, 0),
    75:  ("BalustradeFancyWithNewel", "Fancy Balustrade with Newel", "Model:balustrade_fancy_with_newel", "Bilateral", 1, 3, 0x0, 0),
    76:  ("BalustradeFancyNewel", "Fancy Newel", "Model:balustrade_fancy_newel", "Unilateral", 1, 4, 0x0, 0),
    77:  ("BalustradePlain", "Plain Balustrade", "Model:balustrade_plain", "Bilateral", 1, 10, 0x0, 0),
    78:  ("BalustradePlainOuterCorner", "Plain Outer Corner Balustrade", "Model:balustrade_plain_outer_corner", "Unilateral", 1, 4, 0x0, 0),
    79:  ("BalustradePlainWithNewel", "Plain Balustrade with Newel", "Model:balustrade_plain_with_newel", "Bilateral", 1, 6, 0x0, 0),
    80:  ("BanisterPlainEnd", "Plain Banister End", "Banister:balustrade_stair_plain_end", "Bilateral", 1, 8, 0x0, 2),
    81:  ("BanisterFancyNewelTall", "Tall Fancy Newel", "Model:balustrade_fancy_newel_tall", "Unilateral", 1, 2, 0x0, 0),
    82:  ("BalustradePlainInnerCorner", "Plain Inner Corner Balustrade", "Model:balustrade_plain_inner_corner", "Unilateral", 1, 8, 0x0, 0),
    83:  ("BalustradePlainEnd", "Plain Balustrade End", "Banister:balustrade_plain_end", "Bilateral", 1, 8, 0x0, 2),
    84:  ("BanisterFancyBottom", "Fancy Banister Bottom Transition", "Banister:balustrade_stair_fancy_bottom", "Bilateral", 1, 5, 0x0, 2),
    85:  ("BanisterFancy", "Fancy Banister", "Banister:balustrade_stair_fancy", "Bilateral", 1, 5, 0x0, 2),
    86:  ("BanisterFancyTop", "Fancy Banister Top Transition", "Banister:balustrade_stair_fancy_top", "Bilateral", 1, 5, 0x0, 2),
    87:  ("BanisterFancyEnd", "Fancy Banister End", "Banister:balustrade_stair_fancy_end", "Bilateral", 1, 2, 0x0, 2),
    88:  ("BanisterPlainInnerCorner", "Plain Banister Inner Corner", "Model:balustrade_stair_plain_inner_corner", "Unilateral", 1, 6, 0x0, 0),
    90:  ("Slab", "Slab", "Model:slab", "Quadrilateral", 1, 2, 0x0f, 0),
    91:  ("Stairs", "Stairs", "Model:stairs[lrStraight]", "Bilateral", 3, 4, 0xcf, 0),
    92:  ("StairsOuterCorner", "Stairs Outer Corner", "Model:stairs_outer_corner[lrCorner]", "Unilateral", 2, 3, 0x4f, 0),
    93:  ("StairsInnerCorner", "Stairs Inner Corner", "Model:stairs_inner_corner[rlCorner]", "Unilateral", 1, 1, 0xdf, 0),
    94:  ("SlopeTileA1", "Slope A Start", "Roof", "Bilateral", 1, 1, 0xcf, 0),
    95:  ("SlopeTileA2", "Slope A End", "Roof", "Bilateral", 1, 3, 0x0f, 0),
    96:  ("SlopeTileB1", "Slope B Start", "Roof", "Bilateral", 1, 1, 0xff, 0),
    97:  ("SlopeTileB2", "Slope B Middle", "Roof", "Bilateral", 1, 2, 0xcf, 0),
    98:  ("SlopeTileB3", "Slope B End", "Roof", "Bilateral", 1, 3, 0x0f, 0),
    99:  ("SlopeTileC1", "Slope C 1", "Roof", "Bilateral", 1, 1, 0xff, 0),
    100: ("SlopeTileC2", "Slope C 2", "Roof", "Bilateral", 1, 2, 0xcf, 0),
    101: ("SlopeTileC3", "Slope C 3", "Roof", "Bilateral", 1, 3, 0x0f, 0),
    102: ("SlopeTileC4", "Slope C 4", "Roof", "Bilateral", 1, 4, 0x0f, 0),
    103: ("SlopeTileA1SE", "Slope A Start(Glow)", "Roof", "Bilateral", 1, 1, 0xcf, 0),
    104: ("SlopeTileA2SE", "Slope A End(Glow)", "Roof", "Bilateral", 1, 3, 0x0f, 0),
    105: ("SlopeTileB1SE", "Slope B Start(Glow)", "Roof", "Bilateral", 1, 1, 0xff, 0),
    106: ("SlopeTileB2SE", "Slope B Middle(Glow)", "Roof", "Bilateral", 1, 2, 0xcf, 0),
    107: ("SlopeTileB3SE", "Slope B End(Glow)", "Roof", "Bilateral", 1, 3, 0x0f, 0),
    108: ("SlopeTileC1SE", "Slope C 1(Glow)", "Roof", "Bilateral", 1, 1, 0xff, 0),
    109: ("SlopeTileC2SE", "Slope C 2(Glow)", "Roof", "Bilateral", 1, 2, 0xcf, 0),
    110: ("SlopeTileC3SE", "Slope C 3(Glow)", "Roof", "Bilateral", 1, 3, 0x0f, 0),
    111: ("SlopeTileC4SE", "Slope C 4(Glow)", "Roof", "Bilateral", 1, 4, 0x0f, 0),
    112: ("RoofTileSE", "Roof Tile(Glow)", "Roof", "Bilateral", 1, 2, 0xcf, 0),
    113: ("SquareSE", "Square(Glow)", "Model:square", "Quadrilateral", 1, 1, 0xff, 0),
    114: ("SlabSE", "Slab(Glow)", "Model:slab", "Quadrilateral", 1, 2, 0x0f, 0),
    115: ("AngledRoofRidge", "Angled Roof Ridge", "Model:angled_roof_ridge", "Bilateral", 1, 4, 0x0f, 0),
    116: ("DoubleRoofTile", "Double Roof Tile", "Model:double_roof_tile", "Bilateral", 1, 2, 0xcf, 0),
}
```

Notes:
- Ids 0–6 and 94–112 use `ShapeKind.Roof`. `Roof.acceptsCladding()` = true is `[INFERENCE]`; `Roof.java` was not read.
- `ShapeKind.acceptsCladding()` default = false; `isValidSecondaryMaterial` default = false; `secondaryDefaultsToBase` default = false (`ShapeKind.java`, verified). Any `Model` shape that does not override these therefore accepts no cladding. `Model.java` was not read `[INFERENCE]`.
- Window kinds (ids 30–32): `isValidSecondaryMaterial` = `Blocks.glass_pane` or `Blocks.stained_glass_pane`; `canPlaceUpsideDown()` = false; `newSecondaryMaterialStack` = `blockStackWithState(state, 1)` (`Window.java`, verified).
- Occlusion mask `occlusionMask` drives `ShapeKind.addCollisionBoxesToList` (cases 0x000 cubelet bitmap, 0x100 square, 0x200 slab, 0x300 back-corner slab, 0x400/0x500 back slab(s), default full cube) (`ShapeKind.java`, verified). Consumers other than collision are `[INFERENCE]`.

---

## 3. Orientation: side (0–5) and turn (0–3)

### 3.1 Storage and transform
- `TileArchitecture` holds `side` and `turn`; `TileShape` adds `offsetX` with `getOffsetX()` used in `ShapeKind.orientOnPlacement` and `onHammerUse` (verified). Byte storage and the `/16` scale are `[INFERENCE]`.
- Local→global transform: `Trans3.sideTurn(side, turn)` `[INFERENCE: TileShape.localToGlobalTransformation not read this pass]`.

### 3.2 Rotation math (`compat/Matrix3.java`, `compat/Trans3.java`, verified 1.12.19 = master)

```
rot(deg, i, j): r[i][i] = c; r[i][j] = -s; r[j][i] = s; r[j][j] = c   (c = cos, s = sin)
rotX(d) = rot(d,1,2)   rotY(d) = rot(d,2,0)   rotZ(d) = rot(d,0,1)

turnRotations[t] = rotY(90*t)                                  # t = 0..3
sideRotations[s]:
  0: I
  1: rotX(180)            = diag(1, -1, -1)
  2: rotX(90)             = [[1,0,0],[0,0,-1],[0,1,0]]
  3: rotX(-90)·rotY(180)  = [[-1,0,0],[0,0,-1],[0,-1,0]]
  4: rotZ(-90)·rotY(90)   = [[0,1,0],[0,0,-1],[-1,0,0]]
  5: rotZ(90)·rotY(-90)   = [[0,-1,0],[0,0,-1],[1,0,0]]
sideTurnRotations[s][t] = sideRotations[s] · turnRotations[t]   # matrix product
local → world:  world = origin + M · local
world → local:  local = Mᵀ · (world − origin)   # M is orthogonal
```

Matrices for side 2–5 were computed by hand from `rotX`, `rotY`, `rotZ`, and the `sideRotations` list `[I, rotX(180), rotX(90), rotX(-90)·rotY(180), rotZ(-90)·rotY(90), rotZ(90)·rotY(-90)]` in `Matrix3.java` (verified list). Products were checked on column 1 only (local −Y image).

`rotY(90t)` columns (image of local X, Y, Z under turn alone):

| t | rotY(90t) | image of +X | image of +Z |
|---|---|---|---|
| 0 | I | (1,0,0) | (0,0,1) |
| 1 | [[0,0,1],[0,1,0],[-1,0,0]] | (0,0,−1) | (1,0,0) |
| 2 | diag(−1,1,−1) | (−1,0,0) | (0,0,−1) |
| 3 | [[0,0,−1],[0,1,0],[1,0,0]] | (0,0,1) | (−1,0,0) |

**Meaning of `side`:** the world direction of local −Y (column 1 of M, negated):

| side | local −Y → world | local +Y → world |
|---|---|---|
| 0 | DOWN (0,−1,0) | UP (0,1,0) |
| 1 | UP (0,1,0) | DOWN (0,−1,0) |
| 2 | NORTH (0,0,−1) | SOUTH (0,0,1) |
| 3 | SOUTH (0,0,1) | NORTH (0,0,−1) |
| 4 | WEST (−1,0,0) | EAST (1,0,0) |
| 5 | EAST (1,0,0) | WEST (−1,0,0) |

### 3.3 Explicit tables: side 0 and side 1

M = sideRotations[side] · rotY(90t). Each cell is the world image of a local face (local EAST=+X, WEST=−X, SOUTH=+Z, NORTH=−Z, UP=+Y, DOWN=−Y).

**side = 0** (M = rotY(90t))

| turn | local EAST | local WEST | local SOUTH | local NORTH | local UP | local DOWN |
|---|---|---|---|---|---|---|
| 0 | EAST (1,0,0) | WEST (−1,0,0) | SOUTH (0,0,1) | NORTH (0,0,−1) | UP | DOWN |
| 1 | NORTH (0,0,−1) | SOUTH (0,0,1) | EAST (1,0,0) | WEST (−1,0,0) | UP | DOWN |
| 2 | WEST (−1,0,0) | EAST (1,0,0) | NORTH (0,0,−1) | SOUTH (0,0,1) | UP | DOWN |
| 3 | SOUTH (0,0,1) | NORTH (0,0,−1) | WEST (−1,0,0) | EAST (1,0,0) | UP | DOWN |

**side = 1** (M = diag(1,−1,−1)·rotY(90t))

| turn | local EAST | local WEST | local SOUTH | local NORTH | local UP | local DOWN |
|---|---|---|---|---|---|---|
| 0 | EAST (1,0,0) | WEST (−1,0,0) | NORTH (0,0,−1) | SOUTH (0,0,1) | DOWN | UP |
| 1 | SOUTH (0,0,1) | NORTH (0,0,−1) | EAST (1,0,0) | WEST (−1,0,0) | DOWN | UP |
| 2 | WEST (−1,0,0) | EAST (1,0,0) | SOUTH (0,0,1) | NORTH (0,0,−1) | DOWN | UP |
| 3 | NORTH (0,0,−1) | SOUTH (0,0,1) | WEST (−1,0,0) | EAST (1,0,0) | DOWN | UP |

Worked check, side 1 turn 1: M·e_x = diag(1,−1,−1)·(0,0,−1) = (0,0,1) → local +X → SOUTH. M·e_z = diag(1,−1,−1)·(1,0,0) = (1,0,0) → local +Z → EAST.

Side 0 local DOWN → world DOWN; side 1 local DOWN → world UP. This matches `Shape.rightSideUpSide()` (0 unless `placeUnderneath`) and `upsideDownSide()` (1 unless `placeUnderneath`).

### 3.4 Placement logic (verified)

**`ShapeItem.placeBlockAt`** (prior pass): `d = directionVec(face)`; `hit = (hitX − d.x − 0.5, hitY − d.y − 0.5, hitZ − d.z − 0.5)`; `te.readFromItemStack(stack)`; `npos = te.pos.offset(oppositeFacing(face))`; `te.shape.orientOnPlacement(player, te, npos, nstate, nte, face, hit)`.

**`Shape.orientOnPlacement(player, te, npos, nstate, nte, face, hit)`** (`Shape.java`): calls `te.shape.kind.orientOnPlacement(player, te, npos, nstate, nte, face, hit)`; if false, calls `orientFromHitPosition`.

**`ShapeKind.orientOnPlacement(player, te, npos, nstate, nte, otherFace, hit)`** (`ShapeKind.java`): if `nte instanceof TileShape`, delegates to the `TileShape` overload; else passes `nte = null`.

**`ShapeKind.orientOnPlacement(player, te, nte, otherFace, hit)`** (`ShapeKind.java`, verified). If `nte != null && !player.isSneaking()`:
- `otherProfile = Profile.getProfileGlobal(nte.shape, nte.side, nte.turn, otherFace)`; if non-null:
- `thisFace = oppositeFacing(otherFace)`; for `i` in 0..3: `turn = (nte.turn + i) & 3`; `thisProfile = Profile.getProfileGlobal(te.shape, nte.side, turn, thisFace)`; if `Profile.matches(thisProfile, otherProfile)` → `te.setSide(nte.side)`, `te.setTurn(turn)`, `te.setOffsetX(nte.getOffsetX())`, return true.
- Otherwise return false.
`Profile` class is not read `[INFERENCE: Profile.getProfileGlobal maps local faces through side/turn and returns a profile per face]`.

**`Shape.orientFromHitPosition(player, te, face, hit)`** (`Shape.java`, verified):
- `face == UP` → `side = rightSideUpSide()`.
- `face == DOWN` → `side = canPlaceUpsideDown() ? upsideDownSide() : rightSideUpSide()`.
- other faces → if sneaking: `side = oppositeFacing(face).ordinal()`; else if `hit.y > 0 && canPlaceUpsideDown()`: `side = upsideDownSide()`; else `side = rightSideUpSide()`.
- `turn = turnForPlacementHit(side, hit, symmetry)`; `te.setSide(side)`; `te.setTurn(turn)`.
- If `flags & placeOffset`: `te.setOffsetX(offsetXForPlacementHit(side, turn, hit))`.

`rightSideUpSide()` = `placeUnderneath ? 1 : 0`; `upsideDownSide()` = `placeUnderneath ? 0 : 1` (`Shape.java`, verified).

**`turnForPlacementHit(side, hit, symmetry)`** (`Shape.java`, verified): `h = Trans3.sideTurn(side, 0).ip(hit)`; then by symmetry on `(h.x, h.z)`:
- `Quadrilateral` → 0.
- `Bilateral`: if `|h.z| > |h.x|` → `h.z < 0 ? 2 : 0`; else `h.x > 0 ? 1 : 3`.
- `Unilateral`: if `h.z > 0` → `h.x < 0 ? 0 : 1`; else `h.x > 0 ? 2 : 3`.
- default → 0.

**`offsetXForPlacementHit(side, turn, hit)`** (`Shape.java`, verified): `h = Trans3.sideTurn(side, turn).ip(hit)`; returns `kind.placementOffsetX()`, negated when `h.x < 0`. `placementOffsetX()` = 0 by default (`ShapeKind.java`, verified), `6/16` for `Banister` (`Banister.java`, verified).

**Window** (`Window.java`, verified): `orientOnPlacement(player, te, nte, otherFace, hit)`: if not sneaking and (`nte == null` or `nte.shape.kind` is not a `Window`): `otherFace` EAST/WEST → `setSide(0)`, `setTurn(0)`; NORTH/SOUTH → `setSide(0)`, `setTurn(1)`; returns true. Otherwise returns false, so `orientFromHitPosition` runs. `canPlaceUpsideDown()` = false.

**Banister** (`Banister.java`, verified): if not sneaking:
- If the neighbour is a `BlockStairs` and `otherFace` is UP or DOWN: `nside = stairsSide(nstate)` = `(meta >> 2) & 1`; `nturn = Utils.turnToFace(F_SOUTH, stairsFacing(nstate))`, `stairsFacing = stairsFacingMap[meta & 3]`, `stairsFacingMap = {F_WEST, F_EAST, F_SOUTH, F_NORTH}`; if `nside == 1 && (nturn & 1) == 0` then `nturn ^= 2`.
- Else if the neighbour is a `BlockShape` with a `TileShape`: `nside = nte.side`, `nturn = nte.turn`.
- If found and `side = oppositeFacing(otherFace).ordinal()` equals `nside`: `setSide(side)`, `setTurn(nturn & 3)`, `setOffsetX(te.shape.offsetXForPlacementHit(side, nturn, hit))`; return true.
- Otherwise falls through to `super.orientOnPlacement` (`Model`, not read `[INFERENCE]`).

Note: `Directions.F_WEST` / `F_EAST` alias `EnumFacing.EAST` / `WEST` `[INFERENCE: Directions.java not read; the aliasing is inferred from the mapping's use in Banister]`. Use ordinals when generating NBT.

**Hammer** (`ShapeKind.onHammerUse`, verified): sneak → `side = (side + 1) % 6`. Otherwise: if `offsetX != 0` → `offsetX = −offsetX`; then if `offsetX >= 0` → `turn = (turn + 1) % 4`. Then `markChanged()`.

**Chisel** (`ShapeKind.onChiselUse`, verified): `zoneHit(face, hit)` returns a side zone or null; a side hit toggles a connection, a centre hit clears secondary material (drops it as an item unless creative).

---

## 4. Materials: validity and `BaseName`

- `BaseName`: `[INFERENCE]` written with `BlockCompatUtils.getNameForBlock(block)` (prior pass; `compat/BlockCompatUtils.java` not re-read this pass). Returns the registry name, e.g. `minecraft:planks`. `BaseData` = `getMetaFromBlockState(state)`.
- Load: `[INFERENCE]` `TileShape` resolves `BaseName` with `Block.getBlockFromName`, falling back to `Blocks.planks` meta 0 when absent or unknown (prior pass). `[INFERENCE]` Any block name loads without validation on read.
- Secondary material gate: `ShapeKind.isValidSecondaryMaterial` (default false; Window overrides it, section 2). `ShapeKind.newSecondaryMaterialStack(state)` = cladding stack when `acceptsCladding()`, else null (`ShapeKind.java`, verified). Cladding item is `ArchitectureCraft.content.itemCladding` (verified).
- `ShapeKind.newStack(...)` with `Shape.CladdingSheet` returns `ArchitectureCraft.content.itemCladding.newStack(materialBlock, materialMeta, stackSize)` (verified). Other shapes return a `blockShape`/`blockShapeSE` stack with a TE (verified).
- Sawbench input check (`TileSawbench`, prior pass): `makeResultStack` requires `stackSize ≥ materialUsed` (`materialMultiple`), an `ItemBlock` material, and `isAcceptableMaterial`. Config `materials` default lists `tile.chisel.stained_glass` and `tile.extrautils:greenscreen`. The rest of `isAcceptableMaterial` (lines 300–479) was not read.
- `ItemCladding` (`common/item/ItemCladding.java`, lines 1–300 of 851): imports `getBlockStateFromMeta` and `getMetaFromBlockState`. `newStack(state, n)` and stack NBT were not read (lines 301–851).

---

## 5. Sawbench cost per shape

- `materialUsed` = input material units consumed per craft (3rd constructor argument). `itemsProduced` = shape items produced per craft (4th). Verified in `Shape.java`.
- `TileSawbench.materialMultiple()` = `factor × materialUsed`, `factor` = 2 when the input is a `BlockSlab` (prior pass; `[INFERENCE]` exact condition not re-read). `resultMultiple()` = `itemsProduced` (prior pass).
- Pages (`TileSawbench.pages`, prior pass): 0 Roofing, 1 Rounded, 2 Classical, 3 Window, 4 Arches, 5 Railings, 6 Other, 7 Glow.
- Automation (prior pass): insert only into `materialSlot`; extract only from DOWN and only if `allowAutomation` (false).

Cost is the `materialUsed` / `itemsProduced` pair in section 2's table. Examples: Roof Tile 1→2; Stairs 3→4; Stairs Outer Corner 2→3; Pole 1→16.

---

## 6. Postea / GTNH transforms

- `PosteaCompat.java` (prior pass): `addTransformationHandler("ArchitectureCraft:shape", new ItemShapeTransformer())`.
- **Mismatch:** the key `"ArchitectureCraft:shape"` is mixed case; the real registry name is `architecturecraft:shape` (section 1). `[INFERENCE]` The handler key never matches a stack's id, so item-stack transforms do not run. Postea's matching rules were not read.
- `ItemShapeTransformer.apply(originalId, stack)` (prior pass): if the tag has `BaseName`, call `TransformerRegistry.getBlockReplacement(IDRegistry.getBlockId(blockName), data, …)`; if converted, set `BaseData = converted.metadata` and `BaseName = getNameForBlock(Block.getBlockById(converted.blockID))`. Item stacks only.
- World TE: `TileShape.nbtGetBlockState` runs `TransformerRegistry.getBlockReplacement` at read time when `ArchitectureCraft.posteaLoaded` (prior pass). The rewrite is not saved to NBT until the TE is written again.
- Rules live in Postea's registry (not in this repo) `[INFERENCE]`.

---

## 7. NBT layout and example TEs

Tag types: `int` = TAG_Int, `byte` = TAG_Byte, `string` = TAG_String.

Keys written by `TileShape.writeToNBT` (prior pass, not re-verified this pass): `side`, `turn` (`TileArchitecture`), `Shape` (int = `shape.id`), `BaseName` (string), `BaseData` (int), `Disconnected` (bit layout `[INFERENCE]`), `Name2`/`Data2` (secondary), `offsetX`. `id`, `x`, `y`, `z` are the standard `TileEntity` keys `[INFERENCE]`.

Writer conditionality (when each key is written) is `[INFERENCE]`. Readers default missing tags to 0, so the examples write `side`, `turn`, and `offsetX` explicitly.

Item stack NBT: `TileShape.readFromItemStackNBT` reads `Shape`, `BaseName`, `BaseData` (prior pass). Its write side is `[INFERENCE]`.

### Example A — RoofTile on top face, upright (side 0, turn 0), birch planks

```python
nbt_roof_tile = {
    "id":       ("string", "gcewing.shape"),
    "x":        ("int", 10),          # schematic-relative
    "y":        ("int", 64),
    "z":        ("int", -5),
    "side":     ("byte", 0),
    "turn":     ("byte", 0),
    "Shape":    ("int", 0),           # Shape.RoofTile
    "BaseName": ("string", "minecraft:planks"),
    "BaseData": ("int", 2),           # birch planks
}
```

### Example B — Plain Banister on stone, side 0, turn 1, offsetX +6/16

```python
nbt_banister_plain = {
    "id":       ("string", "gcewing.shape"),
    "x":        ("int", 3),
    "y":        ("int", 70),
    "z":        ("int", 7),
    "side":     ("byte", 0),
    "turn":     ("byte", 1),
    "Shape":    ("int", 71),          # Shape.BanisterPlain
    "BaseName": ("string", "minecraft:stone"),
    "BaseData": ("int", 0),
    "offsetX":  ("byte", 6),          # 16 * 6/16 [INFERENCE: stored scale]
}
```

### Example C — Window Frame, planks base, glass-pane secondary, side 0, turn 2

```python
nbt_window_frame = {
    "id":       ("string", "gcewing.shape"),
    "x":        ("int", -2),
    "y":        ("int", 66),
    "z":        ("int", 12),
    "side":     ("byte", 0),
    "turn":     ("byte", 2),
    "Shape":    ("int", 30),          # Shape.WindowFrame
    "BaseName": ("string", "minecraft:planks"),
    "BaseData": ("int", 0),
    "Name2":    ("string", "minecraft:glass_pane"),   # Window.isValidSecondaryMaterial
    "Data2":    ("int", 0),
}
```

### Example D — Item stack NBT (no side/turn/offset/secondary)

```python
nbt_item_roof_outer_corner = {
    "Shape":    ("int", 1),           # Shape.RoofOuterCorner
    "BaseName": ("string", "minecraft:stone"),
    "BaseData": ("int", 0),
}
```

---

## 8. Quick facts and quirks

- Registry names: `architecturecraft:shape`, `architecturecraft:shapeSE`; TE id `gcewing.shape` → `TileShape`.
- Block meta 0–15 = `LIGHT` property. Orientation is never in meta.
- NBT keys: `Shape` (int id), `BaseName` (string), `BaseData` (int), `side` (byte), `turn` (byte), `offsetX` (byte), `Disconnected`, `Name2`, `Data2`.
- `side` = world direction of local −Y. `turn` = rotation about local +Y, applied **before** side (`sideRotations[s] · rotY(90t)`).
- **Quirk 1 (facing mirror):** `Vector3.facing()` (`compat/Vector3.java`, verified prior pass) returns `WEST` for `dx > 0` and `EAST` for `dx < 0`, while `directionVec(WEST)` = (−1,0,0). `[INFERENCE]` This swaps E/W for any caller that uses `facing()` on a direction vector. Affects `Trans3` helpers that call `facing()` and `BlockShape.isSideSolid`. Not tested in-world.
- **Quirk 2 (F_ aliases):** `Banister.stairsFacingMap` uses `F_WEST`, `F_EAST` `[INFERENCE: aliases to EnumFacing.EAST/WEST per prior read of Directions.java]`. Use ordinals when generating NBT.
- Tag `1.12.19` matches master on `Matrix3`, `TileShape` NBT logic, `Trans3` header, `Vector3.facing` (90–130), `ShapeKind` head, and `Shape.java` 1–300. `ItemShapeTransformer` and `TileSawbench` 300+ were not compared on 1.12.19.
