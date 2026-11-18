# GTNH Repository — Agent Guide

## CLI Usage

```bash
./gtnh <subcommand> [args]           # queries nesql.db
./gtnh --data /path/to/nesql.db ...  # alternate db
./gtnh --json <subcommand> ...       # JSON output (pipe to jq)
./gtnh --dot <subcommand> ...        # Graphviz DOT (eu-cost, uu-cost)
./gtnh --all-recipes <subcommand>    # include Recycler + recycle=1 recipes
```

Rebuild after editing source: `cargo build --release && \cp -u target/release/gtnh .`

---

## Subcommands

| Command | Description |
|---------|-------------|
| `build-db [script] [-o path]` | *(Legacy)* Convert `nesql-db.script` → `nesql.db` |
| `merge-db <src>` | Merge another NESQL export into `--data` (e.g. a `/nesqlcrops` or `/nesqlmultiblocks` repository); only rows the DB lacks are added, and collection rows (tooltip lines, structure blocks) only for entities the DB has none for |
| `search <query>` | Substring search items+fluids by name/id. Flags: `--tooltip`/`-t`, `--regex`/`-r`, `--limit N` |
| `item <id>` / `fluid <id>` | Details for one item or fluid; items show their Shift tooltip too when it differs (GT multiblock structure text) |
| `structure <id> [--tier N] [--layers]` | A multiblock's structure as NEI's "Multiblock Structure" tab builds it (block counts, hatch dots, `--layers` y-slices); for a non-controller id, the multiblocks that use that block |
| `recipe-types [--filter <str>]` | List recipe type names with counts |
| `recipes-for <id>` | Recipes that produce the item/fluid |
| `recipes-using <id>` | Recipes that consume the item/fluid/ore-dict |
| `recipe <id>` | Full detail for one recipe by `r~` hash |
| `recipes-of-type <name>` | All recipes of a type. Name can be prefix (matches all tiers). Default limit 20 |
| `eu-cost <id>` | Min EU cost to produce 1 unit, tracing full chain to free inputs |
| `uu-cost <id>` | Min UU-Matter cost to produce 1 unit |

**`--sort`** (on `recipes-for`, `recipes-using`, `recipes-of-type`): `eu` (default), `time`, `inputs`, `fuel`

**`search --regex`/`-r`**: case-insensitive regex — supports `|` for OR, `.*` for wildcards.

**`eu-cost` flags**: `--depth N` (default 3), `--why` (diagnose blocked paths), `--min-tier` (find lowest peak-tier path; break ties with lowest EU cost)

**`eu-cost` graph rules**: Thaumcraft aspects (`thaumcraftneiplugin~Aspect` in 2.8, `i~aspectrecipeindex~aspect~…` in 2.9) are free inputs. NEI display pages that show a whole chain or a structure as one 1-EU recipe are excluded (`DISPLAY_ONLY_TYPES` in `src/lib.rs`: High Temperature Gas Reactor, Foundry Module Components, Godforge Upgrades). Metadata tier gates (`metadata_tier_min`): `fusion_threshold`, `compression_tier`, `algae_pond_tier` (Algae Pond casing tier = voltage tier). The `.eucache` is rebuilt when the DB or the `gtnh` binary changes.

**`uu-cost` flags**: `--depth N` (default 3). It runs on the same graph as `eu-cost` (shares `.eucache`), seeded only with UU-Matter at 1 UU/mB: recipe EU is ignored, and recipes that consume nothing (bees, crops, siphons, ore veins, water/air) don't count, so every good is traced back to UU-Matter.

**Indexes**: `Repository::open` adds missing lookup indexes to the DB once (`LOOKUP_INDEXES` in `src/lib.rs`). NESQL-Exporter's SQLite output only has Hibernate's FK indexes; without them per-item lookups scan whole tables (minutes instead of seconds). The DB must be writable the first time.

---

## ID Format

| Prefix | Example | Meaning |
|--------|---------|---------|
| `i:` | `i:gregtech:gt.blockmachines:1189` | Item (`mod:internalName:damage`) |
| `f:` | `f:bartworks:naquadah based liquid fuel mki` | Fluid (registry name, lowercase) |
| `o:` | `o:ingotNaquadah` | Ore dict entry |
| `r~` | `r~thLHqSL-PayH7mBL1s4WeA==` | Recipe (base64 hash) |

---

## Recipe Output Format

```
#1   [r~<id>]  <RecipeTypeName>  →  <total EU>  (<EU/output>)
  GT:    <voltage> EU/t × <amps>A × <ticks>t = <total> (<duration>)  [<TIER>]
  Meta:  key=value ...
  Inputs:  N× Item Name
  Outputs: N× Item Name  (probability%)
```

Fuel recipes (`voltage=0`) omit GT line; show `fuel_value=N` in Meta. Sort with `--sort fuel`.

