# GTNH Repository — Agent Guide

## Running the CLI

```bash
./gtnh <subcommand> [args]          # query gtnh.db in the current directory
./gtnh --data /path/to/gtnh.db ...  # use a different database file
./gtnh --json <subcommand> ...      # emit JSON instead of human-readable text
```

After editing `src/main.rs` or `src/lib.rs`, rebuild:
```bash
cargo build --release && \cp -u target/release/gtnh .
```

---

## Subcommands

### `build-db [script] [--output <path>]`
Convert `nesql-db.script` (HSQLDB dump) into `gtnh.db`. Only needed once (or after the
script is updated). Defaults: script=`nesql-db.script`, output=`gtnh.db`.

```bash
./gtnh build-db
./gtnh build-db /path/to/nesql-db.script --output /path/to/gtnh.db
```

### `search <query>`
Case-insensitive substring search across item name, id, and internal name — and the same
for fluids. Returns both item and fluid matches. Search runs in parallel.

```bash
./gtnh search "naquadah"
./gtnh search "naquadah" --limit 5
./gtnh search "produces oxygen" --tooltip      # also searches tooltip text
./gtnh search "produces oxygen" -t             # short form
```

Use `search` first to discover the exact id of an item or fluid before using other commands.

### `item <id>` / `fluid <id>`
Show details (name, mod, stack size, recipe counts) for a single item or fluid by id.

```bash
./gtnh item "i:gregtech:gt.blockmachines:1189"
./gtnh fluid "f:bartworks:naquadah based liquid fuel mki"
```

### `recipe-types [--filter <substring>]`
List all recipe type names with recipe counts and mod category. Useful for discovering
what machine types exist before querying them.

```bash
./gtnh recipe-types
./gtnh recipe-types --filter nuclear
```

### `recipes-for <id>`
All recipes that **produce** the given item or fluid.
Canner, Recycler, and `recycle=1` metadata recipes are hidden by default; pass `--all-recipes` to include them.

```bash
./gtnh recipes-for "i:gregtech:gt.rodNaquadah32:0"
./gtnh recipes-for "f:bartworks:naquadah based liquid fuel mki"
./gtnh --all-recipes recipes-for "f:bartworks:naquadah based liquid fuel mki"
```

### `recipes-using <id>`
All recipes that **consume** the given item, fluid, or ore dict as an input.
Canner, Recycler, and `recycle=1` metadata recipes are hidden by default; pass `--all-recipes` to include them.

```bash
./gtnh recipes-using "i:GoodGenerator:highDensityPlutonium:0"
./gtnh recipes-using "o:ingotNaquadah"          # ore dict prefix: o:
./gtnh --all-recipes recipes-using "o:ingotNaquadah"
```

### `recipe <id>`
Full detail for a single recipe by its recipe id (the `r~...` hash shown in other outputs).

```bash
./gtnh recipe "r~thLHqSL-PayH7mBL1s4WeA=="
```

### `recipes-of-type <type-name>`
All recipes of a given recipe type. Default limit 20; use `--limit 0` for all.

The name can be an exact match **or** a prefix that omits the tier suffix — e.g. `"Scanner"`
matches `"Scanner (LV)"`, `"Scanner (MV)"`, etc. Copy exact names from `recipe-types` output
when you need a specific tier only.

```bash
./gtnh recipes-of-type "Large Naquadah Reactor" --limit 0
./gtnh recipes-of-type "Gas Turbine Fuel" --sort fuel
./gtnh recipes-of-type "Scanner" --limit 0      # all tiers
```

### Sort options (`--sort`)
Available on `recipes-for`, `recipes-using`, and `recipes-of-type`:
- `eu` (default) — EU per output unit, ascending (best efficiency first)
- `time` — duration in ticks, ascending (fastest first)
- `inputs` — number of distinct inputs, ascending (simplest first)
- `fuel` — `fuel_value` metadata, descending (highest energy density first)

---

## ID Format

| Prefix | Example | Meaning |
|--------|---------|---------|
| `i:` | `i:gregtech:gt.blockmachines:1189` | Item (`mod:internalName:damage`) |
| `f:` | `f:bartworks:naquadah based liquid fuel mki` | Fluid (usually lowercase) |
| `o:` | `o:ingotNaquadah` | Ore dict entry |
| `r~` | `r~thLHqSL-PayH7mBL1s4WeA==` | Recipe (base64 hash) |

Fluid ids are typically the fluid's registry name in lowercase. Item damage values
distinguish variants (e.g. `gt.blockmachines:1189` vs `:1190`).

---

## Recipe Output Format

```
#1   [r~<id>]  <RecipeTypeName>  →  <total EU>  (<EU/output>)
  GT:    <voltage> EU/t × <amps>A × <ticks>t = <total> (<duration>)  [<TIER>]
  Meta:  key=value  key2=value2
  Inputs:
       N×  Item Name
  Outputs:
       N×  Item Name  (probability%)
```

**Fuel recipes** (`voltage=0, duration=0`) skip the GT line and show only `fuel_value=N`
in Meta. Sort with `--sort fuel` to rank by energy density.

**Metadata keys encountered in the data:**

