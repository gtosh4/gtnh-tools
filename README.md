# gtnh-tools

Tools for [GT New Horizons](https://www.gtnewhorizons.com/) 2.9, built on a full
[NESQL](https://github.com/ShadowTheAge/nesql-exporter) export of the modpack:

- **`gtnh`** (Rust): query items, fluids and recipes, and trace the minimum EU / UU-Matter cost or
  the lowest voltage tier at which anything can be made, through the whole recipe graph.
- **`gtnhbuild`** (Python): design buildings block by block in Python and export WorldEdit /
  Schematica `.schematic` files, with previews, a palette browser and lighting checks.

The data files are too large for git; they are attached to a
[release](https://github.com/gtosh4/gtnh-tools/releases/tag/data-gtnh-2.9.0).

## Data files

| File | Size | Used by | Contents |
|---|---|---|---|
| `nesql.db.zst` | 114 MB (620 MB unpacked) | `gtnh` | GTNH 2.9.0 NESQL export (SQLite, with lookup indexes): items, fluids, ore dicts, all recipe maps, GT recipe metadata, quests, bees, mobs, worldgen (ore veins, small ores, underground fluids), CropsNH crops, GT multiblock structures and the controllers' Shift tooltips |
| `blocks.db` | 14 MB | `gtnhbuild` | Block palette: every placeable block + meta, its per-face textures and average colours, light, bounds |
| `block-textures.zip` | 7 MB | `gtnhbuild` | Block texture PNGs referenced by `blocks.db` (Modernity resource pack) |
| `item-icons.zip` | 148 MB | optional | 64×64 item icons, under `item.image_file_path` from `nesql.db` |
| `SHA256SUMS` | | | Checksums of the files above |

Download into the repo root and unpack the database:

```bash
git clone https://github.com/gtosh4/gtnh-tools && cd gtnh-tools

# with the GitHub CLI
gh release download data-gtnh-2.9.0 -R gtosh4/gtnh-tools

# or with curl
base=https://github.com/gtosh4/gtnh-tools/releases/download/data-gtnh-2.9.0
for f in nesql.db.zst blocks.db block-textures.zip item-icons.zip SHA256SUMS; do
  curl -LO "$base/$f"
done

sha256sum -c SHA256SUMS
zstd -d nesql.db.zst          # -> nesql.db
```

`item-icons.zip` is only needed if you want item pictures; skip it otherwise.

## `gtnh` — recipe and cost CLI

Build (Rust 1.85+, SQLite is bundled):

```bash
cargo build --release && cp target/release/gtnh .
```

Run from the directory holding `nesql.db` (or pass `--data path/to/nesql.db`):

```bash
./gtnh search "naquadah"                       # items + fluids by name
./gtnh recipes-for i:gregtech:gt.metaitem.01:2324 --limit 5
./gtnh recipes-using o:ingotNaquadah --limit 5
./gtnh recipe 'r~thLHqSL-PayH7mBL1s4WeA=='
./gtnh recipes-of-type "Blast Furnace" --limit 10
./gtnh eu-cost i:gregtech:gt.blockcasings5:4   # min EU to make 1, full chain
./gtnh eu-cost i:gregtech:gt.blockcasings5:4 --min-tier   # lowest peak voltage tier
./gtnh uu-cost i:minecraft:diamond:0           # min UU-Matter to make 1
./gtnh structure i:gregtech:gt.blockmachines:1000 --tier 3 --layers   # EBF as NEI's structure tab builds it
./gtnh structure i:gregtech:gt.blockcasings:11 # which multiblocks use a block
./gtnh --json recipes-for f:gregtech:hydrogen | jq '.[0]'
```

Ids: `i:mod:name:meta` items, `f:name` fluids, `o:oreDictName` ore dicts, `r~…` recipes.

`eu-cost` traces every recipe back to free or seeded sources (water and air hatches, ore veins with
their rocket tiers, bees, CropsNH crops, Extreme Entity Crusher drops, …) and applies tier gates
the voltage tag alone misses (fusion EU thresholds, special compressors, Algae Pond casings, a
crop's sub-soil block). `uu-cost` uses the same graph with UU-Matter as the only source. The first
run builds a cache (`nesql.db.eucache`, ~10 s) and, once, adds lookup indexes to `nesql.db`; the
cache is rebuilt whenever the database or the binary changes.

[`CLAUDE.md`](CLAUDE.md) documents every subcommand, the output format, metadata keys, voltage
tiers, coil requirements and the graph rules in detail.

### Merging another export

`gtnh merge-db <src.db>` folds another NESQL export of the same game into `nesql.db`, adding only
the rows it lacks (NESQL keys rows by content hash; a list such as an item's tooltip lines is taken
whole, only for entities the database has none for). The CropsNH crops and the multiblock
structures in the release database came in this way, from `/nesqlcrops` and `/nesqlmultiblocks`
exports.

## `gtnhbuild` — building toolkit

Python 3.10+ with Pillow; needs `blocks.db` and `block-textures.zip` in the repo root (or
`GTNH_BLOCKS_DB` / `GTNH_TEXTURES_ZIP`).

```python
# builds/hut.py
from gtnhbuild import Build

build = b = Build("hut")
b.fill((0, 0, 0), (6, 0, 6), "minecraft:stonebrick")
b.walls((0, 1, 0), (6, 3, 6), "minecraft:planks:1")
b.gable_roof((0, 4, 0), (6, 4, 6), "minecraft:spruce_stairs", fill="minecraft:planks:1")
```

```bash
python -m gtnhbuild run builds/hut.py --schematic hut.schematic   # schematic + previews in out/
python -m gtnhbuild search marble --solid                          # find blocks
python -m gtnhbuild swatch --color '#8a6b4a' --out swatch.png      # pick by colour
python -m gtnhbuild gradient minecraft:stone chisel:marble:0       # colour runs between blocks
python -m gtnhbuild light hut.schematic                            # hostile-spawn spots
```

It handles orientation of stairs, logs, slabs and mod blocks, ArchitectureCraft shapes, Carpenter's
Blocks, Forge Multipart microblocks and tile-entity data (signs, Nuclear Control panels). Previews:
isometric PNGs, layer slices, ASCII layers, a bill of materials, a light/spawn report and a
three.js viewer. `gtnhbuild.terrain` reads a world's region files so builds can be carved into
real terrain in world coordinates (`//paste -o`).

`builds/` holds a worked example (`example_cottage.py`); other scripts you put there stay out of
git (`.gitignore`). [`.claude/skills/gtnh-build/SKILL.md`](.claude/skills/gtnh-build/SKILL.md) is
the complete guide.

Some defaults point at the author's setup (the client instance's schematics folder, a server
reached over `scp`); override them with `--schematic` and the `GTNH_SCHEMATICS_DIRS`,
`GTNH_SERVER_SCHEMATICS`, `GTNH_WORLD`, `GTNH_SERVER_WORLD` and `GTNH_LEVEL_DAT` environment
variables, or set `GTNH_SERVER_SCHEMATICS=""` to skip the server copy.

## Regenerating the data

- `nesql.db`: run `/nesql` (full export, ~1 hour) in a creative single-player world with
  NESQL-Exporter installed, then copy `.minecraft/nesql/<repository>/nesql.db` here. CropsNH crops
  come from the exporter's `cropsnh` plugin (`/nesqlcrops`, then `gtnh merge-db`), multiblock
  structures and Shift tooltips from its `multiblock` plugin (`/nesqlmultiblocks`, then
  `gtnh merge-db`).
- `blocks.db`, `block-textures.zip`: `/nesqlblocks` from the same exporter.

The CropsNH and multiblock plugins, `/nesqlcrops`, `/nesqlmultiblocks`, `/nesqlblocks` and the
Shift tooltips are additions in a local fork of NESQL-Exporter that is not published yet.
