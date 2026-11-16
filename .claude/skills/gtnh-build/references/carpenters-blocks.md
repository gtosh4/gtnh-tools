> **Toolkit note (overrides §4.2 / §8 examples):** `gtnhbuild` writes cover attributes **without** the numeric
> ItemStack `id`, so `ItemStack.loadItemStackFromNBT` yields null and `Attribute.loadAttributeFromNBT` resolves the
> cover through `cbUniqueId` — portable across worlds whose numeric ids differ. Needs one in-game confirmation.
> Semantics used: a slope/stairs "facing" d (with UP) has its low side toward d and full face opposite.

# Carpenter's Blocks — TileEntity NBT & Orientation Reference

Source: `GTNewHorizons/CarpentersBlocks`, branch `master` (tree SHA `4dda8ff4d6f90403670e95d46aef0a571c79b057`). **Not** the `CarpentersBlocks-3.7.3-GTNH` tag; master may differ. Paths are relative to `src/main/java/com/carpentersblocks/`. `[INFERENCE]` = not directly observed in the fetched source.

---

## 1. Summary

- Every Carpenter's TE is a `TEBase` (or subclass). All per-block state lives in one 32-bit int `cbMetadata`, plus an attribute list `cbAttrList` (covers, dyes, overlays, illuminator, plant/soil/fertilizer, upgrade). (`tileentity/TEBase.java`)
- World block metadata is **not** the source of truth. It is only touched for cover-derived behaviour (§4.3). [INFERENCE: schematic block-meta byte does not affect TE state; set it to the cover item's damage for covered blocks.]
- Stored orientations use `ForgeDirection.ordinal()` (verified: `Torch.setDirection`, `Ladder`, `Collapsible.setDirection` store `dir.ordinal()`).

### ForgeDirection (verified)
Source: `MinecraftForge/MinecraftForge` branch `1.7.10`, `src/main/java/net/minecraftforge/common/util/ForgeDirection.java` (enum at lines 1-45; `VALID_DIRECTIONS = {DOWN, UP, NORTH, SOUTH, WEST, EAST}`; `getOrientation(id)` returns `VALID_DIRECTIONS[id]` for 0..5, else `UNKNOWN`).

| Ordinal | Name | Offset (x,y,z) | Matches task convention? |
|---|---|---|---|
| 0 | DOWN | (0,-1,0) | yes |
| 1 | UP | (0,1,0) | yes |
| 2 | NORTH | (0,0,-1) | yes (-Z) |
| 3 | SOUTH | (0,0,1) | yes (+Z) |
| 4 | WEST | (-1,0,0) | yes (-X) |
| 5 | EAST | (1,0,0) | yes (+X) |
| 6 | UNKNOWN | (0,0,0) | sentinel only |

No difference from the task convention.

---

## 2. Registry

### 2.1 Block registration
Source: `util/registry/BlockRegistry.java` (block fields and registrations, ~lines 300-585 of the file; fields and render IDs confirmed in lines 1-120).

Registry name form: Forge 1.7.10 prefixes the active mod id, so names are `CarpentersBlocks:<name>` [INFERENCE: standard Forge behaviour; `MODID = "CarpentersBlocks"` in `CarpentersBlocks.java`].

| Registry name (after `CarpentersBlocks:`) | Block class (`block/`) | Data class (`data/`) | ItemBlock | Notes |
|---|---|---|---|---|
| `blockCarpentersBarrier` | BlockCarpentersBarrier | `Barrier` | default | |
| `blockCarpentersBed` | BlockCarpentersBed | `Bed` | default | |
| `blockCarpentersBlock` | BlockCarpentersBlock | — | default [INFERENCE] | base coverable block |
| `blockCarpentersButton` | BlockCarpentersButton | `Button` | ItemBlockSided | |
| `blockCarpentersCollapsibleBlock` | BlockCarpentersCollapsibleBlock | `Collapsible` | default | |
| `blockCarpentersDaylightSensor` | BlockCarpentersDaylightSensor | `DaylightSensor` | ItemBlockSided | |
| `blockCarpentersDoor` | BlockCarpentersDoor | `Hinge` | default | uses `Hinge` bitfield |
| `blockCarpentersFlowerPot` | BlockCarpentersFlowerPot | `FlowerPot` | default | |
| `blockCarpentersGarageDoor` | BlockCarpentersGarageDoor | `GarageDoor` | default | |
| `blockCarpentersGate` | BlockCarpentersGate | `Gate` | default | |
| `blockCarpentersHatch` | BlockCarpentersHatch | `Hatch` | default | |
| `blockCarpentersLadder` | BlockCarpentersLadder | `Ladder` | default | extends `BlockSided` |
| `blockCarpentersLever` | BlockCarpentersLever | `Lever` | ItemBlockSided | |
| `blockCarpentersPressurePlate` | BlockCarpentersPressurePlate | `PressurePlate` | ItemBlockSided | |
| `blockCarpentersSafe` | BlockCarpentersSafe | `Safe` | default | TE `TECarpentersSafe` [INFERENCE: name match] |
| `blockCarpentersSlope` | BlockCarpentersSlope | `Slope` | ItemBlockCarpentersSlope | |
| `blockCarpentersStairs` | BlockCarpentersStairs | `Stairs` | default | |
| `blockCarpentersTorch` | BlockCarpentersTorch | `Torch` | ItemBlockSided | extends `BlockSided`; sets light level 1.0F |

Slab (`data/Slab.java`) is a data class with no separate registry entry captured [INFERENCE: not a standalone block here].

### 2.2 TileEntity registration (the `id` strings)
Source: `proxy/CommonProxy.java`, `init()`:

```java
GameRegistry.registerTileEntity(TEBase.class, "TileEntityCarpentersSlope");        // compat
GameRegistry.registerTileEntity(TEBase.class, "TileEntityCarpentersBed");          // compat
GameRegistry.registerTileEntity(TEBase.class, "TileEntityCarpentersBlock");
GameRegistry.registerTileEntity(TECarpentersDaylightSensor.class, "TileEntityCarpentersExt"); // compat
GameRegistry.registerTileEntity(TECarpentersDaylightSensor.class, "TileEntityCarpentersDaylightSensor");
GameRegistry.registerTileEntity(TECarpentersFlowerPot.class, "TileEntityCarpentersFlowerPot");
GameRegistry.registerTileEntity(TECarpentersSafe.class, "TileEntityCarpentersSafe");
GameRegistry.registerTileEntity(TECarpentersTorch.class, "TileEntityCarpentersTorch");
GameRegistry.registerTileEntity(TECarpentersGarageDoor.class, "TileEntityCarpentersGarageDoor");
```

**Which `id` is written on save.** `TileEntity.writeToNBT` writes the class's registered name via the class→name map that Forge fills with `TileEntity.addMapping` [INFERENCE: standard 1.7.10 Forge; a later `put` for the same class overwrites the earlier one]. `TEBase` is registered three times, so the last `TEBase` entry (`TileEntityCarpentersBlock`) is the one written. The same logic applies to `TECarpentersDaylightSensor`.

| TE class | Written `id` | Also readable as |
|---|---|---|
| `TEBase` | `TileEntityCarpentersBlock` | `TileEntityCarpentersSlope`, `TileEntityCarpentersBed` |
| `TECarpentersDaylightSensor` | `TileEntityCarpentersDaylightSensor` | `TileEntityCarpentersExt` |
| `TECarpentersFlowerPot` | `TileEntityCarpentersFlowerPot` | — |
| `TECarpentersSafe` | `TileEntityCarpentersSafe` | — |
| `TECarpentersTorch` | `TileEntityCarpentersTorch` | — |
| `TECarpentersGarageDoor` | `TileEntityCarpentersGarageDoor` | — |

Which TE class each block creates:
- Torch → `TECarpentersTorch` (`block/BlockCarpentersTorch.java`, `createNewTileEntity`).
- Other blocks: `BlockCoverable.createNewTileEntity` was not captured (lines 1-300 and 1380-1433 of the file were read; the middle section was not). The default `TEBase` is inferred for Slope, Stairs, Ladder, Barrier, Gate, Hatch, Door, Collapsible, and Block [INFERENCE: no other TE class is registered for these data families].
- Safe, GarageDoor, FlowerPot, DaylightSensor → their named TE classes [INFERENCE: name match; their block files were not read].

---

## 3. TileEntity NBT layout (`TEBase.writeToNBT`)

Source: `tileentity/TEBase.java` (tag constants ~lines 24-29; attr IDs ~31-41; `writeToNBT`, `readFromNBT`, `addAttribute`, `getData/setData` in the body).

### 3.1 Tags

| Tag | Type | Meaning | Notes |
|---|---|---|---|
| `id` | String | TE registry name (§2.2) | vanilla `TileEntity.writeToNBT` [INFERENCE] |
| `x`,`y`,`z` | Int | world coords (schematic-relative when pasted) | vanilla [INFERENCE] |
| `cbMetadata` | Int | per-block state word (§5) | written as Int |
| `cbAttrList` | List<Compound> | attributes (§4) | list always written [INFERENCE: may be empty] |
| `cbChiselDesign_0`..`cbChiselDesign_6` | String | per-side chisel design | written by `writeToNBT` [INFERENCE: may be `""`] |
| `cbDesign` | String | design name | written |
| `cbOwner` | String | owner name | written |

`TAG_*` constants in `TEBase.java`: `TAG_ATTR="cbAttribute"`, `TAG_ATTR_LIST="cbAttrList"`, `TAG_METADATA="cbMetadata"`, `TAG_OWNER="cbOwner"`, `TAG_CHISEL_DESIGN="cbChiselDesign"`, `TAG_DESIGN="cbDesign"`.

### 3.2 Reader rules (`readFromNBT`)
1. If `nbt.hasKey("owner")` → legacy path `TileEntityHelper.updateMappingsOnRead` (§7). Otherwise the new path.
2. `cbAttrList` read as tag list type 10 (compound). Each entry: `cbAttribute` (byte) = attr index; `Attribute.loadAttributeFromNBT` (§4.1). Stack size forced to 1.
3. `cbChiselDesign_0..6` read as strings.
4. `cbMetadata`: `convertDataToInt` accepts NBTTagShort (pre-3.3.7) and NBTTagInt.
5. `cbDesign`, `cbOwner` read as strings.

### 3.3 Attribute indices (`TEBase`, ~lines 31-41)

| Constant | Value | Meaning |
|---|---|---|
| `ATTR_COVER[0..5]` | 0..5 | cover on side DOWN, UP, NORTH, SOUTH, WEST, EAST |
| `ATTR_COVER[6]` | 6 | full-block cover |
| `ATTR_DYE[0..6]` | 7..13 | dye per side (7 = side 0 … 13 = full) |
| `ATTR_OVERLAY[0..6]` | 14..20 | overlay per side |
| `ATTR_ILLUMINATOR` | 21 | illuminator |
| `ATTR_PLANT` | 22 | flower pot plant |
| `ATTR_SOIL` | 23 | flower pot soil |
| `ATTR_FERTILIZER` | 24 | flower pot fertilizer |
| `ATTR_UPGRADE` | 25 | safe upgrade (54 slots when present) |

Side indexes 0..5 match `ForgeDirection` ordinals [INFERENCE: consistent with the `[DOWN, UP, NORTH, SOUTH, WEST, EAST]` face arrays in `data/Slope.java`].

### 3.4 Other TE NBT
- `TECarpentersSafe` adds `Items`: TagList (compound 10) of `{"Slot": ("byte", i), <vanilla ItemStack fields>}` for each non-null slot 0..53. Slot read with `& 255`. (`tileentity/TECarpentersSafe.java`.)
- `TECarpentersTorch`, `TECarpentersGarageDoor`, `TECarpentersFlowerPot`, `TECarpentersDaylightSensor` override only client packet/tick logic (`onDataPacket`, `updateEntity`, `getDynamicLightValue`). They add no NBT keys. Verified.

---

## 4. Covers and attributes

### 4.1 Attribute entry layout (`util/Attribute.java`)

`Attribute.writeToNBT(nbt)`:
- Calls `_itemStack.writeToNBT(nbt)` (vanilla ItemStack fields; §4.2).
- Adds `cbUniqueId` (String) = `GameRegistry.findUniqueIdentifierFor(item).toString()`, e.g. `"minecraft:stonebrick"`.
- `TEBase.writeToNBT` adds `cbAttribute` (Byte) = attr index (§3.3).

`Attribute.loadAttributeFromNBT(nbt)`:
- Calls `ItemStack.loadItemStackFromNBT(nbt)`. If null, falls back to `GameRegistry.findItemStack(modId, name, 1)` using `cbUniqueId`, with `Damage` (Short).
- Logs on failure.

So each attribute compound = **vanilla ItemStack fields + `cbAttribute` + `cbUniqueId`**. The reader prefers numeric `id` and falls back to `cbUniqueId`.

### 4.2 Vanilla ItemStack fields (1.7.10) [INFERENCE]
Vanilla `ItemStack.writeToNBT` writes `id` (Short, `Item.getIdFromItem`), `Count` (Byte), `Damage` (Short), and optional `tag` (Compound). Not re-verified against MCP source in this pass.

**Emitter recommendation:** write `id` (Short), `Count` (Byte 1), `Damage` (Short), and `cbUniqueId` (String). Importers should prefer `cbUniqueId` for portability (the numeric id is world-specific) [INFERENCE].

### 4.3 Cover side mapping
- Cover on side `s` (0..5) → `cbAttrList` entry with `cbAttribute = s`.
- Full-block cover → `cbAttribute = 6`.
- `TEBase.addAttribute` for `ATTR_COVER[6]` sets the world block metadata to `itemStack.getItemDamage()`. World meta is not persisted in the TE. [INFERENCE: schematic block-meta byte should equal that damage for correct rendering.]

### 4.4 `addAttribute` side effects
- Attr < 7 calls `notifyBlocksOfNeighborChange` (`TEBase.java`). Not relevant to NBT.

### 4.5 Metadata swap
`TEBase.setMetadata/restoreMetadata` temporarily swap world metadata for lighting. Not persisted.

---

## 5. Per-block `cbMetadata` encodings

Source per block: `data/<Name>.java` (bit comments in each class).

### 5.1 Slope (`data/Slope.java`) — whole `cbMetadata` = `slopeID` (0..64)
Constructors (`Slope.java` static block, lines ~100-678 of the file) give exact facings. `slopesList = new Slope[65]`. `getSlope` and `getSlopeById` reset IDs ≥ 65 to 0. `isPositive = facings.contains(UP)`.

| ID | Constant | Type | Facings |
|---|---|---|---|
| 0 | `ID_WEDGE_SE` | WEDGE_SIDE | SOUTH, EAST |
| 1 | `ID_WEDGE_NW` | WEDGE_SIDE | NORTH, WEST |
| 2 | `ID_WEDGE_NE` | WEDGE_SIDE | NORTH, EAST |
| 3 | `ID_WEDGE_SW` | WEDGE_SIDE | SOUTH, WEST |
| 4 | `ID_WEDGE_NEG_N` | WEDGE | DOWN, NORTH |
| 5 | `ID_WEDGE_NEG_S` | WEDGE | DOWN, SOUTH |
| 6 | `ID_WEDGE_NEG_W` | WEDGE | DOWN, WEST |
| 7 | `ID_WEDGE_NEG_E` | WEDGE | DOWN, EAST |
| 8 | `ID_WEDGE_POS_N` | WEDGE | UP, NORTH |
| 9 | `ID_WEDGE_POS_S` | WEDGE | UP, SOUTH |
| 10 | `ID_WEDGE_POS_W` | WEDGE | UP, WEST |
| 11 | `ID_WEDGE_POS_E` | WEDGE | UP, EAST |
| 12 | `ID_WEDGE_INT_NEG_SE` | WEDGE_INT | DOWN, SOUTH, EAST |
| 13 | `ID_WEDGE_INT_NEG_NW` | WEDGE_INT | DOWN, NORTH, WEST |
| 14 | `ID_WEDGE_INT_NEG_NE` | WEDGE_INT | DOWN, NORTH, EAST |
| 15 | `ID_WEDGE_INT_NEG_SW` | WEDGE_INT | DOWN, SOUTH, WEST |
| 16 | `ID_WEDGE_INT_POS_SE` | WEDGE_INT | UP, SOUTH, EAST |
| 17 | `ID_WEDGE_INT_POS_NW` | WEDGE_INT | UP, NORTH, WEST |
| 18 | `ID_WEDGE_INT_POS_NE` | WEDGE_INT | UP, NORTH, EAST |
| 19 | `ID_WEDGE_INT_POS_SW` | WEDGE_INT | UP, SOUTH, WEST |
| 20 | `ID_WEDGE_EXT_NEG_SE` | WEDGE_EXT | DOWN, SOUTH, EAST |
| 21 | `ID_WEDGE_EXT_NEG_NW` | WEDGE_EXT | DOWN, NORTH, WEST |
| 22 | `ID_WEDGE_EXT_NEG_NE` | WEDGE_EXT | DOWN, NORTH, EAST |
| 23 | `ID_WEDGE_EXT_NEG_SW` | WEDGE_EXT | DOWN, SOUTH, WEST |
| 24 | `ID_WEDGE_EXT_POS_SE` | WEDGE_EXT | UP, SOUTH, EAST |
| 25 | `ID_WEDGE_EXT_POS_NW` | WEDGE_EXT | UP, NORTH, WEST |
| 26 | `ID_WEDGE_EXT_POS_NE` | WEDGE_EXT | UP, NORTH, EAST |
| 27 | `ID_WEDGE_EXT_POS_SW` | WEDGE_EXT | UP, SOUTH, WEST |
| 28 | `ID_OBL_INT_NEG_SE` | OBLIQUE_INT | DOWN, SOUTH, EAST |
| 29 | `ID_OBL_INT_NEG_NW` | OBLIQUE_INT | DOWN, NORTH, WEST |
| 30 | `ID_OBL_INT_NEG_NE` | OBLIQUE_INT | DOWN, NORTH, EAST |
| 31 | `ID_OBL_INT_NEG_SW` | OBLIQUE_INT | DOWN, SOUTH, WEST |
| 32 | `ID_OBL_INT_POS_SE` | OBLIQUE_INT | UP, SOUTH, EAST |
| 33 | `ID_OBL_INT_POS_NW` | OBLIQUE_INT | UP, NORTH, WEST |
| 34 | `ID_OBL_INT_POS_NE` | OBLIQUE_INT | UP, NORTH, EAST |
| 35 | `ID_OBL_INT_POS_SW` | OBLIQUE_INT | UP, SOUTH, WEST |
| 36 | `ID_OBL_EXT_NEG_SE` | OBLIQUE_EXT | DOWN, SOUTH, EAST |
| 37 | `ID_OBL_EXT_NEG_NW` | OBLIQUE_EXT | DOWN, NORTH, WEST |
| 38 | `ID_OBL_EXT_NEG_NE` | OBLIQUE_EXT | DOWN, NORTH, EAST |
| 39 | `ID_OBL_EXT_NEG_SW` | OBLIQUE_EXT | DOWN, SOUTH, WEST |
| 40 | `ID_OBL_EXT_POS_SE` | OBLIQUE_EXT | UP, SOUTH, EAST |
| 41 | `ID_OBL_EXT_POS_NW` | OBLIQUE_EXT | UP, NORTH, WEST |
| 42 | `ID_OBL_EXT_POS_NE` | OBLIQUE_EXT | UP, NORTH, EAST |
| 43 | `ID_OBL_EXT_POS_SW` | OBLIQUE_EXT | UP, SOUTH, WEST |
| 44 | `ID_PRISM_NEG` | PRISM | DOWN |
| 45 | `ID_PRISM_POS` | PRISM | UP |
| 46 | `ID_PRISM_1P_POS_N` | PRISM_1P | UP, NORTH |
| 47 | `ID_PRISM_1P_POS_S` | PRISM_1P | UP, SOUTH |
| 48 | `ID_PRISM_1P_POS_W` | PRISM_1P | UP, WEST |
| 49 | `ID_PRISM_1P_POS_E` | PRISM_1P | UP, EAST |
| 50 | `ID_PRISM_2P_POS_NS` | PRISM_2P | UP, NORTH, SOUTH |
| 51 | `ID_PRISM_2P_POS_WE` | PRISM_2P | UP, WEST, EAST |
| 52 | `ID_PRISM_2P_POS_SE` | PRISM_2P | UP, SOUTH, EAST |
| 53 | `ID_PRISM_2P_POS_NW` | PRISM_2P | UP, NORTH, WEST |
| 54 | `ID_PRISM_2P_POS_NE` | PRISM_2P | UP, NORTH, EAST |
| 55 | `ID_PRISM_2P_POS_SW` | PRISM_2P | UP, SOUTH, WEST |
| 56 | `ID_PRISM_3P_POS_NWE` | PRISM_3P | UP, NORTH, WEST, EAST |
| 57 | `ID_PRISM_3P_POS_SWE` | PRISM_3P | UP, SOUTH, WEST, EAST |
| 58 | `ID_PRISM_3P_POS_NSW` | PRISM_3P | UP, NORTH, SOUTH, WEST |
| 59 | `ID_PRISM_3P_POS_NSE` | PRISM_3P | UP, NORTH, SOUTH, EAST |
| 60 | `ID_PRISM_POS_4P` | PRISM_4P | UP, NORTH, SOUTH, WEST, EAST |
| 61 | `ID_PRISM_WEDGE_POS_N` | PRISM_WEDGE | UP, NORTH |
| 62 | `ID_PRISM_WEDGE_POS_S` | PRISM_WEDGE | UP, SOUTH |
| 63 | `ID_PRISM_WEDGE_POS_W` | PRISM_WEDGE | UP, WEST |
| 64 | `ID_PRISM_WEDGE_POS_E` | PRISM_WEDGE | UP, EAST |

Static field names differ from ID constant names in a few places (e.g. `PRISM_3P_POS_WEN` uses `ID_PRISM_3P_POS_NWE`; `WEDGE_POS_S` → 9). The numeric IDs are authoritative, and each row's facings come from the constructor passing that ID.

Face-shape array order: `[DOWN, UP, NORTH, SOUTH, WEST, EAST]` (`Slope.java` field comment).

Hammer: `BlockCarpentersSlope` right-click cycles `slopeType.getNextSlopeType(slope)` and calls `TE.setData(newSlope.slopeID)`.

Placement-time orientation (`onBlockPlacedBy`, `BlockCarpentersSlope.java` lines 300-505) was **not** read.

### 5.2 Stairs (`data/Stairs.java`) — whole `cbMetadata` = stairs ID (0..27)
`stairsList = new Stairs[28]`.

| ID | Type | Name |
|---|---|---|
| 0–3 | NORMAL_SIDE | SE, NW, NE, SW |
| 4–7 | NORMAL NEG | NEG_N, NEG_S, NEG_W, NEG_E |
| 8–11 | NORMAL POS | POS_N, POS_S, POS_W, POS_E |
| 12–15 | INT NEG | NEG_SE, NEG_NW, NEG_NE, NEG_SW |
| 16–19 | INT POS | POS_SE, POS_NW, POS_NE, POS_SW |
| 20–23 | EXT NEG | NEG_SE, NEG_NW, NEG_NE, NEG_SW |
| 24–27 | EXT POS | POS_SE, POS_NW, POS_NE, POS_SW |

Face shape constants: NO_FACE=0, FULL=1, STAGGERED=2. Staggered corners: MIN_MIN=1, MIN_MAX=2, MAX_MIN=3, MAX_MAX=4 (`Stairs.java`).

Hammer (`block/BlockCarpentersStairs.java`): NORMAL_SIDE adds 8; NORMAL/INT/EXT positive → `-=4`, negative → `+=12` (EXT negative → 0). `onBlockPlaced` returns side+2 / side+6 / 12-13 for top/bottom placement.

### 5.3 Collapsible (`data/Collapsible.java`)
32-bit `cbMetadata`:

| Field | Bits | Mask | Range |
|---|---|---|---|
| XZNN quad depth | 22..18 | `0x7c0000` | 0..16 |
| XZNP quad depth | 17..13 | `0x3e000` | 0..16 |
| XZPN quad depth | 12..8 | `0x1f00` | 0..16 |
| XZPP quad depth | 7..3 | `0xf8` | 0..16 |
| Direction (ForgeDirection ordinal) | 2..0 | `0x7` | 0..5 |

Quad constants: QUAD_XZNN=0, XZNP=1, XZPN=2, XZPP=3. `setQuadDepth` rejects <0 or >16; `getQuadDepth` clamps to 16. `isPositive` = dir==UP. Side-solidity: DOWN → true; UP → `CollapsibleUtil.isMax(TE)`; NORTH: XZNN+XZPN==32; SOUTH: XZNP+XZPP==32; WEST: XZNP+XZNN==32; EAST: XZPN+XZPP==32.

### 5.4 Slab (`data/Slab.java`)

| Value | Meaning |
|---|---|
| 0 | BLOCK_FULL |
| 1 | X_NEG |
| 2 | X_POS |
| 3 | Y_NEG |
| 4 | Y_POS |
| 5 | Z_NEG |
| 6 | Z_POS |

`DIR_MAP = {4,5,0,1,2,3}`. `getDirection = ForgeDirection.getOrientation(DIR_MAP[data-1])` [INFERENCE on mapping meaning beyond the file comment].

### 5.5 Barrier (`data/Barrier.java`)
`[Unused][Post 1 @ bit4][Type 4 @ bits0-3]`

| Field | Mask | Values |
|---|---|---|
| Type | `0xf` | 0 VANILLA, 1 VANILLA_X1, 2 VANILLA_X2, 3 VANILLA_X3, 4 PICKET, 5 SHADOWBOX, 6 WALL |
| Post | `0x10` | 0 NO_POST, 1 HAS_POST |

### 5.6 Gate (`data/Gate.java`)
`[Unused][State 1 @ bit6][Facing 1 @ bit5][OpenDir 1 @ bit4][Type 4 @ bits0-3]`

| Field | Mask | Values |
|---|---|---|
| Type | `0xf` | same as Barrier |
| OpenDir | `0x10` | 0 DIR_POS, 1 DIR_NEG |
| Facing | `0x20` | 0 FACING_ON_X, 1 FACING_ON_Z |
| State | `0x40` | 0 CLOSED, 1 OPEN |

### 5.7 Hatch (`data/Hatch.java`)
`[Unused][Rigid 1 @ bit7][Dir 2 @ bits5-6][State 1 @ bit4][Position 1 @ bit3][Type 3 @ bits0-2]`

| Field | Mask | Values |
|---|---|---|
| Type | `0x7` | 0 HIDDEN, 1 WINDOW, 2 SCREEN, 3 FRENCH_WINDOW, 4 PANEL |
| Position | `0x8` | 0 LOW, 1 HIGH |
| State | `0x10` | 0 CLOSED, 1 OPEN |
| Dir | `0x60` | 0 Z_NEG, 1 Z_POS, 2 X_NEG, 3 X_POS |
| Rigidity | `0x80` | 0 NONRIGID, 1 RIGID |

### 5.8 Hinge (`data/Hinge.java`) — used by the Door block
`[Unused][Rigid 1 @ bit8][Piece 1 @ bit7][State 1 @ bit6][Facing 2 @ bits4-5][Hinge 1 @ bit3][Type 3 @ bits0-2]`

| Field | Mask | Values |
|---|---|---|
| Type | `0x7` | 0 GLASS_TOP, 1 GLASS_TALL, 2 PANELS, 3 SCREEN_TALL, 4 FRENCH_GLASS, 5 HIDDEN |
| Hinge | `0x8` | 0 LEFT, 1 RIGHT |
| Facing | `0x30` | 0 XP, 1 ZP, 2 XN, 3 ZN |
| State | `0x40` | 0 CLOSED, 1 OPEN |
| Piece | `0x80` | 0 BOTTOM, 1 TOP |
| Rigidity | `0x100` | 0 NONRIGID, 1 RIGID |

### 5.9 Ladder (`data/Ladder.java`)
`[Unused][Type 4 @ bits3-6][Dir 3 @ bits0-2]`

| Field | Mask | Values |
|---|---|---|
| Dir | `0x7` | ForgeDirection ordinal. 0 (DOWN) = DIR_ON_X and 1 (UP) = DIR_ON_Z for freestanding; 2..5 = wall-mounted on NORTH/SOUTH/WEST/EAST |
| Type | `0x78` | 0 DEFAULT, 1 RAIL, 2 POLE |

`isFreestanding` = `ordinal < 2`.

### 5.10 Torch (`data/Torch.java`)
`[Unused][Type 4 @ bits5-8][State 2 @ bits3-4][Dir 3 @ bits0-2]`

| Field | Mask | Values |
|---|---|---|
| Dir | `0x7` | ForgeDirection ordinal of the **mounting face** (the wall it attaches to). Head placement (`getHeadCoordinates`): NORTH → head at `z+0.27`, SOUTH → `z-0.27`, WEST → `x+0.27`, EAST → `x-0.27`; `default` (includes **UP and DOWN**) → floor-standing head at block centre |
| State | `0x18` | `State` enum ordinal: 0 LIT, 1 SMOLDERING, 2 UNLIT (`setState` stores `ordinal << 3`; `getState` maps 0/1 to LIT/SMOLDERING, anything else UNLIT) |
| Type | `0x1e0` | 0 VANILLA, 1 LANTERN (`setType` stores `(type & 0xf) << 5`) |

Verified from `data/Torch.java` (`getHeadCoordinates`, `getState`, `setState`, `setType`).

---

## 6. Python-dict-friendly tables

```python
# ForgeDirection ordinals (verified; ForgeDirection.java)
FORGE_DIR = {"DOWN": 0, "UP": 1, "NORTH": 2, "SOUTH": 3, "WEST": 4, "EAST": 5}

# Attribute indices (TEBase)
ATTR_COVER = [0, 1, 2, 3, 4, 5, 6]     # index 6 = full-block
ATTR_DYE = [7, 8, 9, 10, 11, 12, 13]
ATTR_OVERLAY = [14, 15, 16, 17, 18, 19, 20]
ATTR_ILLUMINATOR = 21
ATTR_PLANT = 22
ATTR_SOIL = 23
ATTR_FERTILIZER = 24
ATTR_UPGRADE = 25

# TE ids written on save
TE_ID = {
    "TEBase": "TileEntityCarpentersBlock",
    "DaylightSensor": "TileEntityCarpentersDaylightSensor",
    "FlowerPot": "TileEntityCarpentersFlowerPot",
    "Safe": "TileEntityCarpentersSafe",
    "Torch": "TileEntityCarpentersTorch",
    "GarageDoor": "TileEntityCarpentersGarageDoor",
}

# Torch cbMetadata
TORCH_DIR_MASK = 0x7; TORCH_STATE_SHIFT = 3; TORCH_TYPE_SHIFT = 5
TORCH_STATE = {"LIT": 0, "SMOLDERING": 1, "UNLIT": 2}
TORCH_TYPE = {"VANILLA": 0, "LANTERN": 1}

# Ladder cbMetadata
LADDER_TYPE = {"DEFAULT": 0, "RAIL": 1, "POLE": 2}   # shift 3, mask 0x78

# Slab cbMetadata
SLAB = {"BLOCK_FULL": 0, "X_NEG": 1, "X_POS": 2, "Y_NEG": 3, "Y_POS": 4, "Z_NEG": 5, "Z_POS": 6}

# Collapsible cbMetadata
COLLAPSIBLE_SHIFTS = {"XZNN": 18, "XZNP": 13, "XZPN": 8, "XZPP": 3}  # 5-bit fields, 0..16
COLLAPSIBLE_DIR_MASK = 0x7

# Slope cbMetadata = ID 0..64 (see §5.1); Stairs cbMetadata = ID 0..27 (see §5.2)
```

---

## 7. Migration (`readFromNBT`)

- **Legacy gate:** `nbt.hasKey("owner")` → `TileEntityHelper.updateMappingsOnRead` (`tileentity/TileEntityHelper.java`). Keys: `metadata`, `owner`, `design`, `chiselDesign_0..6`, `itemstacks` (list of compounds with `cover`/`dye`/`overlay`/`illuminator`), `pot_property` (list with `soil`/`plant`).
- **`cbMetadata` type:** NBTTagShort (pre-3.3.7) → `convertDataToInt`.
- **Safe upgrade:** `inventorySize > 27` → `ATTR_UPGRADE` with iron ingot (`TECarpentersSafe.readFromNBT`).
- **Slope range:** `getSlope` resets IDs ≥ 65 to 0 and logs (`Slope.java`).

---

## 8. Example NBTs

Notation: `("type", value)`. A list is `("list", ("compound", [...]))`. Coordinates are schematic-relative.

### 8.1 Stone-brick full-cover wedge slope, WEDGE POS_S (ID 9)
Block: `CarpentersBlocks:blockCarpentersSlope`. Facings UP + SOUTH. The schematic block-meta byte should be set to the stonebrick damage (0) per §4.3.

```python
slope_te = {
    "id":           ("string", "TileEntityCarpentersBlock"),
    "x":            ("int", 10),
    "y":            ("int", 64),
    "z":            ("int", -20),
    "cbMetadata":   ("int", 9),                 # ID_WEDGE_POS_S (UP, SOUTH)
    "cbAttrList": ("list", ("compound", [
        {
            "cbAttribute": ("byte", 6),         # ATTR_COVER[6] = full-block cover
            "id":          ("short", 98),       # numeric id — world-specific [INFERENCE]
            "Count":       ("byte", 1),
            "Damage":      ("short", 0),
            "cbUniqueId":  ("string", "minecraft:stonebrick"),
        },
    ])),
    "cbDesign":     ("string", ""),
    "cbOwner":      ("string", ""),
}
```

### 8.2 Lantern torch on the north wall, LIT, type LANTERN
Block: `CarpentersBlocks:blockCarpentersTorch`. `cbMetadata = dir(NORTH=2) | (LIT=0)<<3 | (LANTERN=1)<<5 = 34`.

```python
torch_te = {
    "id":           ("string", "TileEntityCarpentersTorch"),
    "x":            ("int", 5),
    "y":            ("int", 70),
    "z":            ("int", 12),
    "cbMetadata":   ("int", 34),                # 2 | (0 << 3) | (1 << 5)
    "cbAttrList":   ("list", ("compound", [])), # no covers
    "cbDesign":     ("string", ""),
    "cbOwner":      ("string", ""),
}
```

### 8.3 Minimum NBT for any covered block
Required: `id`, `x`, `y`, `z`, `cbMetadata`. One `cbAttrList` entry per covered side with `cbAttribute` and `cbUniqueId`; `id`, `Count`, `Damage` are recommended. `readFromNBT` reads `cbChiselDesign_*`, `cbDesign`, `cbOwner` as optional [INFERENCE: missing `getString` keys yield `""`].

---

## 9. Open items / gaps

1. `BlockCoverable.createNewTileEntity` (middle section of `block/BlockCoverable.java`) not captured; default TE `TEBase` for non-Torch/Safe blocks is inferred.
2. Vanilla ItemStack NBT field types (§4.2) not verified against MCP source.
3. Placement-time orientation (`onBlockPlacedBy`) for Slope (`BlockCarpentersSlope.java` 300-505) and Stairs (`BlockCarpentersStairs.java` 300-422) not read; `cbMetadata` values above are the stored state, not placement logic.
4. Barrier/Gate/Hatch/Door/Ladder placement logic not read beyond the §5 bit definitions. Safe/GarageDoor/FlowerPot/DaylightSensor block files not read.
5. Data is from `master`, not the `3.7.3-GTNH` tag.

---

## 10. Geometry semantics

Source: `GTNewHorizons/CarpentersBlocks` `master` (tree `4dda8ff`), paths under `src/main/java/com/carpentersblocks/`. `[INFERENCE]` = not directly observed.

Coordinates: +X East, -Z North, +Y Up. Face arrays `[DOWN, UP, NORTH, SOUTH, WEST, EAST]`. Boxes `{minX,minY,minZ,maxX,maxY,maxZ}`, block-local 0..1.

### 10.1 Slope geometry, IDs 0–11

Facings are from §5.1 (`data/Slope.java`). The solid faces are derived from the face arrays [INFERENCE]: a `FULL` face is solid, and the sloped surface's outward normal points toward the open horizontal and vertical facings.

| ID | Constant | Facings | Solid (FULL) faces | Notes |
|---|---|---|---|---|
| 0 | `ID_WEDGE_SE` | SOUTH, EAST | NORTH, WEST | WEDGE_SIDE, vertical diagonal |
| 1 | `ID_WEDGE_NW` | NORTH, WEST | SOUTH, EAST | WEDGE_SIDE |
| 2 | `ID_WEDGE_NE` | NORTH, EAST | SOUTH, WEST | WEDGE_SIDE |
| 3 | `ID_WEDGE_SW` | SOUTH, WEST | NORTH, EAST | WEDGE_SIDE |
| 4 | `ID_WEDGE_NEG_N` | DOWN, NORTH | UP, SOUTH | WEDGE, thin edge on top, north |
| 5 | `ID_WEDGE_NEG_S` | DOWN, SOUTH | UP, NORTH | WEDGE |
| 6 | `ID_WEDGE_NEG_W` | DOWN, WEST | UP, EAST | WEDGE |
| 7 | `ID_WEDGE_NEG_E` | DOWN, EAST | UP, WEST | WEDGE |
| 8 | `ID_WEDGE_POS_N` | UP, NORTH | DOWN, SOUTH | WEDGE, low edge north, high edge south |
| 9 | `ID_WEDGE_POS_S` | UP, SOUTH | DOWN, NORTH | WEDGE |
| 10 | `ID_WEDGE_POS_W` | UP, WEST | DOWN, EAST | WEDGE |
| 11 | `ID_WEDGE_POS_E` | UP, EAST | DOWN, WEST | WEDGE |

ID 8 (`WEDGE_POS_N`): the solid region is `y <= z` in block-local coordinates [INFERENCE from the face array]. This matches the user's example.

Per-ID collision boxes (`SlopeUtil` bounds) were not read. The table is inferred from face shapes only. WEDGE_SIDE (0–3) differ from WEDGE (4–11) in their DOWN/UP faces [INFERENCE]. The INT/EXT/OBLIQUE/PRISM families (12–64) were not analysed beyond §5.1.

### 10.2 Stairs tall half

Source: `util/stairs/StairsUtil.java` `genBounds`. Box 1 is the full-height half (`minY=0, maxY=1`) for every stairs type. Observed:

| Stairs | Tall half | Low step |
|---|---|---|
| `NORMAL_POS_N` (8) | south (+Z) | north (−Z) quarter |

Other IDs were NOT read. Take their tall-half direction from `StairsUtil.genBounds` before use. INT/EXT corner orientation is `[INFERENCE]` until checked.

### 10.3 Placement ID: player facing north, placed on ground

Assumptions: player yaw 180° (facing north), clicks the top face of the ground block (`side = 1`).

Yaw → rotation: `rot = floor(yaw*4/360 + 0.5) & 3` (`util/EntityLivingUtil.getRotationValue`). For 180° → `rot = 2` [INFERENCE: MC yaw 0 faces south].

**Stairs** (`block/BlockCarpentersStairs.java` `onBlockPlacedBy`):
1. `onBlockPlaced(side=1)` returns 13 (§5.2 placement note).
2. `facing = rot = 2` → mapping 0→N, 1→E, 2→S, 3→W [INFERENCE from the switch].
3. Stairs ID 13 falls in the `POS`/`NEG` switch: `case 2` → `ID_NORMAL_POS_S` = **9**.
4. Not sneaking → `StairsTransform.transformStairs` (`util/stairs/StairsTransform.java`) finds no neighbours, so the ID stays 9.

Result: **9 (`NORMAL_POS_S`)**. For a bottom-face click (`side = 0`), `onBlockPlaced` returns 12 → `NEG_S` = **5** [INFERENCE from the same switch].

**Slope** (`block/BlockCarpentersSlope.java` `onBlockPlacedBy`):
1. `eventFace = 1` (top) → positive.
2. `dir = EntityLivingUtil.getFacing(entity).getOpposite()`. `getFacing = getRotationFacing(rot).getOpposite()`, and `getRotationFacing(2) = ForgeDirection.getOrientation(Direction.directionToFacing[2])`. `Direction.directionToFacing[2] = NORTH` [INFERENCE: vanilla `{3,4,2,5}`]. So `dir = NORTH`.
3. `getWedgeOrientation(NORTH, positive)` → `WEDGE_POS_S` = **9**.
4. Not sneaking → `SlopeTransform.transformWedge` (`util/slope/SlopeTransform.java`) finds no neighbours, so the ID stays 9.

Result: **9 (`WEDGE_POS_S`)**, the same as stairs. For a bottom-face click, the slope becomes `NEG_S` = **5** [INFERENCE].

### 10.4 TE class per block

`block/BlockCoverable.java`:
- `createNewTileEntity(World, int)` returns `new TEBase()`.
- `hasTileEntity(int)` returns `true`.
- `onBlockAdded` sets the TE via `createNewTileEntity`.

`BlockCarpentersSlope` and `BlockCarpentersStairs` were read and do not override `createNewTileEntity`. So both create `TEBase`, written as `id` `TileEntityCarpentersBlock` (§2.2).

Torch overrides to `TECarpentersTorch` (§2.2). `BlockCarpentersBlock` and `BlockCarpentersCollapsibleBlock` were not read. Their TE is `TEBase` [INFERENCE: no override seen in `BlockCoverable`].

### 10.5 Tag `3.7.3-GTNH` versus master

Source: GitHub compare, `3.7.3-GTNH...master`.
- `3.7.3-GTNH` and `3.8.0-GTNH` both point at `0ef22db308928e53fb67bccb5647af7d5e744556`.
- Master `4dda8ff4d6f90403670e95d46aef0a571c79b057` is one commit ahead of the tag. That commit changes only `.github/workflows/build-and-test.yml` (CI branch filter).

**No `src/` difference.** `TEBase`, `Attribute`, `Slope`, `Stairs` are identical between the tag and master. The §1 caveat is resolved for source.

### 10.6 `GameRegistry.findItemStack` and `ItemStack.loadItemStackFromNBT`

- FML `cpw/mods/fml/common/registry/GameRegistry.java` `findItemStack`: calls `GameData.findItemStack`. If found, returns a copy clamped to the max stack size. If not found, returns `null`. Its javadoc says default Block/Item stacks are created when no explicit entry exists. That fallback is in `GameData`, which was not read [INFERENCE]. So a registered name gives a default stack; an unknown name gives `null`.
- Vanilla `ItemStack.loadItemStackFromNBT`: read from the 1.8.9 mirror (`Marcelektro/MavenMCP-1.8.9`, `ItemStack.java`). It creates a stack, calls `readFromNBT`, and returns `null` when `getItem()==null`. Without `id`, the item is null and the result is `null`. The 1.7.10 source was not retrieved, so this is [INFERENCE] for 1.7.10. This is why §4.1 falls back to `cbUniqueId`.

### 10.7 Answers

| # | Question | Answer | Basis |
|---|---|---|---|
| 1 | Slope geometry IDs 0–11 | §10.1 table; ID 8 = `y <= z` | Face arrays, `Slope.java` [INFERENCE] |
| 2 | Stairs tall half, POS_N, NEG_N, INT/EXT | POS_N: tall south; other IDs not read | `StairsUtil.genBounds` |
| 3 | Placed ID, north-facing player on ground | Stairs 9, Slope 9 (top click); 5 for bottom click | `onBlockPlacedBy`, transforms; yaw convention [INFERENCE] |
| 4 | TE class for slope/stairs/block/collapsible | `TEBase` for slope/stairs; block/collapsible [INFERENCE] | `BlockCoverable.createNewTileEntity` |
| 5 | Tag `3.7.3-GTNH` vs master | No `src/` difference; master differs by one CI workflow commit | GitHub compare |
| 6 | `findItemStack` fallback, null when `id` absent | Null when unregistered; default stack per javadoc; `loadItemStackFromNBT` null without `id` (1.8.9) | FML `GameRegistry`, MavenMCP 1.8.9 [INFERENCE] for 1.7.10 |