| Key | Meaning |
|-----|---------|
| `fuel_value` | Energy per item for generator fuels (not in EU directly — conversion depends on the generator) |
| `fuel_type` | Generator family (0 = diesel/combustion, 1 = gas turbine, 5 = magic absorber, …) |
| `lftr_output_power` | EU/t output of the LFTR while this fuel is loaded |
| `lng_basic_output` | Base EU/t output of the Large Naquadah Reactor while this fuel is loaded |
| `sparge_max_byproduct` | LFTR Gas Sparging — max byproduct items per operation |
| `nke_range` | Neutron Activator — required neutron flux range |
| `precise_assembler_casing_tier` | Precise Assembler — required casing tier |
| `mass` | Radio Hatch — mass value of the material |

---

## Voltage Tiers

```
0=ULV   1=LV    2=MV    3=HV    4=EV    5=IV
6=LuV   7=ZPM   8=UV    9=UHV  10=UEV  11=UIV  12=UMV  13=UXV
```

EU/t per amp: ULV=8, LV=32, MV=128, HV=512, EV=2048, IV=8192, LuV=32768, ZPM=131072,
UV=524288, UHV=2097152.

The `voltage_tier` field on `GtRecipe` is this index. `voltage` is the raw EU/t value.

---

## Recipe Tiers and Overclock

When determining what tier a machine can first be crafted, **look at the recipe's voltage
tier**, not just the component names.

- The recipe tier tells you what machine is actually required to run it.
- Multiblock machines (EBF, Assembler, Precise Assembler, etc.) can overclock: they can
  run recipes **one tier higher** than their energy hatch. This means a machine with an
  IV-tier energy hatch can run LuV recipes, an LuV hatch can run ZPM recipes, etc.
- **Exception**: some multiblocks explicitly forbid overclocking up. Check the controller
  block's tooltip for wording like *"can only run recipes matching [X] energy hatch tier"*.
  The Precise Assembler is a known example — `precise_assembler_casing_tier` metadata on
  its recipes enforces a hard tier match.

**Practical example:**
- UV Machine Hull has a recipe at UV tier in the Assembler.
- An EBF running with an IV energy hatch can overclock to LuV recipes — but the Assembler
  is not the EBF. Check each multiblock individually.
- Naquadah Alloy (needed for UV hull) is an EBF recipe at LuV tier. An EBF with an IV
  energy hatch can overclock to run LuV recipes, so UV hull is reachable at IV tier.

**Workflow for "what tier can I first craft X":**
1. `recipes-for <id>` — find all production recipes and note their `[TIER]`.
2. For each recipe, identify the machine type (from the recipe type name).
3. Subtract one tier if the machine is a multiblock that allows overclocking, unless the
   tooltip/metadata says otherwise.
4. The minimum input tier is the earliest you can satisfy all recipe inputs recursively.

---

## Common Workflows

**Find how to make something:**
```bash
./gtnh search "item name"            # get the id
./gtnh recipes-for "<id>"            # production recipes
```

**Find what something is used in:**
```bash
./gtnh recipes-using "<id>"
```

**Find the best fuel for a generator type:**
```bash
./gtnh recipe-types --filter turbine  # find the exact recipe type name
./gtnh recipes-of-type "Gas Turbine Fuel" --sort fuel
```

**Trace a full production chain:** run `recipes-for` on each intermediate, working
backwards from the target.

**Extract precise numeric data for calculations:** use `--json` and pipe to `python3 -c`
or `jq`. The JSON schema directly mirrors the Rust structs (`GtRecipe`, `RecipeIo`, etc.).

---

## Data Scale

41,091 items · 1,542 fluids · 625 ore dicts · 154 recipe types · 190,080 recipes

Some machines/multiblocks have no recipe entry in the data (output computed outside GT
recipe system). Notable gaps: IC2 Nuclear Fission (EU/t computed by reactor simulation,
not stored), some BartWorks LNR fuel production chains.

---

## Crate Structure

| File | Contents |
|------|----------|
| `src/lib.rs` | `Repository`, all entity structs (`Item`, `Fluid`, `Recipe`, `GtRecipe`, …), SQLite queries, `build_db` |
| `src/main.rs` | CLI (`clap` derive), display formatting, sort helpers |
| `gtnh.db` | SQLite database built from `nesql-db.script` via `build-db` subcommand |

## Infinite resource sources
In order of best to worst (written as currently available in ZPM):
- Reservoir Hatch (water)
- Extreme Entity Crusher
- Ender Tree (endstone and obsidian)
- Nether Tree (netherrack, nether quartz, soulsand)
- Air intake hatch (air, nether air)
- Extreme Industrial Greenhouse (non-IC2 crop)
  - EIG isn't shown as recipes, see https://wiki.gtnewhorizons.com/wiki/Extreme_Industrial_Greenhouse for some of the recommended seeds
- Planetary Gas Siphon
  - These don't have recipes in data.bin, see https://wiki.gtnewhorizons.com/wiki/Planetary_Gas_Siphon for gases
- Bees
- Extreme Industrial Greenhouse (IC2 crop)
  - Use https://wiki.gtnewhorizons.com/wiki/IC2_Crops_List for the list of crops and their drops

When answering "what is the best way to source X", always enumerate what **each**
infinite source produces first, then trace those outputs forward to X. Do not filter
by obvious inputs (water, air) and stop — less obvious sources like EIG crops or EEC
mob drops may yield far better routes.