**Metadata keys:** `fuel_value`, `fuel_type` (0=diesel, 1=gas turbine, 5=magic), `lftr_output_power`, `lng_basic_output`, `sparge_max_byproduct`, `nke_range`, `precise_assembler_casing_tier`, `mass`, `coil_heat` (minimum Kelvin required — EBF and Alloy Blast Smelter)

**CropsNH crops** (recipe type `Crops`, NEI's "Crops" page): inputs are the seed, then the soils and sub-soils (multi-item groups, shown as `one of N: …`); outputs are the harvest drops with their chances. Extra lines: `Crop:` (name, crop id, tier, growth points, drop multiplier), `Likes:` (biome tags), `Needs:` (growth requirements such as light). JSON adds a `crop` object. In `eu-cost` the seed and soil are free, but a required sub-soil (input slot 2) is a real input with amount 0 (shown `0× … [placed, not consumed]`): the crop is reachable only if some sub-soil block is, and that block's tier counts for `--min-tier`, `--max-tier` and the peak tier, with no EU added. They come from the NESQL-Exporter `cropsnh` plugin: run `/nesqlcrops` in a single-player world (exports only base + cropsnh to `.minecraft/nesql/crops/`), then `./gtnh merge-db <instance>/.minecraft/nesql/crops/nesql.db`. A full `/nesql` export includes them when `cropsnh` is in the exporter's `enabled_plugins`.

---

## Voltage Tiers

`0=ULV 1=LV 2=MV 3=HV 4=EV 5=IV 6=LuV 7=ZPM 8=UV 9=UHV 10=UEV 11=UIV 12=UMV 13=UXV`

EU/t per amp: ULV=8, LV=32, MV=128, HV=512, EV=2048, IV=8192, LuV=32768, ZPM=131072, UV=524288, UHV=2097152.

`voltage_tier` on `GtRecipe` is the index above; `voltage` is raw EU/t.

---

## Recipe Tiers and Overclock

Use the recipe's `[TIER]` to determine required machine tier — not component names.

- Most multiblocks can overclock: run recipes **one tier above** their energy hatch (IV hatch → runs LuV recipes).
- **Exception**: some multiblocks forbid overclock-up (check tooltip). Precise Assembler enforces `precise_assembler_casing_tier` metadata exactly.

**"What tier can I first craft X":**
1. `recipes-for <id>` → note `[TIER]` and machine type.
2. Subtract one tier if the machine is an overclockable multiblock.
3. If the recipe has `coil_heat` metadata, find the minimum coil meeting that heat and take the max of the recipe tier and that coil's craft tier (see table below).
4. Recurse on inputs.

**EBF / Alloy Blast Smelter coil requirements** (`coil_heat` metadata key):

| Coil | Heat (K) | Craft tier (full chain) |
|------|----------|------------------------|
| Cupronickel | 1,801 | EV |
| Kanthal | 2,701 | EV |
| Nichrome | 3,601 | EV |
| TPV-Alloy | 4,501 | IV |
| HSS-G | 5,401 | IV |
| HSS-S | 6,301 | UV |
| Naquadah | 7,201 | UV |
| Naquadah Alloy | 8,101 | UEV |
| Trinium | 9,001 | ZPM (recipe tier; full chain likely higher) |
| Fluxed Electrum (2.8: Electrum Flux) | 9,901 | UV (recipe tier; full chain likely higher) |
| Awakened Draconium | 10,801 | UHV (recipe tier) |
| Infinity | 11,701 | UEV (Assemblyline) |
| Hypogen | 12,601 | UIV (Assemblyline) |
| Eternal | 13,501 | UMV (Assemblyline) |

"Craft tier" = peak tier shown in `eu-cost` header when unblocked; `eu-cost --min-tier` gives the lowest-tier reachable path. For Trinium and Fluxed Electrum the full ingredient chains are partially blocked; treat ZPM/UV as a floor.

For recipes with `coil_heat ≤ 3601` the coil is never the bottleneck (Nichrome is EV, same as most early EBF recipes). For `coil_heat > 3601`, check whether the coil's craft tier exceeds the recipe's voltage tier.

---

## Minimizing Token Usage

- **`--limit N`**: always cap recipe lists; default is 20 but use smaller when possible.
- **`--peak-tier`**: single line instead of full `eu-cost` tree when you only need the tier.
- **`recipe r~<hash>`**: fetch one recipe by id rather than re-running `recipes-for`.
- **`--json | jq`**: extract only needed fields — avoid ingesting full output.
- **Avoid `--limit 0`** on broad types (Assembler, Chemical Reactor = thousands of rows).
- **`recipe-types --filter`**: confirm name and count before a bulk fetch.
- **Skip `search`** when you already have the id.

---

## Data Scale

GTNH 2.9.0: 122,285 items · 1,475 fluids · 142,291 ore dicts · 2,587 recipe types · 252,490 recipes · 122 ore veins · 54 small ores · 48 underground fluid entries · 543 bee mutations · 402 mob entries · 3,814 quests. (The 2.8 export is kept as `nesql-2.8.db`; use `--data nesql-2.8.db`.)

Gaps: IC2 Nuclear Fission EU/t not stored. Planetary Gas Siphon and Bee Products are included. CropsNH crop drops are not in the 2.9.0 export until a `/nesqlcrops` export is merged in (see Recipe Output Format); then `crop` (one row per crop, `recipe_id` joins its `Crops` recipe: `crop_id`, `localized_name`, `tier`, `growth_duration`, `drop_chance`) with `crop_liked_biome_tags` and `crop_requirements` (ordered text rows keyed by `crop.id`).

Multiblock structures (`/nesqlmultiblocks`, merged in; 334 GT multiblocks, 1,643 tier rows): `multiblock_structure` (one row per controller × tier slider value: `controller_id`, `tier`, `max_tier`, `sizex/y/z`, `controllerx/y/z`; controller faces south, +z) with `multiblock_structure_blocks` (`blocks_x/y/z` from the lowest corner, `blocks_item_id` = the block's item, `blocks_block` + `blocks_block_meta` = registry name and meta, `blocks_dot` = hatch hint dot, 0 for none), `multiblock_structure_hints` (`hints_key` dot → accepted hatches) and `multiblock_structure_description` (structure tooltip lines). Built with every channel slider unset and one of each required hatch placed on a dot position; the rest of the dot positions hold the casing. Shift tooltips: `item_shift_tooltip` (ordered rows, only where they differ from `item_tooltip`).

Files: `src/lib.rs` (structs, queries), `src/main.rs` (CLI, formatting), `nesql.db` (SQLite). Item tooltips are read from `item.tooltip` (exports before NESQL-Exporter 0.5.7) or joined from `item_tooltip` rows (0.5.7+); `Repository::open` picks whichever the DB has.

Worldgen (NESQL-Exporter 0.5.7+, same data as the GT NEI ore plugin pages): `ore_vein` / `small_ore_deposit` with one `*_dimensions` row per dimension (`dimensions_name`, `dimensions_abbreviation`, `dimensions_rocket_tier`, `dimensions_miny`/`maxy`, `dimensions_chance`), and `underground_fluid` (per fluid × dimension: `rocket_tier`, `chance`, `min_amount`, `max_amount`). Ore mining tiers for `eu-cost` come from the lowest rocket tier per ore (T1=EV … T8+=UIV); older exports lack these columns and load without mining tiers.

Block palette (`/nesqlblocks`, separate from `nesql.db`): `blocks.db` with `block` (one row per placeable block + meta: `registry_name` as WorldEdit uses it, `item_id` joining `nesql.db` items, `opaque_cube`, `normal_block`, `render_type`, `render_pass`, `light_value`, bounds), `block_face` (texture per side: down/up/north/south/west/east), and `texture` (`file`, size, `average_color`, `opacity`). Texture PNGs are in `block-textures.zip` under the `texture.file` paths; textures come from the active resource packs (Modernity). Item icons (64×64, inventory view) are in `item-icons.zip` under `item.image_file_path`.

Building toolkit (`gtnhbuild/`, Python, needs Pillow): scripts in `builds/*.py` define `build = Build(...)`; `python -m gtnhbuild run builds/x.py` writes `x.schematic` (name-mapped, loads in WorldEdit and Schematica) to the Threshold instance and the Threshold server's WorldEdit folder, plus previews in `out/` (iso PNG, layer slices, ASCII layers, BOM, light/spawn check, three.js HTML). `gtnhbuild.terrain` syncs and reads the live server world so builds can be carved into real terrain (world coordinates, `//paste -o`). Palette lookups: `python -m gtnhbuild search|swatch|info|gradient` (`search --light` for emitters, `gradient` for colour runs between blocks). Handles ArchitectureCraft shapes (previews drawn from the mod's models), Carpenter's Blocks and Forge Multipart microblocks. Workflow and API: `.claude/skills/gtnh-build/SKILL.md`.

---

## Infinite Resource Sources
*(ZPM-era, best→worst)*

- Reservoir Hatch (water)
- Extreme Entity Crusher (mob drops)
- Ender Tree (endstone, obsidian)
- Nether Tree (netherrack, nether quartz, soulsand)
- Air intake hatch (air, nether air)
- Extreme Industrial Greenhouse — non-IC2 crops ([wiki](https://wiki.gtnewhorizons.com/wiki/Extreme_Industrial_Greenhouse))
- Planetary Gas Siphon
- Bees
- CropsNH crops (replaced the IC2 crop mods in 2.9; `Crops` recipes, see Recipe Output Format)

When answering "best way to source X": enumerate what **each** source produces first, then trace forward to X. Do not stop at obvious inputs (water, air) — EIG crops and EEC mob drops may yield better routes.
