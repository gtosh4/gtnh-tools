---
name: gtnh-build
description: Design GTNH 2.9 buildings with the gtnhbuild Python toolkit — pick blocks from blocks.db, script the build, preview it (iso PNG, layer slices, ASCII, 3D HTML), and export a .schematic for WorldEdit / Schematica. Covers ArchitectureCraft shapes and Carpenter's Blocks.
---

Use for any request to design, sketch, modify, or cost a structure (house, hall, tower, roof, base facade, decor) for the user's GTNH 2.9 world "Threshold". Not for GT multiblock layouts — StructureLib's hologram projector already places those in game.

## Workflow

1. **Brief.** Get the footprint, height, style, palette and tier constraints. Work out the coordinates before writing code. Convention: +x = east, +y = up, +z = south, and build (0,0,0) is the paste anchor (the player's feet with WorldEdit `//paste`).
2. **Pick materials.**
   - `python -m gtnhbuild search <text> [--mod chisel] [--solid] [--color '#rrggbb']`
   - `python -m gtnhbuild swatch <text> --out out/swatch.png`, then **read the PNG**. Chisel and other mods reuse one localized name for many variants, so choose by sight, not by name.
   - `python -m gtnhbuild gradient <low> [<mid> ...] <high> --pool-query stone [--pool spec ...] --steps 7 --style dither --out out/gradient.png` prints the strip and renders a sample wall; read it before using `b.gradient`.
   - `python -m gtnhbuild info <spec>` shows face textures, orientation metas and variants.
   - Craftability: block items join `nesql.db`, so `./gtnh recipes-for i:mod:name:meta` / `./gtnh eu-cost ...` work on the ids printed in brackets.
3. **Script it** as `builds/<name>.py`, with a module-level `build = Build("<name>")`. See `builds/example_cottage.py`.
4. **Run:** `python -m gtnhbuild run builds/<name>.py`. This runs `check()`, writes `<name>.schematic` to both Threshold client folders (Schematica's `.minecraft/schematics` and single-player WorldEdit's `config/worldedit/schematics`), copies it to the Threshold server's `config/worldedit/schematics` (scp; a failure is printed, not fatal), and writes previews to `out/<name>*`.
5. **Verify visually, every iteration.** Read `out/<name>-iso.png` (SE and NW views) and `out/<name>-slices.png` (per-layer top-down, with arrows on oriented blocks). Use `python -m gtnhbuild layers builds/<name>.py --y 3:5` for exact per-cell checks. Fix, re-run, and look again.
6. **Hand over:** the schematic path, `out/<name>.html` (3D orbit viewer with a layer slider and block hover info), and `out/<name>-bom.txt`.

## API (`from gtnhbuild import Build`)

| Call | Notes |
|---|---|
| `b.block("mod:name[:meta]" \| "Exact Localized Name")` | Validates against blocks.db and raises on unknown or ambiguous names. Every primitive also accepts a spec string. |
| `b.set(x,y,z, blk)` / `b.get` | `None` removes the block. |
| `b.fill(a, b, blk)`, `b.clear(a, b)` | Inclusive boxes. |
| `b.hollow(a, b, blk)`, `b.walls(a, b, blk)`, `b.outline(a, b, blk)` | Shell / 4 walls / 12 edges. |
| `b.line(a, b, blk)` | |
| `b.cylinder(base, r, h, blk, hollow=, axis='y')`, `b.sphere(c, r, blk, hollow=, half='top')` | |
| `b.replace(old, new, a=None, b=None)` | `old` as a registry name matches every meta. |
| `b.gradient(a, b, waypoints, pool=, steps=, axis='y', style='bands', seed=0, face='side', hollow=, only=)` | Fills a..b with blocks stepping in colour (CIELAB) through the waypoint blocks; `pool` adds in-between candidates (else the waypoints alone). `style`: `bands`, `dither` (ordered), `noise` (wobbly bands), `patches` (map-like, ignores the axis). `axis` `-y` runs top to bottom. `only(pos, block)` restricts it, e.g. recolour existing walls. Returns the strip. Deterministic per `seed`. |
| `b.gable_roof(a, b, stairs, ridge_axis='x', fill=, overhang=1, slab=)` | `a[1]` = eave y. |
| `b.stairs(spec, ascend='n', upside_down=False)` | `ascend` = the direction you walk up, where the tall half sits. |
| `b.slab(spec, top=False)`, `b.pillar(spec, 'x'\|'y'\|'z')`, `b.facing(spec, dir)` | `facing` is for furnace/chest/ladder/wall-sign/dispenser style blocks. |
| `b.ac(shape, material, front='n', up='u', secondary=, glow=)` | ArchitectureCraft shape. See below. |
| `b.cb_block(cover, slab=None)`, `b.cb_slope(cover, faces='n', kind='wedge')`, `b.cb_stairs(cover, faces='n')` | Carpenter's Blocks with a full-block cover. |
| `b.mb(kind, material, where, size)`, `b.add_micro(x,y,z, *parts)`, `b.micro(*parts)` | Forge Multipart microblocks. See below. |
| `b.paste(other, offset, rotate=k, mirror='x'\|'z')` | Rotation is clockwise seen from above. Block orientations are rewritten. |
| `b.transformed(rotate=, mirror=)`, `b.translate(dx,dy,dz)` | |
| `b.save(path=None)`, `b.preview(prefix, views=('se','nw'))`, `b.bom()`, `b.check()` | `preview` also writes `-light.txt`/`-light.png`. |
| `schematic.load(path)` | Reads any Alpha schematic: ours, WorldEdit `//schem save`, or Schematica. Blocks keep the file's WorldEdit coordinates (`WEOrigin`; world coordinates for a `//copy` save) and `anchor` is its paste anchor. Use it to modify existing builds. |

Make symmetric buildings by designing one wing or quarter and `paste`-ing it rotated or mirrored. Rotation and mirroring cover vanilla stairs, logs, quartz pillars, furnaces, chests, ladders, torches, buttons, levers, pumpkins, beds, doors, trapdoors, fence gates, vines, signs, and every modded stair/pillar/trapdoor/gate/button in `gtnhbuild/data/we-mappings/*.json`. They also cover ArchitectureCraft side/turn, Carpenter's slope/stairs/torch/ladder/slab, and microblock slots. Anything else keeps its meta, so check it in the slices.

### Building into the real terrain (`gtnhbuild.terrain`)

- `terrain.sync(a, b)` copies `level.dat` plus the region files covering box a..b from the Threshold server into `~/.cache/gtnhbuild/threshold`. `terrain.open_world().load(a, b, name)` returns a Build in **world coordinates** holding every block in the box, tile entities and EndlessIDs metas above 15 (GT ores) included. `W.get(x, y, z)` and `W.height(x, z, solid=...)` read single cells and columns.
- The schematic is the whole box. Cells the design doesn't touch carry the real terrain, so the paste restores them instead of carving air. Sync at the top of the script (so every run is fresh) and paste soon after: changes made in game inside the box since the sync are reverted.
- Such builds keep the terrain as `b.base`. `check()`, the BOM, the iso/slices/layers/HTML previews and the light check's floor list then cover only `b.design()` (placed or replaced blocks) and `b.changed()` (including carved air). For cutaways, filter `b.blocks` yourself and use `render.iso(..., frame=(lo, hi))`. They also keep the loaded box as `b.box`: the schematic is exactly that box (terrain cleared at its edge still pastes as air), and `b.set` outside it raises, since a stray block would widen the schematic and paste a slab of air over whatever is next door. Check `b.inside(p)` before touching neighbours of edge cells.
- Set `b.anchor` to a world position the player can stand in before the paste (feet block). Example: `builds/threshold_gate_atrium.py`.
- Staged projects: put shared palette and helpers in a `builds/<project>_lib.py` (see `threshold_lib.py`: `carve` lines rooms with `Space`s, plus `trench`, `doorway`, `knockout`, `clean_ores`, `pad` / `trench_run` (machine footprints and grate trenches that also fill a `reserved` set), `aisle_lights` (floor lamps on a grid, only in cells not reserved for machines, trenches or planters), and labels: `info_panel(b, a, c, mount, "TEXT", text="orange")` builds a Nuclear Control Advanced Information Panel with extenders and a Text Card; by default the low-profile transparent overlay that sits in the open cells in front of a lintel, `mount` = the wall's direction (NBT `facing` is the side it's fixed to), always on (`powerMode` 2), colours by dye name, black..orange only (Nuclear Control has 15 colours, no white; text index 15 crashes the client). `sign` places a temporary standing sign).
- Stages: `STAGES` in the lib is the one place each stage's script, box and marker live; scripts take `BOX = STAGES[name].box`. When a stage's box overlaps earlier ones, `lay_stages(b, W, BOX, [earlier names])` runs every earlier stage whose marker cell isn't in the live world yet and lays its result into the overlap (then resets `b.base`). Keep a new stage's box clear of earlier stages' info panels (pasting over a panel breaks it) and, where it can, of other new stages. Paste in order; re-pasting an earlier stage later reverts every later stage inside its box.
- One-paste install: `builds/threshold_all.py` lays every stage in `STAGES` order over the terrain of the union of their boxes (later stages win overlaps; they already carry earlier stages via `lay_stages`) and exports `threshold-all` for a single `//schem load threshold-all` + `//paste -o`. It refuses a world where a stage marker is already present; there, paste the remaining stages one by one. Re-run it right before pasting: cells outside every stage box are the terrain as synced.
- Item stacks inside tile entities (panel cards, chest contents) use numeric ids from `b.item_registry` (the server's, for terrain builds; `b.item_id(name)`); the schematic's `ItemMapping` lets WorldEdit remap them by name in any world. Blocks are better left without inventories: chests, crafting stations and machines are the player's to place.

### ArchitectureCraft (`b.ac`)

- Any block can be the material: `BaseName` is the registry name and `BaseData` is the meta. Shapes are listed in `gtnhbuild/modblocks.py` `SHAPES` and can be named by title ("Roof Tile", "Roof Outer Corner", "Hip Roof Ridge", "Round Pillar", "Window Frame", ...) or by id.
- `front` is the shape's local north:
  - Roof Tile: the side the slope faces (its low edge).
  - Outer Corner (`front='n'`): slopes north and east, with the peak in the south-west.
  - Inner Corner: low corner toward front and front+90°.
  - Modelled shapes have their back (the wall side) opposite `front`: a balustrade's rail, a cornice's wall face, an architrave's back. To put a rail on the edge of a drop, point `front` away from the drop.
- `up='d'` mounts the shape upside down. Windows take `secondary="minecraft:glass_pane"`. `glow=True` gives the `shapeSE` variant, which renders full-bright and emits light 15.
- BOM converts shapes to Sawbench input (`materialUsed` per `itemsProduced`).

### Carpenter's Blocks

- `cb_slope(cover, faces, kind)`, where `faces` lists the horizontal direction(s) the sloped surface faces:
  - `wedge` 'n': a ramp rising toward the south. This is the same shape a player facing south places.
  - `wedge_ext` / `wedge_int` / `oblique_ext` / `oblique_int` 'ne': corners.
  - `wedge_side` 'ne': a vertical diagonal.
  - `prism_wedge`.
  - `upside_down=True` gives the ceiling variant.
- `cb_stairs(cover, 'n')`: low step to the north, tall half to the south.
- `cb_block(cover, slab='down'|'up'|'north'|...)`.
- Covers are written by registry name (`cbUniqueId`), so they survive worlds with different numeric ids.

### Forge Multipart microblocks (`b.mb` / `b.add_micro`)

- One cell (`ForgeMultipart:block`, TE `savedMultipart`) holds any number of parts. `add_micro` merges parts into the cell at a position and raises if two parts would take the same slot.
- `b.mb(kind, material, where, size)`, with `size` in eighths of a block:
  - `face`: cover 1, panel 2, slab 4. `where` = the side it lies against (`'down'`, `'n'`, ...).
  - `hollow`: hollow cover/panel/slab with a ½-block hole. `where` as for `face`.
  - `corner`: nook 1, corner 2, notch 4. `where` = three sides, e.g. `'dnw'`.
  - `edge`: strip 1, post 2, pillar 4. `where` = the two sides it runs between; `'dn'` is the bottom-north edge, running east-west.
  - `post`: centred post, size 2/4/6. `where` = axis `x`/`y`/`z`.
- Sizes 1–7 are all valid parts, but only 1/2/4 come out of a saw directly.
- Valid materials: FMP defaults, `config/microblocks.cfg`, every chisel block, Extra Utilities decorative/colour blocks and Lapis Caelestis, and ProjectRed inverted lamps (`...lamp:16`–`31`). These registrations were found by scanning the mod jars. `check()` warns on anything else; some other mods also register a few blocks, so confirm those in game.
- The BOM lists each part. Raw materials follow the saw and glue recipes: face = size/8 of a block, edge = half that, corner = a quarter.

### Lighting

- `python -m gtnhbuild search --light [text]` lists light emitters with their level (`L15`).
- A microblock cell emits the light of its brightest part's material, whatever the part's size. Covers, strips, nooks and posts therefore make the same light as a full block:
  - glowstone and Extra Utilities coloured glowstone (`ExtraUtilities:color_lightgem`): 15
  - ProjectRed inverted-lamp microblocks: 15
  - Lapis Caelestis (`ExtraUtilities:greenscreen`): its colour's brightness. White 15, light grey 12, pink 11, magenta/yellow/cyan 10, purple 9, orange/grey 7, light blue 6, green/blue/red 5, brown/dark green 3, black 0. The value is computed per position, so `blocks.db` shows 0; the toolkit uses the mod's colour table.
  - ArchitectureCraft Glow shapes: 15.
- Chisel Anti Blocks render full-bright but emit **no** light. Mobs can't spawn on them.
- `python -m gtnhbuild light <build> [--out x.png]`, also run by `run`/`preview`, models block light at night:
  - -1 per step; opaque cubes, slabs and stairs stop it.
  - It marks every walkable cell on the build's own floors where hostiles could spawn (light ≤ 7).
  - Aim for `0 can spawn hostiles`, and read `-light.png` to judge evenness.
  - Approximations: microblock, Carpenter's and ArchitectureCraft cells pass light, and floors outside the build aren't checked.

## Preview limits

- Geometry is exact for cubes, slabs, stairs, logs, fences, walls, panes, plants, roof tiles/corners/ridges, Carpenter's wedges and corners, and every microblock part. ArchitectureCraft model shapes (pillars, capitals, cornices, arches, balustrades, spheres, overhangs...) are drawn from the mod's own `.objson` models in the instance's ArchitectureCraft jar (`GTNH_AC_JAR` overrides; without the jar they fall back to collision boxes). Full-bright materials (Lapis Caelestis in its flat colour, Anti Blocks, glow shapes, inverted lamps) are drawn unshaded.
- ArchitectureCraft windows and roof profiles are approximated; Carpenter's prisms and TESR blocks (chests, GT machines, info panels) render as their collision boxes.
- Textures come from the Modernity pack. Biome tint uses plains colours.
- The HTML viewer loads three.js from unpkg, so it needs internet access.

## Loading in game

- **Schematica** (survival projection): load it from the Schematica menu (`.minecraft/schematics`), then use the printer or build along the projection.
- **WorldEdit** runs on the Threshold server, so `//schem load <name>` reads the **server's** `config/worldedit/schematics` (`run` copies files there); single-player worlds read the client folder. Then:
  - `//paste -o` places the clipboard at its saved coordinates. For world-coordinate builds that is exactly where it was designed, wherever you stand.
  - `//paste` places the build's anchor at your feet block (`b.anchor`, default build (0,0,0)). Stand in it exactly: F3 "Block:" must match, or `/tp @p <x+.5> <y> <z+.5>`.
  - `-a` skips air, `-s` selects the pasted region, `//undo` reverts. `//rotate` and `//flip` also handle ArchitectureCraft tile entities.
  - Blocks that sync their look through IC2's field network (Nuclear Control info panels: facing, screen, power mode, transparency, thickness, colours) read the pasted NBT on the server, but the client only gets those fields when it starts watching the chunk, so right after a paste they show defaults. Relog (single player: Save and Quit, reopen) or move out of view range and back (confirmed in game).
  - Pasting over panels that are already there breaks them: each replaced extender makes Nuclear Control rebuild the old screen from whatever neighbours exist at that instant, and the core saves those partial bounds, so text sits off-centre over a shorter screen. Clear them first: select the stage box (`//pos1`, `//pos2` at its corners), `//replace IC2NuclearControl:blockNuclearControlMain 0`, then `//paste -o` and relog.
- Files carry `BlockMapping` and `SchematicaMapping` name tables, so numeric block ids never matter. They have no `AddBlocks` and hold at most 255 distinct block names per file; split larger palettes. Metas above 255 go in WorldEdit's `AddData`; Schematica reads only the low byte.

## References

- `references/architecturecraft.md`: TileShape NBT, the shape table, side/turn matrices and placement rules.
- `references/carpenters-blocks.md`: TEBase NBT, cover attributes, and the slope/stairs/collapsible/door/torch `cbMetadata` tables.
- Overrides: `gtnhbuild/palette.py` env vars `GTNH_BLOCKS_DB`, `GTNH_TEXTURES_ZIP`, `GTNH_LEVEL_DAT`; `gtnhbuild/schematic.py` `GTNH_SCHEMATICS_DIRS` (`os.pathsep`-separated) and `GTNH_SERVER_SCHEMATICS` (`host:dir`, empty to skip); `gtnhbuild/terrain.py` `GTNH_WORLD` (local copy) and `GTNH_SERVER_WORLD` (`host:dir` of the server world).
