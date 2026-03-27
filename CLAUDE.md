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
| `search <query>` | Substring search items+fluids by name/id. Flags: `--tooltip`/`-t`, `--regex`/`-r`, `--limit N` |
| `item <id>` / `fluid <id>` | Details for one item or fluid |
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

**`uu-cost` flags**: `--depth N` (default 3)

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
| Electrum Flux | 9,901 | UV (recipe tier; full chain likely higher) |
| Awakened Draconium | 10,801 | UHV (recipe tier) |
| Infinity | 11,701 | UEV (Assemblyline) |
| Hypogen | 12,601 | UIV (Assemblyline) |
| Eternal | 13,501 | UMV (Assemblyline) |

"Craft tier" = peak tier shown in `eu-cost` header when unblocked; `eu-cost --min-tier` gives the lowest-tier reachable path. For Trinium and Electrum Flux the full ingredient chains are partially blocked; treat ZPM/UV as a floor.

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

115,873 items · 1,542 fluids · 121,352 ore dicts · 2,206 recipe types · 226,374 recipes · 79 ore veins · 538 bee mutations · 424 mob entries · 3,739 quests.

Gaps: IC2 Nuclear Fission EU/t not stored. Planetary Gas Siphon and Bee Products are included.

Files: `src/lib.rs` (structs, queries), `src/main.rs` (CLI, formatting), `nesql.db` (SQLite).

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
- Extreme Industrial Greenhouse — IC2 crops ([crop list](https://wiki.gtnewhorizons.com/wiki/IC2_Crops_List))

When answering "best way to source X": enumerate what **each** source produces first, then trace forward to X. Do not stop at obvious inputs (water, air) — EIG crops and EEC mob drops may yield better routes.
